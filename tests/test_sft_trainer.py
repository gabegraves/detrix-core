from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from detrix.core.trajectory import GovernedTrajectory
from detrix.improvement.sft_trainer import DetrixSFTTrainer, TrainingResult
from detrix.improvement.training_config import TrainingConfig
from detrix.runtime.trajectory_store import TrajectoryStore

pytest.importorskip("datasets")


def _seed_store(db_path: str) -> TrajectoryStore:
    store = TrajectoryStore(db_path)
    for i in range(3):
        store.append(
            GovernedTrajectory(
                trajectory_id=f"t-{i}",
                run_id="r1",
                domain="xrd",
                prompt=json.dumps({"sample_id": f"s{i}", "input": f"pattern_{i}"}),
                completion=json.dumps({"phases": [f"phase_{i}"], "rwp": 8.0 + i}),
                verdicts=[{"decision": "accept", "gate_id": "g1", "evidence": {}}],
                governance_score=1.0,
                gate_pass_rate=1.0,
                started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
            )
        )
    return store


class TestDetrixSFTTrainer:
    def test_load_dataset_from_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "evidence.db")
            _seed_store(db_path)
            config = TrainingConfig(model_name="test/model", evidence_db=db_path, domain="xrd")
            trainer = DetrixSFTTrainer(config)
            dataset = trainer.load_dataset()
            assert len(dataset) == 3
            assert "text" in dataset.column_names

    def test_format_chat_contains_prompt_and_completion(self) -> None:
        row = {"prompt": "input data", "completion": "output data"}
        text = DetrixSFTTrainer.format_chat(row)
        assert "input data" in text
        assert "output data" in text

    def test_format_chat_uses_chatml(self) -> None:
        row = {"prompt": "test prompt", "completion": "test completion"}
        text = DetrixSFTTrainer.format_chat(row)
        assert "<|im_start|>" in text
        assert "<|im_end|>" in text

    def test_empty_store_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "evidence.db")
            TrajectoryStore(db_path)
            config = TrainingConfig(model_name="test/model", evidence_db=db_path, domain="pharma")
            trainer = DetrixSFTTrainer(config)
            with pytest.raises(ValueError, match="No trajectories"):
                trainer.load_dataset()


    def test_load_dataset_honors_explicit_limit_without_silent_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "evidence.db")
            store = TrajectoryStore(db_path)
            for i in range(105):
                store.append(
                    GovernedTrajectory(
                        trajectory_id=f"bulk-{i}",
                        run_id="r1",
                        domain="xrd",
                        prompt=json.dumps({"sample_id": f"bulk-{i}"}),
                        completion=json.dumps({"phases": ["quartz"]}),
                        verdicts=[{"decision": "accept", "gate_id": "g1", "evidence": {}}],
                        governance_score=1.0,
                        gate_pass_rate=1.0,
                        started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
                    )
                )

            uncapped = DetrixSFTTrainer(
                TrainingConfig(model_name="test/model", evidence_db=db_path, domain="xrd")
            ).load_dataset()
            capped = DetrixSFTTrainer(
                TrainingConfig(model_name="test/model", evidence_db=db_path, domain="xrd", limit=2)
            ).load_dataset()

            assert len(uncapped) == 105
            assert len(capped) == 2

    def test_training_result_structure(self) -> None:
        result = TrainingResult(
            adapter_path="/path/to/adapter",
            model_name="test/model",
            backend="sft",
            num_examples=10,
            num_steps=50,
            final_loss=0.5,
            metrics={"eval_loss": 0.6},
        )
        assert result.adapter_path == "/path/to/adapter"
        assert result.backend == "sft"
        assert result.final_loss == 0.5
