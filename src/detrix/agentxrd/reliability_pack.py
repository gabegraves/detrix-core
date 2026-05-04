from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

AdmissionDecision = Literal[
    "ACCEPT",
    "SET",
    "SUPPORT_ONLY",
    "REQUEST_MORE_DATA",
    "EVAL_ONLY",
    "HARD_STOP",
]
TrainingRoute = Literal["sft_positive", "dpo_candidate", "eval_only", "excluded"]
LangfuseJoinStatus = Literal["joined", "unjoinable_cache_summary", "missing"]

MAY_STORE_EVAL_ONLY = "MAY_STORE_EVAL_ONLY"
MAY_CREATE_REPLAY_FIXTURE = "MAY_CREATE_REPLAY_FIXTURE"
MAY_EXPORT_DPO_NEGATIVE = "MAY_EXPORT_DPO_NEGATIVE"
MAY_EXPORT_SFT_POSITIVE = "MAY_EXPORT_SFT_POSITIVE"
MAY_UPDATE_LAB_STATE = "MAY_UPDATE_LAB_STATE"
MAY_TRIGGER_NEXT_EXPERIMENT = "MAY_TRIGGER_NEXT_EXPERIMENT"
MAY_PROMOTE_MODEL = "MAY_PROMOTE_MODEL"
MAY_PROMOTE_GATE = "MAY_PROMOTE_GATE"
MUST_REQUEST_MORE_DATA = "MUST_REQUEST_MORE_DATA"
MUST_HUMAN_REVIEW = "MUST_HUMAN_REVIEW"
DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"

BLOCKABLE_CONSEQUENCES = [
    MAY_UPDATE_LAB_STATE,
    MAY_EXPORT_SFT_POSITIVE,
    MAY_PROMOTE_MODEL,
    MAY_PROMOTE_GATE,
]


class AgentXRDEvidenceAuthority(BaseModel):
    deterministic_agentxrd: bool = True
    langfuse_process_trace: bool = False
    llm_or_qwen_judge: bool = False


class AgentXRDRiskConstraints(BaseModel):
    max_false_accepts: int = 0
    max_support_only_promotions: int = 0
    max_unsafe_sft_positive_rows: int = 0
    max_promotion_regressions: int = 0
    min_replay_cases_for_promotion: int = 30


class AgentXRDRiskMetrics(BaseModel):
    false_accept_count: int = 0
    support_only_promotion_count: int = 0
    unsafe_sft_positive_count: int = 0
    promotion_regression_count: int = 0
    accepted_coverage: float = 0.0
    abstention_count: int = 0


class AgentXRDTransitionAdmission(BaseModel):
    schema_version: str = "agentxrd_transition_admission_v0.1"
    transition_id: str
    transition_type: str
    proposer: str
    proposal: dict[str, Any]
    evidence_packet_ref: str
    artifact_hashes: list[str] = Field(default_factory=list)
    domain_policy_version: str = "agentxrd_pxrd_phase_id_v0.1"
    gate_verdicts: list[dict[str, Any]] = Field(default_factory=list)
    replay_status: dict[str, Any] = Field(default_factory=dict)
    admission_decision: AdmissionDecision
    allowed_consequences: list[str]
    blocked_consequences: list[str]
    training_eligibility: TrainingRoute
    reason_codes: list[str]
    promotion_record_ref: str = "promotion_packet.json"


class AgentXRDReliabilityPackRow(BaseModel):
    schema_version: str = "agentxrd_transition_admission_pack_row_v0.1"
    sample_id: str
    transition_id: str
    evidence_authority: AgentXRDEvidenceAuthority = Field(default_factory=AgentXRDEvidenceAuthority)
    langfuse_join_status: LangfuseJoinStatus
    advisory_only: bool
    admission_decision: AdmissionDecision
    training_route: TrainingRoute
    promotion_allowed: bool
    promotion_block_reasons: list[str]
    allowed_consequences: list[str]
    blocked_consequences: list[str]
    reason_codes: list[str]
    blocker_class: str | None = None
    support_only: bool | None = None
    accept_eligible: bool | None = None
    truth_flags: dict[str, Any] = Field(default_factory=dict)
    deterministic_export_label: str
    transition_admission_ref: str


