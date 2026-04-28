from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class FailurePatternRow(BaseModel):
    schema_version: str = "agentxrd_failure_patterns_v0.1"
    sample_id: str
    trace_id: str | None = None
    observation_id: str | None = None
    high_level_bucket: str
    low_level_bucket: str
    blocker_class: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    blocking_fields: list[str] = Field(default_factory=list)
    next_allowed_action: str | None = None
    terminal_verdict: str | None = None
    support_only: bool | None = None
    accept_eligible: bool | None = None
    truth_flags: dict[str, Any] = Field(default_factory=dict)
    wrong_accept_risk: bool | str | None = None
    judge_recommendation: str | None = None
    judge_gate_classification: str | None = None
    deterministic_export_label: str
    source_artifacts: list[str] = Field(default_factory=list)


class FailurePatternSummary(BaseModel):
    schema_version: str = "agentxrd_failure_patterns_v0.1"
    row_count: int
    high_level_counts: dict[str, int]
    low_level_counts: dict[str, int]
    blocker_counts: dict[str, int]
    judge_gate_conflict_count: int
    judge_over_promote_count: int
    sft_positive_count: int
    langfuse_observation_count: int
    langfuse_failure_hint_counts: dict[str, int] = Field(default_factory=dict)
    unjoinable_langfuse_trace_count: int = 0
    unjoinable_langfuse_trace_patterns: dict[str, int] = Field(default_factory=dict)
    trace_cache_miss_reason: str | None = None
    advisory_sources: list[str]
    deterministic_gates_authoritative: bool


