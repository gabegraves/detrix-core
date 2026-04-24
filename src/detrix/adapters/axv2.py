"""Adapter: AgentXRD_v2 gate records to Detrix governance evidence."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from detrix.core.governance import Decision, VerdictContract
from detrix.core.models import RunRecord, StepResult, StepStatus
from detrix.core.trajectory import GovernedTrajectory
from detrix.runtime.audit import AuditLog

_STATUS_DECISION_MAP: dict[tuple[str, str], Decision] = {
    ("passed", "continue"): Decision.ACCEPT,
    ("rejected", "halt_unknown"): Decision.UNKNOWN,
    ("rejected", "downgrade_set"): Decision.CAUTION,
}

_TERMINAL_VERDICT_TO_REJECTION: dict[str, str | None] = {
    "ACCEPT": None,
    "SET": None,
    "UNKNOWN": "output_quality",
    "REQUEST_MORE_DATA": "input_quality",
}

_GATE_NAME_TO_STEP: dict[str, str] = {
    "post_score_quality_gate": "SCORING",
    "post_refinement_quality_gate": "REFINEMENT",
    "metrology_guard": "METROLOGY_GUARD",
    "metrology": "METROLOGY_GUARD",
}


def gate_record_to_verdict(record: dict[str, Any]) -> VerdictContract:
    """Convert an AXV2 GateRecord dict to a Detrix VerdictContract."""
    status = str(record.get("status", ""))
    decision_str = str(record.get("decision", ""))
    decision = _STATUS_DECISION_MAP.get((status, decision_str))
    if decision is None:
        decision = Decision.ACCEPT if status == "passed" else Decision.REJECT

    return VerdictContract(
        decision=decision,
        gate_id=str(record.get("gate_name", "unknown")),
        evidence=dict(record.get("evidence", {})),
        reason_codes=list(record.get("reason_codes", [])),
        input_hash=str(record.get("input_hash", "")),
        evaluator_version="axv2-import",
    )


def project_to_audit_log(artifact: dict[str, Any], audit: AuditLog) -> None:
    """Project an AXV2 RunArtifact into the existing Detrix AuditLog schema."""
    run_id = str(artifact.get("run_id") or uuid.uuid4().hex[:12])
    started_at = _parse_timestamp(artifact.get("timestamp"))
    total_ms = float(artifact.get("total_duration_ms", 0.0) or 0.0)
    finished_at = datetime.fromtimestamp(
        started_at.timestamp() + total_ms / 1000.0,
        tz=timezone.utc,
    )
    status = StepStatus.SUCCESS if artifact.get("success", False) else StepStatus.FAILED

    record = RunRecord(
        run_id=run_id,
        workflow_name="axv2-import",
        workflow_version=str(artifact.get("pipeline_version", "unknown")),
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        inputs={
            "config_hash": artifact.get("config_hash"),
            "input_file_hash": artifact.get("input_file_hash"),
        },
    )
    audit.record_run_start(record)
    audit.record_run_end(record)

    steps = list(artifact.get("steps", []))
    step_names = {str(step.get("name", "")) for step in steps}
    matched_gates: dict[str, list[VerdictContract]] = defaultdict(list)
    synthetic_gates: list[tuple[str, VerdictContract]] = []

    for gate_record in artifact.get("gate_history", []):
        verdict = gate_record_to_verdict(gate_record)
        gate_name = str(gate_record.get("gate_name", "unknown"))
        sample_id = str(gate_record.get("sample_id", "default"))
        target_step = _resolve_gate_step(gate_name, sample_id)
        if target_step in step_names:
            matched_gates[target_step].append(verdict)
        else:
            synthetic_gates.append((target_step, verdict))

    for step in steps:
        step_name = str(step.get("name", "unknown"))
        for step_result in _step_results_for_step(
            step=step,
            started_at=started_at,
            finished_at=finished_at,
            matched_verdicts=matched_gates.get(step_name, []),
        ):
            audit.record_step(run_id, step_result)

    for synthetic_step_id, verdict in synthetic_gates:
        audit.record_step(
            run_id,
            StepResult(
                step_id=synthetic_step_id,
                status=StepStatus.SUCCESS,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=0.0,
                gate_verdict=verdict.to_dict(),
            ),
        )


def run_artifact_to_trajectories(
    artifact: dict[str, Any],
    domain: str = "xrd",
) -> list[GovernedTrajectory]:
    """Convert an AXV2 RunArtifact dict to GovernedTrajectory rows."""
    run_id = str(artifact.get("run_id") or uuid.uuid4().hex[:12])
    started_at = _parse_timestamp(artifact.get("timestamp"))
    gate_history = list(artifact.get("gate_history", []))
    terminal_routes: dict[str, dict[str, Any]] = dict(artifact.get("terminal_routes", {}))
    steps = list(artifact.get("steps", []))

    records_by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in gate_history:
        sample_id = str(record.get("sample_id", "default"))
        records_by_sample[sample_id].append(record)

    sample_ids = set(records_by_sample) | set(terminal_routes)
    if not sample_ids:
        sample_ids = {"default"}

    trajectories: list[GovernedTrajectory] = []
    for sample_id in sorted(sample_ids):
        sample_records = records_by_sample.get(sample_id, [])
        verdicts = [gate_record_to_verdict(record).to_dict() for record in sample_records]
        total = len(sample_records)
        passed = sum(1 for record in sample_records if record.get("status") == "passed")
        gate_pass_rate = passed / total if total else 0.0
        terminal = terminal_routes.get(sample_id)
        rejection_type = _terminal_rejection_type(terminal)
        evaluator_versions = {
            str(record.get("gate_name", "unknown")): "axv2-import"
            for record in sample_records
        }

        trajectories.append(
            GovernedTrajectory(
                trajectory_id=f"{run_id}-{sample_id}",
                run_id=run_id,
                domain=domain,
                prompt=json.dumps({"sample_id": sample_id, "steps": steps}, default=str),
                completion=json.dumps(
                    {"verdicts": verdicts, "terminal": terminal}
                    if terminal is not None
                    else {"verdicts": verdicts},
                    default=str,
                ),
                verdicts=verdicts,
                governance_score=gate_pass_rate,
                gate_pass_rate=gate_pass_rate,
                rejection_type=rejection_type,
                evaluator_versions=evaluator_versions,
                gate_versions=evaluator_versions,
                started_at=started_at,
            )
        )

    return trajectories


def _parse_timestamp(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _resolve_gate_step(gate_name: str, sample_id: str) -> str:
    if gate_name in _GATE_NAME_TO_STEP:
        return _GATE_NAME_TO_STEP[gate_name]
    if "score" in gate_name:
        return "SCORING"
    if "refinement" in gate_name or "refine" in gate_name:
        return "REFINEMENT"
    return f"GATE:{gate_name}:{sample_id}"


def _step_results_for_step(
    *,
    step: dict[str, Any],
    started_at: datetime,
    finished_at: datetime,
    matched_verdicts: list[VerdictContract],
) -> list[StepResult]:
    step_name = str(step.get("name", "unknown"))
    step_status = (
        StepStatus.SUCCESS
        if step.get("status", "success") == "success"
        else StepStatus.FAILED
    )
    duration_ms = float(step.get("duration_ms", 0.0) or 0.0)
    input_hash = str(step.get("input_hash", "") or "")
    output_hash = str(step.get("output_hash", "") or "")

    if not matched_verdicts:
        return [
            StepResult(
                step_id=step_name,
                status=step_status,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                input_hash=input_hash,
                output_hash=output_hash,
            )
        ]
    return [
        StepResult(
            step_id=step_name,
            status=step_status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            input_hash=input_hash,
            output_hash=output_hash,
            gate_verdict=verdict.to_dict(),
        )
        for verdict in matched_verdicts
    ]


def _terminal_rejection_type(terminal: dict[str, Any] | None) -> str | None:
    if terminal is None:
        return None
    return _TERMINAL_VERDICT_TO_REJECTION.get(
        str(terminal.get("verdict", "UNKNOWN")),
        "output_quality",
    )