class AgentXRDReliabilityPack(BaseModel):
    schema_version: str = "agentxrd_transition_admission_pack_v0.1"
    generated_at: str
    domain: str = "AgentXRD_v2"
    buyer_facing_name: str = "Materials Characterization Admission Pack"
    pack_inputs: dict[str, str]
    evidence_authority: dict[str, bool]
    risk_constraints: AgentXRDRiskConstraints
    risk_metrics: AgentXRDRiskMetrics
    summary: dict[str, Any]
    rows: list[AgentXRDReliabilityPackRow]
    transition_admissions_ref: str = "transition_admissions.jsonl"
    allowed_consequences_ref: str = "allowed_consequences.jsonl"
    blocked_consequences_ref: str = "blocked_consequences.jsonl"
    failure_pattern_summary_ref: str = "failure_pattern_summary.json"
    next_actions_ref: str = "governed_next_actions.jsonl"
    provenance_ref: str = "provenance_dag.jsonl"
    promotion_packet_ref: str = "promotion_packet.json"
    drift_replay_ref: str = "drift_replay_report.json"


def build_agentxrd_reliability_pack(
    *,
    output_dir: Path,
    pack_inputs: dict[str, Path],
) -> AgentXRDReliabilityPack:
    """Write the AgentXRD transition-admission pack from existing harness artifacts."""
    failure_rows = _load_required_jsonl(output_dir / "failure_patterns.jsonl")
    failure_summary = _load_json(output_dir / "failure_pattern_summary.json")
    observations = _load_required_jsonl(output_dir / "normalized_observations.jsonl")
    promotion_packet = _load_json(output_dir / "promotion_packet.json")
    drift_replay = _load_json(output_dir / "drift_replay_report.json")
    next_actions = {
        str(row.get("sample_id")): row
        for row in _load_required_jsonl(output_dir / "governed_next_actions.jsonl")
    }
    observations_by_sample = {
        str(row["sample_id"]): row for row in observations if row.get("sample_id")
    }

    promotion_allowed = bool(promotion_packet.get("promote"))
    promotion_block_reasons = [str(reason) for reason in promotion_packet.get("block_reasons", [])]
    replay_status = {
        "release_blocked": bool(drift_replay.get("release_blocked")),
        "block_reasons": list(drift_replay.get("block_reasons", [])),
        "deltas": dict(drift_replay.get("deltas", {})),
    }

    admissions: list[AgentXRDTransitionAdmission] = []
    pack_rows: list[AgentXRDReliabilityPackRow] = []
    for row in failure_rows:
        sample_id = str(row["sample_id"])
        langfuse_join_status = _langfuse_join_status(row, observations_by_sample)
        decision, training_route, reasons = derive_admission(row, langfuse_join_status)
        allowed, blocked = _consequences_for(
            decision=decision,
            training_route=training_route,
            promotion_allowed=promotion_allowed,
        )
        row_promotion_allowed = (
            promotion_allowed
            and MAY_PROMOTE_MODEL in allowed
            and MAY_PROMOTE_GATE in allowed
        )
        row_promotion_block_reasons = (
            [] if row_promotion_allowed
            else promotion_block_reasons or ["row_not_promotion_eligible"]
        )
        transition_id = _transition_id(sample_id, decision)
        action = next_actions.get(sample_id, {})
        admission = AgentXRDTransitionAdmission(
            transition_id=transition_id,
            transition_type=_transition_type(decision),
            proposer=_proposer_for(row),
            proposal={
                "claim": _claim_for(row),
                "requested_consequence": [
                    MAY_UPDATE_LAB_STATE,
                    MAY_EXPORT_SFT_POSITIVE,
                    MAY_PROMOTE_MODEL,
                ],
                "next_action": action.get("action_type"),
            },
            evidence_packet_ref=f"failure_patterns.jsonl#{sample_id}",
            gate_verdicts=_gate_verdicts_for(row),
            replay_status=replay_status,
            admission_decision=decision,
            allowed_consequences=allowed,
            blocked_consequences=blocked,
            training_eligibility=training_route,
            reason_codes=reasons,
        )
        admissions.append(admission)
        pack_rows.append(
            AgentXRDReliabilityPackRow(
                sample_id=sample_id,
                transition_id=transition_id,
                evidence_authority=_evidence_authority_for(row, langfuse_join_status),
                langfuse_join_status=langfuse_join_status,
                advisory_only=_advisory_only_for(row),
                admission_decision=decision,
                training_route=training_route,
                promotion_allowed=row_promotion_allowed,
                promotion_block_reasons=row_promotion_block_reasons,
                allowed_consequences=allowed,
                blocked_consequences=blocked,
                reason_codes=reasons,
                blocker_class=row.get("blocker_class") or row.get("high_level_bucket"),
                support_only=row.get("support_only"),
                accept_eligible=row.get("accept_eligible"),
                truth_flags=dict(row.get("truth_flags") or {}),
                deterministic_export_label=str(row.get("deterministic_export_label", "eval_only")),
                transition_admission_ref=f"transition_admissions.jsonl#{transition_id}",
            )
        )

    _write_jsonl(output_dir / "transition_admissions.jsonl", [row.model_dump() for row in admissions])
    _write_jsonl(
        output_dir / "allowed_consequences.jsonl",
        _consequence_rows(admissions, key="allowed_consequences"),
    )
    _write_jsonl(
        output_dir / "blocked_consequences.jsonl",
        _consequence_rows(admissions, key="blocked_consequences"),
    )

    risk_metrics = _risk_metrics(pack_rows, promotion_packet, drift_replay)
    pack = AgentXRDReliabilityPack(
        generated_at=datetime.now(timezone.utc).isoformat(),
        pack_inputs={name: str(path) for name, path in pack_inputs.items()},
        evidence_authority={
            "deterministic_agentxrd_authoritative": True,
            "langfuse_advisory_only": True,
            "model_proposals_advisory_only": True,
        },
        risk_constraints=AgentXRDRiskConstraints(),
        risk_metrics=risk_metrics,
        summary={
            "agentxrd_row_count": sum(
                1 for row in pack_rows if not row.sample_id.startswith("unjoinable:")
            ),
            "failure_pattern_row_count": int(failure_summary.get("row_count", len(failure_rows))),
            "langfuse_observation_count": int(
                failure_summary.get("langfuse_observation_count", len(observations))
            ),
            "joinable_langfuse_trace_count": sum(
                1 for obs in observations if obs.get("sample_id")
            ),
            "unjoinable_langfuse_trace_count": int(
                failure_summary.get("unjoinable_langfuse_trace_count", 0)
            ),
            "wrong_accept_count": int(
                promotion_packet.get("metrics", {}).get("wrong_accept_count", 0)
            ),
            "sft_positive_count": int(
                promotion_packet.get("metrics", {}).get("sft_positive_count", 0)
            ),
            "promotion_allowed": promotion_allowed,
            "promotion_block_reasons": promotion_block_reasons,
            "release_blocked": bool(drift_replay.get("release_blocked")),
            "release_block_reasons": list(drift_replay.get("block_reasons", [])),
            "admission_decision_counts": dict(Counter(row.admission_decision for row in pack_rows)),
            "training_route_counts": dict(Counter(row.training_route for row in pack_rows)),
            "top_blocker_classes": dict(
                Counter(row.blocker_class or "UNCLASSIFIED" for row in pack_rows).most_common(8)
            ),
        },
        rows=pack_rows,
    )
    _write_json(output_dir / "reliability_pack.json", pack.model_dump())
    return pack


