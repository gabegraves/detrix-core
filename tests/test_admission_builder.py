from __future__ import annotations

from datetime import datetime, timezone

from detrix.core.admission import AdmissionBuilder
from detrix.core.trajectory import GovernedTrajectory


def _trajectory(verdicts: list[dict[str, object]], domain: str = "openclaw") -> GovernedTrajectory:
    return GovernedTrajectory(
        trajectory_id=f"{domain}-1",
        run_id="run-1",
        domain=domain,
        prompt="prompt",
        completion="completion",
        verdicts=verdicts,
        governance_score=1.0,
        gate_pass_rate=1.0,
        started_at=datetime.now(timezone.utc),
    )


def test_admission_builder_routes_accept_to_sft_and_promotion_after_replay() -> None:
    trajectory = AdmissionBuilder.compute_admission(
        _trajectory([{"decision": "accept", "reason_codes": []}]),
        replay_status="passed",
    )

    assert trajectory.training_route == "sft"
    assert trajectory.replay_status == "passed"
    assert trajectory.promotion_eligible is True


def test_admission_builder_routes_rewrite_cautions_to_dpo() -> None:
    trajectory = AdmissionBuilder.compute_admission(
        _trajectory([{"decision": "caution", "reason_codes": ["needs_chunking"]}])
    )

    assert trajectory.training_route == "dpo"
    assert trajectory.promotion_eligible is False


def test_admission_builder_routes_reject_to_eval_only() -> None:
    trajectory = AdmissionBuilder.compute_admission(
        _trajectory(
            [
                {
                    "decision": "reject",
                    "reason_codes": ["message_length_exceeded"],
                    "rejection_type": "output_quality",
                }
            ]
        )
    )

    assert trajectory.training_route == "eval_only"
    assert trajectory.rejection_type == "output_quality"


def test_admission_builder_has_same_fields_for_openclaw_and_agentxrd() -> None:
    openclaw = AdmissionBuilder.compute_admission(
        _trajectory([{"decision": "caution", "reason_codes": ["needs_reformat"]}], "openclaw")
    )
    agentxrd = AdmissionBuilder.compute_admission(
        _trajectory([{"decision": "accept", "reason_codes": []}], "agentxrd")
    )

    for trajectory in (openclaw, agentxrd):
        dumped = trajectory.model_dump()
        assert "training_route" in dumped
        assert "replay_status" in dumped
        assert "promotion_eligible" in dumped
