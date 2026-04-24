from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from detrix.core.trajectory import GovernedTrajectory
from detrix.improvement.exporter import TrainingExporter
from detrix.runtime.trajectory_store import TrajectoryStore


def _make_trajectory(
    tid: str,
    score: float = 1.0,
    rejection: str | None = None,
    gate_verdicts: list[dict[str, object]] | None = None,
) -> GovernedTrajectory:
    return GovernedTrajectory(
        trajectory_id=tid,
        run_id="run-test",
        domain="xrd",
        prompt=json.dumps({"sample_id": tid, "input": "pattern data"}),
        completion=json.dumps({"phases": ["quartz"], "rwp": 8.5}),
        verdicts=gate_verdicts
        or [
            {"decision": "accept", "gate_id": "score_gate", "evidence": {"confidence": 0.9}},
            {"decision": "accept", "gate_id": "refine_gate", "evidence": {"rwp": 8.5}},
        ],
        governance_score=score,
        gate_pass_rate=score,
        rejection_type=rejection,
        evaluator_versions={"score_gate": "1.0", "refine_gate": "1.0"},
        gate_versions={"score_gate": "1.0", "refine_gate": "1.0"},
        started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )


@pytest.fixture
def store_with_data(tmp_path) -> TrajectoryStore:
    store = TrajectoryStore(str(tmp_path / "evidence.db"))
    store.append(_make_trajectory("t-pass-1", score=1.0))
    store.append(_make_trajectory("t-pass-2", score=0.8))
    store.append(_make_trajectory("t-fail-output", score=0.0, rejection="output_quality"))
    store.append(_make_trajectory("t-fail-input", score=0.0, rejection="input_quality"))
    return store


class TestTrainingExporter:
    def test_export_sft_excludes_rejected(
        self,
        store_with_data: TrajectoryStore,
        tmp_path,
    ) -> None:
        exporter = TrainingExporter(store_with_data)
        path = exporter.export_sft(str(tmp_path / "sft.jsonl"), domain="xrd")

        rows = [json.loads(line) for line in open(path, encoding="utf-8")]
        assert len(rows) == 2
        for row in rows:
            assert "prompt" in row
            assert "completion" in row

    def test_export_sft_respects_min_score(
        self,
        store_with_data: TrajectoryStore,
        tmp_path,
    ) -> None:
        exporter = TrainingExporter(store_with_data)
        path = exporter.export_sft(str(tmp_path / "sft.jsonl"), domain="xrd", min_score=0.9)

        rows = [json.loads(line) for line in open(path, encoding="utf-8")]
        assert len(rows) == 1

    def test_export_grpo_includes_scores(
        self,
        store_with_data: TrajectoryStore,
        tmp_path,
    ) -> None:
        exporter = TrainingExporter(store_with_data)
        path = exporter.export_grpo(str(tmp_path / "grpo.jsonl"), domain="xrd")

        rows = [json.loads(line) for line in open(path, encoding="utf-8")]
        assert len(rows) == 2
        for row in rows:
            assert "governance_score" in row
            assert "gate_verdicts" in row
            assert isinstance(row["governance_score"], float)

    def test_export_dpo_pairs_by_prompt(self, tmp_path) -> None:
        store = TrajectoryStore(str(tmp_path / "evidence.db"))
        shared_prompt = json.dumps({"sample_id": "s1", "input": "same pattern"})
        store.append(
            GovernedTrajectory(
                trajectory_id="chosen",
                run_id="r1",
                domain="xrd",
                prompt=shared_prompt,
                completion=json.dumps({"phases": ["quartz"]}),
                verdicts=[{"decision": "accept", "gate_id": "g1", "evidence": {}}],
                governance_score=1.0,
                gate_pass_rate=1.0,
                started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            )
        )
        store.append(
            GovernedTrajectory(
                trajectory_id="rejected",
                run_id="r2",
                domain="xrd",
                prompt=shared_prompt,
                completion=json.dumps({"phases": ["wrong"]}),
                verdicts=[{"decision": "reject", "gate_id": "g1", "evidence": {}}],
                governance_score=0.0,
                gate_pass_rate=0.0,
                rejection_type="output_quality",
                started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            )
        )
        exporter = TrainingExporter(store)
        path = exporter.export_dpo(str(tmp_path / "dpo.jsonl"), domain="xrd")

        rows = [json.loads(line) for line in open(path, encoding="utf-8")]
        assert len(rows) == 1
        assert rows[0]["chosen"] == json.dumps({"phases": ["quartz"]})
        assert rows[0]["rejected"] == json.dumps({"phases": ["wrong"]})

    def test_export_dpo_no_pairs_returns_empty(
        self,
        store_with_data: TrajectoryStore,
        tmp_path,
    ) -> None:
        exporter = TrainingExporter(store_with_data)
        path = exporter.export_dpo(str(tmp_path / "dpo.jsonl"), domain="xrd")

        rows = [json.loads(line) for line in open(path, encoding="utf-8")]
        assert len(rows) == 0

    def test_export_returns_path(self, store_with_data: TrajectoryStore, tmp_path) -> None:
        exporter = TrainingExporter(store_with_data)
        path = exporter.export_sft(str(tmp_path / "sft.jsonl"), domain="xrd")
        assert os.path.exists(path)

    def test_export_to_dataset(self, store_with_data: TrajectoryStore) -> None:
        pytest.importorskip("datasets")
        exporter = TrainingExporter(store_with_data)
        dataset = exporter.to_dataset("sft", domain="xrd")
        assert len(dataset) == 2
        assert "prompt" in dataset.column_names
        assert "completion" in dataset.column_names
