from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest

from detrix.core.trajectory import TRAJECTORY_SCHEMA_VERSION, GovernedTrajectory
from detrix.runtime.trajectory_store import TrajectoryStore


class TestGovernedTrajectory:
    def test_construct_minimal(self) -> None:
        trajectory = GovernedTrajectory(
            trajectory_id="abc123",
            run_id="run-001",
            domain="xrd",
            prompt='{"pattern": "scan_001.xy"}',
            completion='{"phases": ["quartz"]}',
            verdicts=[],
            governance_score=1.0,
            gate_pass_rate=1.0,
            started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        )
        assert trajectory.schema_version == TRAJECTORY_SCHEMA_VERSION
        assert trajectory.trajectory_id == "abc123"
        assert trajectory.rejection_type is None
        assert trajectory.model_version is None

    def test_to_sft_row_on_passing_trace(self) -> None:
        trajectory = GovernedTrajectory(
            trajectory_id="abc123",
            run_id="run-001",
            domain="xrd",
            prompt="input text",
            completion="output text",
            verdicts=[],
            governance_score=1.0,
            gate_pass_rate=1.0,
            started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        )
        assert trajectory.to_sft_row() == {
            "prompt": "input text",
            "completion": "output text",
        }

    def test_to_sft_row_rejects_failed_trace(self) -> None:
        trajectory = GovernedTrajectory(
            trajectory_id="abc123",
            run_id="run-001",
            domain="xrd",
            prompt="input",
            completion="output",
            verdicts=[],
            governance_score=0.0,
            gate_pass_rate=0.0,
            rejection_type="output_quality",
            started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        )

        with pytest.raises(ValueError, match="rejected"):
            trajectory.to_sft_row()

    def test_to_grpo_row(self) -> None:
        verdict_dict = {"decision": "accept", "gate_id": "quality", "evidence": {}}
        trajectory = GovernedTrajectory(
            trajectory_id="abc123",
            run_id="run-001",
            domain="xrd",
            prompt="input",
            completion="output",
            verdicts=[verdict_dict],
            governance_score=0.8,
            gate_pass_rate=1.0,
            started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        )
        row = trajectory.to_grpo_row()
        assert row["governance_score"] == 0.8
        assert row["gate_verdicts"] == ["accept"]

    def test_roundtrip_json(self) -> None:
        trajectory = GovernedTrajectory(
            trajectory_id="abc123",
            run_id="run-001",
            domain="xrd",
            prompt="in",
            completion="out",
            verdicts=[{"decision": "accept", "gate_id": "g1", "evidence": {}}],
            governance_score=1.0,
            gate_pass_rate=1.0,
            evaluator_versions={"g1": "1.0.0"},
            gate_versions={"g1": "1.0.0"},
            started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        )
        json_str = trajectory.model_dump_json()
        restored = GovernedTrajectory.model_validate_json(json_str)
        assert restored.trajectory_id == trajectory.trajectory_id
        assert restored.verdicts == trajectory.verdicts
        assert restored.evaluator_versions == trajectory.evaluator_versions


class TestTrajectoryStore:
    def test_append_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            trajectory = _trajectory("traj-001")
            store.append(trajectory)
            got = store.get("traj-001")
            assert got is not None
            assert got.trajectory_id == "traj-001"
            assert got.domain == "xrd"

    def test_get_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            assert store.get("nonexistent") is None

    def test_list_by_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            for i in range(3):
                store.append(_trajectory(f"traj-{i}", run_id="run-001"))
            results = store.list_by_run("run-001")
            assert len(results) == 3

    def test_query_by_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            store.append(_trajectory("t1", run_id="r1", domain="xrd"))
            store.append(
                _trajectory(
                    "t2",
                    run_id="r2",
                    domain="pharma",
                    governance_score=0.5,
                    gate_pass_rate=0.5,
                )
            )
            xrd_results = store.query(domain="xrd")
            assert len(xrd_results) == 1
            assert xrd_results[0].domain == "xrd"

    def test_query_by_min_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            for score in [0.2, 0.5, 0.8, 1.0]:
                store.append(
                    _trajectory(
                        f"t-{score}",
                        governance_score=score,
                        gate_pass_rate=score,
                    )
                )
            results = store.query(min_score=0.7)
            assert len(results) == 2

    def test_query_by_rejection_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            store.append(_trajectory("t-pass"))
            store.append(
                _trajectory(
                    "t-fail",
                    governance_score=0.0,
                    gate_pass_rate=0.0,
                    rejection_type="output_quality",
                )
            )
            passed = store.query(rejection_type=None)
            assert len(passed) == 1
            assert passed[0].trajectory_id == "t-pass"

    def test_duplicate_trajectory_id_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            trajectory = _trajectory("dup")
            store.append(trajectory)
            with pytest.raises(sqlite3.IntegrityError):
                store.append(trajectory)

    def test_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            assert store.count() == 0
            store.append(_trajectory("t1"))
            assert store.count() == 1


def _trajectory(
    trajectory_id: str,
    *,
    run_id: str = "run-001",
    domain: str = "xrd",
    governance_score: float = 1.0,
    gate_pass_rate: float = 1.0,
    rejection_type: str | None = None,
) -> GovernedTrajectory:
    return GovernedTrajectory(
        trajectory_id=trajectory_id,
        run_id=run_id,
        domain=domain,
        prompt="in",
        completion="out",
        verdicts=[],
        governance_score=governance_score,
        gate_pass_rate=gate_pass_rate,
        rejection_type=rejection_type,
        started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )
