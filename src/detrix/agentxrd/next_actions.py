from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GovernedNextAction(BaseModel):
    schema_version: str = "agentxrd_governed_next_action_v0.1"
    action_id: str
    sample_id: str
    blocker_class: str
    action_type: str
    source_artifacts: list[str] = Field(default_factory=list)
    allowed_commands: list[str]
    kill_criteria: list[str]
    expected_evidence_delta: str
    training_export_blocked: bool = True


ACTION_MAP = {
    "TRUTH_CONFLICT": (
        "truth_audit",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/audit_nb_truth_provenance.py"],
    ),
    "PROVENANCE_GAP": (
        "provenance_join",
        [
            "python /home/gabriel/Desktop/AgentXRD_v2/scripts/reaction_product_candidate_discovery_v0.py"
        ],
    ),
    "AMBIGUOUS_MULTI_HYPOTHESIS": (
        "hypothesis_disambiguation",
        [
            "python /home/gabriel/Desktop/AgentXRD_v2/scripts/reaction_product_candidate_discovery_v0.py"
        ],
    ),
    "REFINEMENT_STRATEGY": (
        "refinement_strategy_probe",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/probe_bimo_mp_candidate_refine.py"],
    ),
    "INSUFFICIENT_ARTIFACT_EVIDENCE": (
        "artifact_evidence_request",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/generate_v5_evidence_report.py"],
    ),
    "SUPPORT_ONLY_BLOCKED": (
        "calibration_only_review",
        [
            "python /home/gabriel/Desktop/AgentXRD_v2/scripts/check_binary_support_manifest_public_cifs.py"
        ],
    ),
}


def build_governed_next_actions(
    failure_patterns: Path,
    output_path: Path,
) -> list[GovernedNextAction]:
    rows = _load_jsonl(failure_patterns)
    actions: list[GovernedNextAction] = []
    for row in rows:
        blocker = str(row.get("blocker_class") or row.get("high_level_bucket"))
        action_type, commands = ACTION_MAP.get(
            blocker,
            (
                "calibration_only_review",
                [
                    "python /home/gabriel/Desktop/AgentXRD_v2/scripts/build_pxrd_failure_router_v0.py"
                ],
            ),
        )
        actions.append(
            GovernedNextAction(
                action_id=f"{row['sample_id']}:{action_type}",
                sample_id=str(row["sample_id"]),
                blocker_class=blocker,
                action_type=action_type,
                source_artifacts=list(row.get("source_artifacts", [])),
                allowed_commands=commands,
                kill_criteria=[
                    "stop if support_only, accept_eligible, or truth status would be mutated",
                    "stop if required evidence artifact is absent",
                    "stop if proposed action would promote training/export eligibility directly",
                ],
                expected_evidence_delta=(
                    f"resolve or narrow {blocker} without changing deterministic gate authority"
                ),
            )
        )
    _write_jsonl(output_path, [action.model_dump() for action in actions])
    return actions


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
