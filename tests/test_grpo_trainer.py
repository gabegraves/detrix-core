from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from detrix.core.trajectory import GovernedTrajectory
from detrix.improvement.training_config import TrainingConfig
from detrix.runtime.trajectory_store import TrajectoryStore


def _make_trajectory(tid: str, score: float = 1.0, prompt: str | None = None) -> GovernedTrajectory:
    return GovernedTrajectory(
        trajectory_id=tid,
        run_id="r1",
        domain="xrd",
        prompt=prompt or json.dumps({"sample_id": tid, "input": "pattern data"}),
        completion=json.dumps({"phases": ["quartz"], "rwp": 8.5, "candidate": tid}),
        verdicts=[
            {"decision": "accept", "gate_id": "score_gate", "evidence": {"confidence": 0.9}},
            {"decision": "accept", "gate_id": "refine_gate", "evidence": {"rwp": 8.5}},
        ],
        governance_score=score,
        gate_pass_rate=score,
        started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )


class TestGovernedTrajectoryToART:
    def test_converts_to_art_trajectory_group(self) -> None:
        pytest.importorskip("art")
        from detrix.improvement.grpo_trainer import governed_to_art_group

        group = governed_to_art_group(_make_trajectory("t1", score=0.8))
        assert group is not None
        assert len(group.trajectories) >= 1
        assert group.trajectories[0].reward == 0.8

    def test_trajectory_messages_contain_prompt(self) -> None:
        pytest.importorskip("art")
        from detrix.improvement.grpo_trainer import trajectory_messages

        msgs = trajectory_messages(_make_trajectory("t1"))
        user_msgs = [m for m in msgs if m["role"] == "user"]
        assert len(user_msgs) == 1
        assert "pattern data" in user_msgs[0]["content"]
        asst_msgs = [m for m in msgs if m["role"] == "assistant"]
        assert len(asst_msgs) == 1
        assert "quartz" in asst_msgs[0]["content"]

    def test_groups_require_reward_variance(self) -> None:
        pytest.importorskip("art")
        from detrix.improvement.grpo_trainer import group_governed_trajectories

        prompt = json.dumps({"sample_id": "same", "input": "pattern data"})
        groups = group_governed_trajectories(
            [_make_trajectory("t1", 0.4, prompt), _make_trajectory("t2", 0.9, prompt)]
        )
        assert len(groups) == 1
        assert len(groups[0].trajectories) == 2


class TestDetrixGRPOTrainer:
    def test_load_trajectory_groups(self) -> None:
        pytest.importorskip("art")
        from detrix.improvement.grpo_trainer import DetrixGRPOTrainer

        with tempfile.TemporaryDirectory() as tmp:
            store = TrajectoryStore(os.path.join(tmp, "evidence.db"))
            prompt = json.dumps({"sample_id": "same", "input": "pattern data"})
            store.append(_make_trajectory("t1", score=1.0, prompt=prompt))
            store.append(_make_trajectory("t2", score=0.5, prompt=prompt))

            config = TrainingConfig(
                model_name="test/model",
                backend="grpo",
                evidence_db=os.path.join(tmp, "evidence.db"),
                domain="xrd",
            )
            groups = DetrixGRPOTrainer(config).load_trajectory_groups()
            assert len(groups) == 1

    def test_empty_store_raises(self) -> None:
        pytest.importorskip("art")
        from detrix.improvement.grpo_trainer import DetrixGRPOTrainer

        with tempfile.TemporaryDirectory() as tmp:
            TrajectoryStore(os.path.join(tmp, "evidence.db"))
            config = TrainingConfig(
                model_name="test/model",
                backend="grpo",
                evidence_db=os.path.join(tmp, "evidence.db"),
                domain="pharma",
            )
            with pytest.raises(ValueError, match="No trajectories"):
                DetrixGRPOTrainer(config).load_trajectory_groups()
