from __future__ import annotations

import os
import tempfile

from detrix.adapters.axv2 import (
    gate_record_to_verdict,
    project_to_audit_log,
    run_artifact_to_trajectories,
)
from detrix.core.governance import Decision
from detrix.runtime.audit import AuditLog


class TestGateRecordToVerdict:
    def test_passed_gate_maps_to_accept(self) -> None:
        record = {
            "sample_id": "sample_001",
            "gate_name": "post_score_quality_gate",
            "status": "passed",
            "decision": "continue",
            "reason_codes": [],
            "evidence": {"confidence": 0.95, "best_rwp": 12.3},
            "thresholds": {"min_confidence": 0.6},
            "input_hash": "abc123",
        }
        verdict = gate_record_to_verdict(record)
        assert verdict.decision == Decision.ACCEPT
        assert verdict.gate_id == "post_score_quality_gate"
        assert verdict.evidence["confidence"] == 0.95
        assert verdict.input_hash == "abc123"

    def test_rejected_halt_unknown_maps_to_unknown(self) -> None:
        record = {
            "sample_id": "sample_002",
            "gate_name": "post_refinement_quality_gate",
            "status": "rejected",
            "decision": "halt_unknown",
            "reason_codes": ["low_confidence", "high_ensemble_disagreement"],
            "evidence": {"confidence": 0.3},
        }
        verdict = gate_record_to_verdict(record)
        assert verdict.decision == Decision.UNKNOWN
        assert verdict.reason_codes == ["low_confidence", "high_ensemble_disagreement"]

    def test_rejected_downgrade_set_maps_to_caution(self) -> None:
        record = {
            "sample_id": "sample_003",
            "gate_name": "post_refinement_quality_gate",
            "status": "rejected",
            "decision": "downgrade_set",
            "reason_codes": ["unstable_refinement_evidence"],
            "evidence": {"best_rwp": 45.0},
        }
        verdict = gate_record_to_verdict(record)
        assert verdict.decision == Decision.CAUTION

    def test_rejected_request_more_data_maps_to_request_more_data(self) -> None:
        record = {
            "sample_id": "sample_004",
            "gate_name": "evidence_gate",
            "status": "rejected",
            "decision": "request_more_data",
            "reason_codes": ["missing_evidence"],
            "evidence": {"missing": ["confidence"]},
        }
        verdict = gate_record_to_verdict(record)
        assert verdict.decision == Decision.REQUEST_MORE_DATA
        assert verdict.reason_codes == ["missing_evidence"]

    def test_missing_optional_fields_default_safely(self) -> None:
        record = {
            "sample_id": "s1",
            "gate_name": "g1",
            "status": "passed",
            "decision": "continue",
        }
        verdict = gate_record_to_verdict(record)
        assert verdict.decision == Decision.ACCEPT
        assert verdict.evidence == {}
        assert verdict.reason_codes == []
        assert verdict.input_hash == ""


class TestAuditProjection:
    def test_projects_run_and_steps_to_audit_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(os.path.join(tmp, "audit.db"))
            artifact = _make_artifact(
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "score_gate",
                        "status": "passed",
                        "decision": "continue",
                        "evidence": {"confidence": 0.9},
                    },
                ],
            )
            project_to_audit_log(artifact, audit)

            run = audit.get_run("run-abc")
            assert run is not None
            assert run["workflow_name"] == "axv2-import"
            assert run["status"] == "success"
            assert len(run["steps"]) == 2

    def test_step_gate_columns_populated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(os.path.join(tmp, "audit.db"))
            artifact = _make_artifact(
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "score_gate",
                        "status": "passed",
                        "decision": "continue",
                        "evidence": {"confidence": 0.9},
                        "reason_codes": [],
                    },
                ],
            )
            project_to_audit_log(artifact, audit)

            run = audit.get_run("run-abc")
            assert run is not None
            gated_steps = [step for step in run["steps"] if step["gate_decision"] is not None]
            assert len(gated_steps) >= 1
            step = gated_steps[0]
            assert step["gate_decision"] == "accept"
            assert step["gate_id"] == "score_gate"
            assert step["gate_verdict_json"] is not None

    def test_failed_run_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(os.path.join(tmp, "audit.db"))
            artifact = _make_artifact()
            artifact["success"] = False
            project_to_audit_log(artifact, audit)

            run = audit.get_run("run-abc")
            assert run is not None
            assert run["status"] == "failed"

    def test_multiple_gates_attached_to_corresponding_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(os.path.join(tmp, "audit.db"))
            artifact = _make_artifact(
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "post_score_quality_gate",
                        "status": "passed",
                        "decision": "continue",
                        "evidence": {"confidence": 0.9},
                    },
                    {
                        "sample_id": "s1",
                        "gate_name": "post_refinement_quality_gate",
                        "status": "rejected",
                        "decision": "halt_unknown",
                        "evidence": {"rwp": 50.0},
                        "reason_codes": ["high_rwp"],
                    },
                ],
            )
            project_to_audit_log(artifact, audit)

            run = audit.get_run("run-abc")
            assert run is not None
            gated = [step for step in run["steps"] if step["gate_decision"] is not None]
            assert len(gated) == 2
            decisions = {step["gate_id"]: step["gate_decision"] for step in gated}
            assert decisions["post_score_quality_gate"] == "accept"
            assert decisions["post_refinement_quality_gate"] == "unknown"
            step_ids = {step["gate_id"]: step["step_id"] for step in gated}
            assert step_ids["post_score_quality_gate"] == "SCORING"
            assert step_ids["post_refinement_quality_gate"] == "REFINEMENT"

    def test_unknown_gate_creates_synthetic_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(os.path.join(tmp, "audit.db"))
            artifact = _make_artifact(
                gate_history=[
                    {
                        "sample_id": "s1",
                        "gate_name": "custom_domain_gate",
                        "status": "passed",
                        "decision": "continue",
                        "evidence": {"metric": 42},
                    },
                ],
            )
            project_to_audit_log(artifact, audit)

            run = audit.get_run("run-abc")
            assert run is not None
            gated = [step for step in run["steps"] if step["gate_decision"] is not None]
            assert len(gated) == 1
            assert gated[0]["step_id"] == "GATE:custom_domain_gate:s1"
            assert gated[0]["gate_decision"] == "accept"