def derive_admission(
    row: dict[str, Any], langfuse_join_status: LangfuseJoinStatus
) -> tuple[AdmissionDecision, TrainingRoute, list[str]]:
    reasons: list[str] = []
    export_label = str(row.get("deterministic_export_label", "eval_only"))
    raw_truth_flags = row.get("truth_flags")
    truth_flags = raw_truth_flags if isinstance(raw_truth_flags, dict) else {}
    high_level = str(row.get("high_level_bucket") or "")
    wrong_accept_risk = row.get("wrong_accept_risk")

    if wrong_accept_risk is True or str(wrong_accept_risk).lower() in {"high", "critical"}:
        return "HARD_STOP", "excluded", _ordered_reasons(row, ["wrong_accept_risk"])

    if row.get("support_only") is True:
        reasons.append("support_only")
        return "SUPPORT_ONLY", "eval_only", _ordered_reasons(row, reasons)

    if row.get("accept_eligible") is False:
        reasons.append("accept_eligible_false")
    if truth_flags.get("truth_blocked") is True:
        reasons.append("truth_blocked")
    if truth_flags.get("provisional") is True:
        reasons.append("provisional_truth")
    if "must_not_promote" in row.get("reason_codes", []):
        reasons.append("must_not_promote")
    if reasons:
        route: TrainingRoute = "dpo_candidate" if export_label == "dpo_negative" else "eval_only"
        return "EVAL_ONLY", route, _ordered_reasons(row, reasons)

    if langfuse_join_status == "unjoinable_cache_summary" or high_level == "LANGFUSE_TRACE_UNJOINABLE":
        return (
            "REQUEST_MORE_DATA",
            "eval_only",
            _ordered_reasons(row, ["missing_required_evidence", "langfuse_unjoinable_advisory_only"]),
        )

    missing_markers = {"INSUFFICIENT_ARTIFACT_EVIDENCE", "REQUEST_MORE_DATA"}
    if any(marker in high_level for marker in missing_markers) or row.get("blocking_fields"):
        return "REQUEST_MORE_DATA", "eval_only", _ordered_reasons(row, ["missing_required_evidence"])

    if export_label != "sft_positive":
        return "EVAL_ONLY", "eval_only", _ordered_reasons(row, ["not_training_positive"])

    terminal = str(row.get("terminal_verdict") or "").upper()
    decision: AdmissionDecision = "ACCEPT" if terminal == "ACCEPT" else "SET"
    return decision, "sft_positive", _ordered_reasons(row, ["deterministic_gate_passed"])


