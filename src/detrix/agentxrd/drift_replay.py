from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class DriftReplayReport(BaseModel):
    schema_version: str = "agentxrd_drift_replay_v0.1"
    before: dict[str, int]
    after: dict[str, int]
    deltas: dict[str, int]
    release_blocked: bool
    block_reasons: list[str]


def run_drift_replay(
    *,
    binary20_artifact: Path,
    router_summary: Path,
    output_path: Path,
    proposed_metrics: dict[str, int],
) -> DriftReplayReport:
    artifact = json.loads(binary20_artifact.read_text(encoding="utf-8"))
    router = json.loads(router_summary.read_text(encoding="utf-8"))
    reconciliation = artifact["deterministic_gate_reconciliation"]
    before = {
        "row_count": int(reconciliation["row_count"]),
        "sft_positive_count": int(router.get("sft_positive_count", 0)),
        "judge_gate_conflict_count": int(reconciliation["judge_gate_conflict_count"]),
        "judge_over_promote_count": int(reconciliation["judge_over_promote_count"]),
        "wrong_accept_count": int(router.get("wrong_accept_count", 0)),
        "support_only_accept_violation_count": int(
            router.get("support_only_accept_violation_count", 0)
        ),
        "accept_ineligible_accept_violation_count": int(
            router.get("accept_ineligible_accept_violation_count", 0)
        ),
    }
    after = {**before, **proposed_metrics}
    deltas = {key: after.get(key, 0) - before.get(key, 0) for key in sorted(after)}
    block_reasons = []
    if after.get("wrong_accept_count", 0) > before.get("wrong_accept_count", 0):
        block_reasons.append("wrong_accept_regression")
    if after.get("support_only_accept_violation_count", 0) > 0:
        block_reasons.append("support_only_accept_violation")
    if after.get("accept_ineligible_accept_violation_count", 0) > 0:
        block_reasons.append("accept_ineligible_accept_violation")
    report = DriftReplayReport(
        before=before,
        after=after,
        deltas=deltas,
        release_blocked=bool(block_reasons),
        block_reasons=block_reasons,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return report