class TestRunArtifactToTrajectories:
    def test_artifact_with_passing_gates_produces_trajectory(self) -> None:
        artifact = _make_artifact(
            gate_history=[
                {
                    "sample_id": "s1",
                    "gate_name": "score_gate",
                    "status": "passed",
                    "decision": "continue",
                    "evidence": {"confidence": 0.9},
                },
                {
                    "sample_id": "s1",
                    "gate_name": "refine_gate",
                    "status": "passed",
                    "decision": "continue",
                    "evidence": {"rwp": 8.5},
                },
            ],
        )
        trajectories = run_artifact_to_trajectories(artifact, domain="xrd")
        assert len(trajectories) == 1
        trajectory = trajectories[0]
        assert trajectory.run_id == "run-abc"
        assert trajectory.domain == "xrd"
        assert trajectory.governance_score == 1.0
        assert trajectory.gate_pass_rate == 1.0
        assert trajectory.rejection_type is None
        assert len(trajectory.verdicts) == 2

    def test_artifact_with_terminal_route_sets_rejection(self) -> None:
        artifact = _make_artifact(
            gate_history=[
                {
                    "sample_id": "s1",
                    "gate_name": "score_gate",
                    "status": "rejected",
                    "decision": "halt_unknown",
                    "evidence": {"confidence": 0.2},
                    "reason_codes": ["low_confidence"],
                },
            ],
            terminal_routes={
                "s1": {
                    "sample_id": "s1",
                    "verdict": "UNKNOWN",
                    "gate_name": "score_gate",
                    "status": "rejected",
                    "reason_codes": ["low_confidence"],
                },
            },
        )
        trajectories = run_artifact_to_trajectories(artifact)
        assert len(trajectories) == 1
        trajectory = trajectories[0]
        assert trajectory.governance_score == 0.0
        assert trajectory.rejection_type == "output_quality"

    def test_artifact_with_request_more_data_sets_input_quality(self) -> None:
        artifact = _make_artifact(
            terminal_routes={
                "s1": {
                    "sample_id": "s1",
                    "verdict": "REQUEST_MORE_DATA",
                    "gate_name": "metrology",
                    "status": "rejected",
                },
            },
        )
        trajectories = run_artifact_to_trajectories(artifact)
        assert len(trajectories) == 1
        assert trajectories[0].rejection_type == "input_quality"

    def test_artifact_with_no_gates_produces_trajectory_with_zero_score(self) -> None:
        artifact = _make_artifact()
        trajectories = run_artifact_to_trajectories(artifact)
        assert len(trajectories) == 1
        trajectory = trajectories[0]
        assert trajectory.governance_score == 0.0
        assert trajectory.gate_pass_rate == 0.0
        assert trajectory.rejection_type is None

    def test_multi_sample_artifact_produces_multiple_trajectories(self) -> None:
        artifact = _make_artifact(
            gate_history=[
                {"sample_id": "s1", "gate_name": "g1", "status": "passed", "decision": "continue"},
                {"sample_id": "s2", "gate_name": "g1", "status": "passed", "decision": "continue"},
                {"sample_id": "s1", "gate_name": "g2", "status": "passed", "decision": "continue"},
                {
                    "sample_id": "s2",
                    "gate_name": "g2",
                    "status": "rejected",
                    "decision": "halt_unknown",
                },
            ],
            terminal_routes={
                "s2": {
                    "sample_id": "s2",
                    "verdict": "UNKNOWN",
                    "gate_name": "g2",
                    "status": "rejected",
                },
            },
        )
        trajectories = run_artifact_to_trajectories(artifact)
        assert len(trajectories) == 2
        passed = [trajectory for trajectory in trajectories if trajectory.rejection_type is None]
        failed = [trajectory for trajectory in trajectories if trajectory.rejection_type is not None]
        assert len(passed) == 1
        assert len(failed) == 1
        assert passed[0].gate_pass_rate == 1.0
        assert failed[0].gate_pass_rate == 0.5

    def test_training_eligibility_sft_false_rejects_set_terminal_route(self) -> None:
        artifact = _make_artifact(
            gate_history=[
                {
                    "sample_id": "set-row",
                    "gate_name": "agentxrd_scientist_review_gate_v0",
                    "status": "rejected",
                    "decision": "downgrade_set",
                    "evidence": {
                        "training_eligibility": {
                            "sft": False,
                            "dpo": True,
                            "grpo": False,
                            "eval_only": True,
                            "reason": "accept_eligible_false",
                        },
                        "accept_eligible": False,
                    },
                },
            ],
            terminal_routes={
                "set-row": {
                    "sample_id": "set-row",
                    "verdict": "SET",
                    "training_eligibility": {
                        "sft": False,
                        "dpo": True,
                        "grpo": False,
                        "eval_only": True,
                        "reason": "accept_eligible_false",
                    },
                },
            },
        )

        trajectories = run_artifact_to_trajectories(artifact)

        assert len(trajectories) == 1
        assert trajectories[0].rejection_type is not None
        assert "Cannot use rejected trace for SFT" in _sft_error(trajectories[0])

    def test_support_only_gate_evidence_rejects_accept_terminal_route(self) -> None:
        artifact = _make_artifact(
            gate_history=[
                {
                    "sample_id": "support-row",
                    "gate_name": "agentxrd_scientist_review_gate_v0",
                    "status": "passed",
                    "decision": "continue",
                    "evidence": {
                        "support_only": True,
                        "accept_eligible": False,
                        "training_eligibility": {
                            "sft": False,
                            "dpo": True,
                            "grpo": False,
                            "eval_only": True,
                            "reason": "support_only_public_cif_not_accept_eligible",
                        },
                    },
                },
            ],
            terminal_routes={
                "support-row": {
                    "sample_id": "support-row",
                    "verdict": "ACCEPT",
                    "training_eligibility": {
                        "sft": False,
                        "dpo": True,
                        "grpo": False,
                        "eval_only": True,
                        "reason": "support_only_public_cif_not_accept_eligible",
                    },
                },
            },
        )

        trajectories = run_artifact_to_trajectories(artifact)

        assert len(trajectories) == 1
        assert trajectories[0].rejection_type is not None

    def test_clean_accepted_fixture_remains_export_eligible(self) -> None:
        artifact = _make_artifact(
            gate_history=[
                {
                    "sample_id": "clean-row",
                    "gate_name": "agentxrd_scientist_review_gate_v0",
                    "status": "passed",
                    "decision": "continue",
                    "evidence": {
                        "support_only": False,
                        "accept_eligible": True,
                        "training_eligibility": {
                            "sft": True,
                            "dpo": False,
                            "grpo": True,
                            "eval_only": False,
                            "reason": "deterministic_gates_reference_eligible",
                        },
                    },
                },
            ],
            terminal_routes={
                "clean-row": {
                    "sample_id": "clean-row",
                    "verdict": "ACCEPT",
                    "training_eligibility": {
                        "sft": True,
                        "dpo": False,
                        "grpo": True,
                        "eval_only": False,
                        "reason": "deterministic_gates_reference_eligible",
                    },
                },
            },
        )

        trajectories = run_artifact_to_trajectories(artifact)

        assert len(trajectories) == 1
        assert trajectories[0].rejection_type is None
        assert trajectories[0].to_sft_row()["prompt"]


def _sft_error(trajectory) -> str:
    try:
        trajectory.to_sft_row()
    except ValueError as exc:
        return str(exc)
    return ""


def _make_artifact(
    gate_history: list[dict[str, object]] | None = None,
    terminal_routes: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "run_id": "run-abc",
        "timestamp": "2026-04-24T12:00:00",
        "pipeline_version": "abc123",
        "config_hash": "cfg-hash",
        "input_file_hash": "inp-hash",
        "steps": [
            {"name": "SCORING", "status": "success", "duration_ms": 100.0},
            {"name": "REFINEMENT", "status": "success", "duration_ms": 200.0},
        ],
        "success": True,
        "total_duration_ms": 300.0,
        "model_versions": {"SCORING": {"name": "ensemble", "version": "1.0"}},
        "gate_history": gate_history or [],
        "terminal_routes": terminal_routes or {},
    }