def build_failure_pattern_corpus(
    *,
    binary20_artifact: Path,
    row_packets: Path,
    trace_packet_map: Path,
    router_decisions: Path,
    router_summary: Path,
    normalized_observations: Path | None,
    output_dir: Path,
) -> FailurePatternSummary:
    artifact = _load_json(binary20_artifact)
    packets = _load_jsonl(row_packets)
    trace_map = {str(row["sample_id"]): row for row in _load_jsonl(trace_packet_map)}
    router_rows = {str(row["sample_id"]): row for row in _load_jsonl(router_decisions)}
    router = _load_json(router_summary)
    observations = _load_jsonl(normalized_observations) if normalized_observations else []
    observations_by_sample = _observations_by_sample(observations)
    reconciliation = {
        str(row["sample_id"]): row
        for row in artifact["deterministic_gate_reconciliation"]["rows"]
    }
    scores = {str(row["sample_id"]): row for row in artifact["langfuse_score_evidence"]}
    terminals = artifact["terminal_routes"]

    rows: list[FailurePatternRow] = []
    for packet in packets:
        sample_id = str(packet["sample_id"])
        terminal = terminals.get(sample_id, {})
        router_row = router_rows.get(sample_id, {})
        recon = reconciliation.get(sample_id, {})
        score = scores.get(sample_id, {})
        mapped = trace_map.get(sample_id, {})
        observation = observations_by_sample.get(sample_id, {})
        high_level = str(
            router_row.get("blocker_class")
            or packet.get("promotion_audit_bucket")
            or recon.get("classification")
            or _fallback_bucket(terminal)
        )
        low_level = _low_level_bucket(packet, router_row, terminal, recon)

        if observation:
            low_level = str(
                observation.get("failure_hint")
                or observation.get("status")
                or observation.get("name")
                or low_level
            )

        rows.append(
            FailurePatternRow(
                sample_id=sample_id,
                trace_id=score.get("trace_id") or mapped.get("trace_id"),
                observation_id=score.get("observation_id") or mapped.get("observation_id"),
                high_level_bucket=high_level,
                low_level_bucket=low_level,
                blocker_class=router_row.get("blocker_class"),
                reason_codes=list(packet.get("reason_codes", [])),
                blocking_fields=list(router_row.get("blocking_fields", [])),
                next_allowed_action=router_row.get("next_allowed_action"),
                terminal_verdict=terminal.get("verdict") or packet.get("current_verdict"),
                support_only=terminal.get("support_only", packet.get("support_only")),
                accept_eligible=terminal.get("accept_eligible", packet.get("accept_eligible")),
                truth_flags=terminal.get("truth_flags") or packet.get("truth_flags", {}),
                wrong_accept_risk=router_row.get("wrong_accept_risk"),
                judge_recommendation=score.get("judge_recommendation"),
                judge_gate_classification=recon.get("classification"),
                deterministic_export_label=str(
                    recon.get("final_training_export_label", "eval_only")
                ),
                source_artifacts=[
                    str(binary20_artifact),
                    str(row_packets),
                    str(trace_packet_map),
                    str(router_decisions),
                    str(router_summary),
                ],
            )
        )

    unjoinable_observations = [
        obs
        for obs in observations
        if not obs.get("sample_id")
        or str(obs.get("join_status", "")).startswith("unjoinable")
    ]
    for observation in unjoinable_observations:
        trace_id = str(observation.get("trace_id") or "unknown-trace")
        failure_hint = str(
            observation.get("failure_hint")
            or observation.get("status")
            or observation.get("name")
            or "unclassified_trace"
        )
        rows.append(
            FailurePatternRow(
                sample_id=f"unjoinable:{trace_id}",
                trace_id=trace_id,
                high_level_bucket="LANGFUSE_TRACE_UNJOINABLE",
                low_level_bucket=failure_hint,
                reason_codes=["unjoinable_langfuse_cache_summary"],
                deterministic_export_label="eval_only",
                source_artifacts=[str(normalized_observations)]
                if normalized_observations
                else [],
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "failure_patterns.jsonl", [row.model_dump() for row in rows])

    high_counts = Counter(row.high_level_bucket for row in rows)
    low_counts = Counter(row.low_level_bucket for row in rows)
    failure_hint_counts = Counter(
        str(obs.get("failure_hint") or obs.get("status") or "unknown")
        for obs in observations
    )
    unjoinable_counts = Counter(
        row.low_level_bucket
        for row in rows
        if row.high_level_bucket == "LANGFUSE_TRACE_UNJOINABLE"
    )
    summary = FailurePatternSummary(
        row_count=len(rows),
        high_level_counts=dict(high_counts),
        low_level_counts=dict(low_counts),
        blocker_counts=dict(router.get("blocker_counts", {})),
        judge_gate_conflict_count=int(
            artifact["deterministic_gate_reconciliation"]["judge_gate_conflict_count"]
        ),
        judge_over_promote_count=int(
            artifact["deterministic_gate_reconciliation"]["judge_over_promote_count"]
        ),
        sft_positive_count=sum(
            1 for row in rows if row.deterministic_export_label == "sft_positive"
        ),
        langfuse_observation_count=len(observations),
        langfuse_failure_hint_counts=dict(failure_hint_counts),
        unjoinable_langfuse_trace_count=sum(unjoinable_counts.values()),
        unjoinable_langfuse_trace_patterns=dict(unjoinable_counts),
        trace_cache_miss_reason=None
        if observations
        else "no Mission Control Langfuse cache rows matched the selected AgentXRD project aliases",
        advisory_sources=["langfuse_trace_fixture", "langfuse_score_evidence"],
        deterministic_gates_authoritative=True,
    )
    _write_json(output_dir / "failure_pattern_summary.json", summary.model_dump())
    return summary


def _fallback_bucket(terminal: dict[str, Any]) -> str:
    if terminal.get("support_only") is True:
        return "SUPPORT_ONLY_BLOCKED"
    if terminal.get("accept_eligible") is False:
        return "ACCEPT_INELIGIBLE_BLOCKED"
    flags = terminal.get("truth_flags", {})
    if isinstance(flags, dict) and (flags.get("truth_blocked") or flags.get("provisional")):
        return "TRUTH_CONFLICT"
    return "UNCLASSIFIED"


def _low_level_bucket(
    packet: dict[str, Any],
    router_row: dict[str, Any],
    terminal: dict[str, Any],
    recon: dict[str, Any],
) -> str:
    for field in ("reason_codes", "deterministic_blockers"):
        values = packet.get(field)
        if isinstance(values, list) and values:
            return str(values[0])
    fields = router_row.get("blocking_fields")
    if isinstance(fields, list) and fields:
        return str(fields[0])
    reasons = recon.get("block_reasons")
    if isinstance(reasons, list) and reasons:
        return str(reasons[0])
    return str(terminal.get("verdict", "UNKNOWN"))


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _load_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _observations_by_sample(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        sample_id = row.get("sample_id")
        if sample_id and sample_id not in result:
            result[str(sample_id)] = row
    return result


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