def _ordered_reasons(row: dict[str, Any], leading: list[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for reason in [*leading, *row.get("reason_codes", [])]:
        reason_str = str(reason)
        if reason_str and reason_str not in seen:
            ordered.append(reason_str)
            seen.add(reason_str)
    return ordered


def _consequences_for(
    *,
    decision: AdmissionDecision,
    training_route: TrainingRoute,
    promotion_allowed: bool,
) -> tuple[list[str], list[str]]:
    allowed = [MAY_STORE_EVAL_ONLY, MAY_CREATE_REPLAY_FIXTURE]
    blocked = list(BLOCKABLE_CONSEQUENCES)
    if decision in {"REQUEST_MORE_DATA"}:
        allowed.append(MUST_REQUEST_MORE_DATA)
    if decision in {"HARD_STOP"}:
        allowed.append(MUST_HUMAN_REVIEW)
    if decision in {"SUPPORT_ONLY", "EVAL_ONLY"}:
        allowed.append(DIAGNOSTIC_ONLY)
    if training_route == "dpo_candidate":
        allowed.append(MAY_EXPORT_DPO_NEGATIVE)
    if decision in {"ACCEPT", "SET"}:
        allowed.extend([MAY_UPDATE_LAB_STATE, MAY_TRIGGER_NEXT_EXPERIMENT])
        blocked = [item for item in blocked if item != MAY_UPDATE_LAB_STATE]
    if training_route == "sft_positive":
        allowed.append(MAY_EXPORT_SFT_POSITIVE)
        blocked = [item for item in blocked if item != MAY_EXPORT_SFT_POSITIVE]
    if promotion_allowed and decision in {"ACCEPT", "SET"} and training_route == "sft_positive":
        allowed.extend([MAY_PROMOTE_MODEL, MAY_PROMOTE_GATE])
        blocked = [item for item in blocked if item not in {MAY_PROMOTE_MODEL, MAY_PROMOTE_GATE}]
    return _dedupe(allowed), _dedupe(blocked)


def _risk_metrics(
    rows: list[AgentXRDReliabilityPackRow], promotion_packet: dict[str, Any], drift_replay: dict[str, Any]
) -> AgentXRDRiskMetrics:
    metrics = promotion_packet.get("metrics", {})
    agentxrd_count = sum(1 for row in rows if not row.sample_id.startswith("unjoinable:"))
    accepted_count = sum(1 for row in rows if row.admission_decision in {"ACCEPT", "SET"})
    unsafe_sft = sum(
        1
        for row in rows
        if row.training_route == "sft_positive"
        and (
            row.support_only is True
            or row.accept_eligible is False
            or row.truth_flags.get("truth_blocked") is True
            or row.truth_flags.get("provisional") is True
        )
    )
    return AgentXRDRiskMetrics(
        false_accept_count=int(metrics.get("wrong_accept_count", 0)),
        support_only_promotion_count=int(metrics.get("support_only_accept_violation_count", 0)),
        unsafe_sft_positive_count=unsafe_sft
        + int(metrics.get("truth_blocked_positive_count", 0))
        + int(metrics.get("provisional_positive_count", 0)),
        promotion_regression_count=1 if drift_replay.get("release_blocked") else 0,
        accepted_coverage=accepted_count / agentxrd_count if agentxrd_count else 0.0,
        abstention_count=sum(
            1
            for row in rows
            if row.admission_decision in {"REQUEST_MORE_DATA", "EVAL_ONLY", "SUPPORT_ONLY"}
        ),
    )


def _langfuse_join_status(
    row: dict[str, Any], observations_by_sample: dict[str, dict[str, Any]]
) -> LangfuseJoinStatus:
    sample_id = str(row.get("sample_id"))
    if sample_id.startswith("unjoinable:") or row.get("high_level_bucket") == "LANGFUSE_TRACE_UNJOINABLE":
        return "unjoinable_cache_summary"
    if sample_id in observations_by_sample:
        return "joined"
    return "missing"


def _transition_id(sample_id: str, decision: str) -> str:
    safe_sample = sample_id.replace(":", "_").replace("/", "_")
    return f"agentxrd_{safe_sample}_{decision.lower()}"


def _transition_type(decision: AdmissionDecision) -> str:
    return {
        "ACCEPT": "ACCEPT_PHASE_CLAIM",
        "SET": "STORE_GOVERNED_RESULT",
        "SUPPORT_ONLY": "STORE_SUPPORT_ONLY_EVIDENCE",
        "REQUEST_MORE_DATA": "REQUEST_MORE_DATA",
        "EVAL_ONLY": "STORE_EVAL_ONLY",
        "HARD_STOP": "HARD_STOP_UNSAFE_TRANSITION",
    }[decision]


def _proposer_for(row: dict[str, Any]) -> str:
    if str(row.get("sample_id", "")).startswith("unjoinable:"):
        return "langfuse_process_trace"
    return "agentxrd_v2"


def _evidence_authority_for(
    row: dict[str, Any], langfuse_join_status: LangfuseJoinStatus
) -> AgentXRDEvidenceAuthority:
    if _proposer_for(row) == "langfuse_process_trace":
        return AgentXRDEvidenceAuthority(
            deterministic_agentxrd=False,
            langfuse_process_trace=True,
            llm_or_qwen_judge=False,
        )
    return AgentXRDEvidenceAuthority(
        deterministic_agentxrd=True,
        langfuse_process_trace=langfuse_join_status == "joined",
        llm_or_qwen_judge=False,
    )


def _advisory_only_for(row: dict[str, Any]) -> bool:
    return bool(row.get("advisory_only")) or _proposer_for(row) != "agentxrd_v2"


def _claim_for(row: dict[str, Any]) -> str:
    sample_id = row.get("sample_id")
    verdict = row.get("terminal_verdict") or row.get("high_level_bucket")
    return f"Admit AgentXRD row {sample_id} with deterministic verdict {verdict}"


def _gate_verdicts_for(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "agentxrd_deterministic_export_gate",
            "deterministic_export_label": row.get("deterministic_export_label"),
            "reason_codes": row.get("reason_codes", []),
            "support_only": row.get("support_only"),
            "accept_eligible": row.get("accept_eligible"),
            "truth_flags": row.get("truth_flags", {}),
        }
    ]


def _consequence_rows(admissions: list[AgentXRDTransitionAdmission], *, key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for admission in admissions:
        for consequence in getattr(admission, key):
            rows.append(
                {
                    "schema_version": "agentxrd_transition_consequence_v0.1",
                    "transition_id": admission.transition_id,
                    "consequence": consequence,
                    "status": "allowed" if key == "allowed_consequences" else "blocked",
                    "admission_decision": admission.admission_decision,
                    "reason_codes": admission.reason_codes,
                }
            )
    return rows


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _load_required_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Required AgentXRD admission artifact is missing: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
