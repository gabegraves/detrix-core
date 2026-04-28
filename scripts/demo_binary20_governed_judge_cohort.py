#!/usr/bin/env python3
"""Replay the binary20 governed judge cohort as Detrix evidence."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

SCHEMA_VERSION = "binary20_governed_judge_cohort_v0.1"
NOT_PROVEN = [
    "live Langfuse managed evaluator reliability",
    "Qwen judge reliability",
    "autonomous self-improvement",
    "production AgentXRD readiness",
    "support-only/public-CIF promotion",
    "calibrated ACCEPT policy",
]
REQUIRED_ARTIFACT_FIELDS = {
    "run_id",
    "timestamp",
    "workflow_name",
    "pipeline_version",
    "steps",
    "success",
    "total_duration_ms",
    "model_versions",
    "gate_history",
    "terminal_routes",
    "binary20_cohort_schema_version",
    "langfuse_score_schema_version",
    "langfuse_score_evidence",
    "langfuse_trace_fixture",
    "deterministic_gate_reconciliation",
    "judge_gate_disagreement_matrix",
    "training_route_recommendations",
}
REQUIRED_SCORE_FIELDS = {
    "trace_id",
    "observation_id",
    "sample_id",
    "score_name",
    "score_value",
    "score_comment",
    "judge_recommendation",
    "must_not_promote",
    "missing_evidence",
}


def _load_artifact(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Artifact not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Artifact is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Artifact must be a JSON object: {path}")
    missing = sorted(REQUIRED_ARTIFACT_FIELDS - set(payload))
    if missing:
        raise ValueError(f"Artifact is missing required fields: {', '.join(missing)}")
    if payload["binary20_cohort_schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            "Unsupported binary20_cohort_schema_version: "
            f"{payload['binary20_cohort_schema_version']}"
        )
    if payload["langfuse_score_schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            "Unsupported langfuse_score_schema_version: "
            f"{payload['langfuse_score_schema_version']}"
        )
    _validate_scores(payload["langfuse_score_evidence"])
    if not isinstance(payload["langfuse_trace_fixture"], list):
        raise ValueError("langfuse_trace_fixture must be a list")
    reconciliation = payload["deterministic_gate_reconciliation"]
    if not isinstance(reconciliation, dict) or not isinstance(reconciliation.get("rows"), list):
        raise ValueError("deterministic_gate_reconciliation.rows must be a list")
    matrix = payload["judge_gate_disagreement_matrix"]
    if not isinstance(matrix, dict) or "classifications" not in matrix:
        raise ValueError("judge_gate_disagreement_matrix.classifications is required")
    routes = payload["training_route_recommendations"]
    if not isinstance(routes, dict):
        raise ValueError("training_route_recommendations must be an object")
    return payload


def _validate_scores(scores: Any) -> None:
    if not isinstance(scores, list):
        raise ValueError("langfuse_score_evidence must be a list")
    for index, score in enumerate(scores):
        if not isinstance(score, dict):
            raise ValueError(f"langfuse_score_evidence[{index}] must be an object")
        missing = sorted(REQUIRED_SCORE_FIELDS - set(score))
        if missing:
            raise ValueError(
                f"langfuse_score_evidence[{index}] missing fields: {', '.join(missing)}"
            )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _load_audit_gates(audit_db: Path, run_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(audit_db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT run_id, step_id, gate_decision, gate_id, gate_verdict_json
               FROM step_executions
               WHERE run_id = ? AND gate_verdict_json IS NOT NULL
               ORDER BY id""",
            (run_id,),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        payload["gate_verdict"] = json.loads(payload.pop("gate_verdict_json"))
        result.append(payload)
    return result


def _terminal_by_sample(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes = artifact.get("terminal_routes", {})
    if not isinstance(routes, dict):
        raise ValueError("terminal_routes must be an object")
    return {str(sample_id): route for sample_id, route in routes.items() if isinstance(route, dict)}


def _completion_payload(trajectory) -> dict[str, Any]:
    try:
        payload = json.loads(trajectory.completion)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sample_id_for_trajectory(trajectory) -> str:
    payload = _completion_payload(trajectory)
    terminal = payload.get("terminal")
    if isinstance(terminal, dict) and terminal.get("sample_id") is not None:
        return str(terminal["sample_id"])
    prefix = f"{trajectory.run_id}-"
    if trajectory.trajectory_id.startswith(prefix):
        return trajectory.trajectory_id[len(prefix) :]
    return trajectory.trajectory_id


def _truth_blocked(row: dict[str, Any]) -> bool:
    flags = row.get("truth_flags", {})
    reason = str(row.get("training_eligibility", {}).get("reason", "")).lower()
    return (
        isinstance(flags, dict)
        and (flags.get("truth_blocked") is True or flags.get("provisional") is True)
    ) or "truth" in reason or "provisional" in reason


def _score_by_sample(scores: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(score["sample_id"]): score for score in scores}


def _reconciliation_by_sample(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = artifact["deterministic_gate_reconciliation"]["rows"]
    return {str(row["sample_id"]): row for row in rows if isinstance(row, dict)}


def _export_rows(trajectories, artifact: dict[str, Any]) -> list[dict[str, Any]]:
    terminals = _terminal_by_sample(artifact)
    scores = _score_by_sample(artifact["langfuse_score_evidence"])
    reconciled = _reconciliation_by_sample(artifact)
    rows: list[dict[str, Any]] = []
    for trajectory in trajectories:
        sample_id = _sample_id_for_trajectory(trajectory)
        terminal = terminals.get(sample_id, {})
        eligibility = terminal.get("training_eligibility", {})
        if not isinstance(eligibility, dict):
            eligibility = {}
        score = scores.get(sample_id, {})
        reconciliation = reconciled.get(sample_id, {})
        deterministic_label = str(reconciliation.get("final_training_export_label", "eval_only"))
        sft_positive = (
            trajectory.rejection_type is None
            and eligibility.get("sft") is True
            and deterministic_label == "sft_positive"
        )
        if sft_positive:
            label = "sft_positive"
        elif eligibility.get("dpo") is True:
            label = "dpo_negative"
        else:
            label = "eval_only"
        rows.append(
            {
                "trajectory_id": trajectory.trajectory_id,
                "sample_id": sample_id,
                "terminal_verdict": terminal.get("verdict"),
                "rejection_type": trajectory.rejection_type,
                "governance_score": trajectory.governance_score,
                "gate_pass_rate": trajectory.gate_pass_rate,
                "support_only": terminal.get("support_only"),
                "accept_eligible": terminal.get("accept_eligible"),
                "truth_flags": terminal.get("truth_flags", {}),
                "training_eligibility": eligibility,
                "trace_id": score.get("trace_id"),
                "observation_id": score.get("observation_id"),
                "score_name": score.get("score_name"),
                "score_value": score.get("score_value"),
                "score_comment": score.get("score_comment"),
                "judge_recommendation": score.get("judge_recommendation"),
                "judge_gate_classification": reconciliation.get("classification"),
                "deterministic_block_reasons": reconciliation.get("block_reasons", []),
                "export_label": label,
            }
        )
    return rows


def _summary(
    *,
    artifact_path: Path,
    artifact: dict[str, Any],
    trajectories,
    audit_gates: list[dict[str, Any]],
    export_rows: list[dict[str, Any]],
    sft_positive_count: int,
) -> dict[str, Any]:
    reconciliation = artifact["deterministic_gate_reconciliation"]
    verdict_counts = Counter(str(row.get("terminal_verdict", "UNKNOWN")) for row in export_rows)
    labels = Counter(str(row.get("export_label", "eval_only")) for row in export_rows)
    return {
        "artifact_path": str(artifact_path),
        "run_id": artifact["run_id"],
        "row_count": len(artifact["terminal_routes"]),
        "trace_count": len(artifact["langfuse_trace_fixture"]),
        "score_count": len(artifact["langfuse_score_evidence"]),
        "governed_trajectory_count": len(trajectories),
        "audit_gate_count": len(audit_gates),
        "sft_positive_count": sft_positive_count,
        "rejected_or_eval_only_count": sum(
            1 for row in export_rows if row["export_label"] != "sft_positive"
        ),
        "judge_gate_conflict_count": int(reconciliation.get("judge_gate_conflict_count", 0)),
        "judge_over_promote_count": int(reconciliation.get("judge_over_promote_count", 0)),
        "support_only_blocked_count": sum(1 for row in export_rows if row.get("support_only") is True),
        "accept_ineligible_blocked_count": sum(
            1 for row in export_rows if row.get("accept_eligible") is False
        ),
        "truth_or_provisional_blocked_count": sum(1 for row in export_rows if _truth_blocked(row)),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "export_label_counts": dict(sorted(labels.items())),
        "strongest_claim": (
            "Detrix can replay the full binary20 AgentXRD judge cohort, preserve "
            "advisory score pressure, and keep training/export eligibility governed "
            "by deterministic PXRD gates."
        ),
        "not_proven": NOT_PROVEN,
        "exit_status": "ok",
    }


def _report(summary: dict[str, Any], export_rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Binary20 Governed Judge Cohort",
            "",
            "## What did Detrix store?",
            "",
            (
                f"Detrix stored {summary['governed_trajectory_count']} governed trajectories, "
                f"{summary['audit_gate_count']} audit gate rows, and "
                f"{summary['score_count']} advisory score rows."
            ),
            "",
            "## Where did judge pressure appear?",
            "",
            (
                f"Judge/gate conflicts: {summary['judge_gate_conflict_count']}; "
                f"over-promotion pressure: {summary['judge_over_promote_count']}."
            ),
            "",
            "## What was export eligibility?",
            "",
            (
                f"SFT-positive rows: {summary['sft_positive_count']}; "
                f"rejected or eval-only rows: {summary['rejected_or_eval_only_count']}."
            ),
            "",
            "## Row labels",
            "",
            "\n".join(
                f"- {row['sample_id']}: {row['judge_recommendation']} -> "
                f"{row['export_label']} ({row['judge_gate_classification']})"
                for row in export_rows
            ),
            "",
            "## Not proven",
            "",
            "\n".join(f"- {item}" for item in NOT_PROVEN),
            "",
        ]
    )


def run_demo(*, artifact_path: Path, output_dir: Path, domain: str, local: bool) -> dict[str, Any]:
    if not local:
        raise ValueError("Only --local replay is supported for the binary20 governed cohort demo")
    artifact = _load_artifact(artifact_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_db = output_dir / "evidence.db"
    audit_db = output_dir / "audit.db"
    for db_path in (evidence_db, audit_db):
        db_path.unlink(missing_ok=True)

    from detrix.adapters.axv2 import project_to_audit_log, run_artifact_to_trajectories
    from detrix.improvement.exporter import TrainingExporter
    from detrix.runtime.audit import AuditLog
    from detrix.runtime.trajectory_store import TrajectoryStore

    audit = AuditLog(str(audit_db))
    store = TrajectoryStore(str(evidence_db))
    project_to_audit_log(artifact, audit)
    trajectories = run_artifact_to_trajectories(artifact, domain=domain)
    for trajectory in trajectories:
        store.append(trajectory)

    audit_gates = _load_audit_gates(audit_db, str(artifact["run_id"]))
    export_rows = _export_rows(trajectories, artifact)
    _write_jsonl(output_dir / "trace_scores.jsonl", artifact["langfuse_score_evidence"])
    _write_jsonl(
        output_dir / "governed_trajectories.jsonl",
        [json.loads(trajectory.model_dump_json()) for trajectory in trajectories],
    )
    _write_jsonl(output_dir / "audit_gates.jsonl", audit_gates)

    exporter = TrainingExporter(store)
    sft_path = Path(exporter.export_sft(str(output_dir / "sft_positive.jsonl"), domain=domain))
    Path(exporter.export_grpo(str(output_dir / "grpo_candidates.jsonl"), domain=domain))
    sft_positive_count = _read_jsonl_count(sft_path)

    _write_json(output_dir / "judge_gate_disagreement_matrix.json", artifact["judge_gate_disagreement_matrix"])
    _write_json(
        output_dir / "training_route_recommendations.json",
        artifact["training_route_recommendations"],
    )
    export_report = {
        "artifact_path": str(artifact_path),
        "run_id": artifact["run_id"],
        "binary20_cohort_schema_version": artifact["binary20_cohort_schema_version"],
        "rows": export_rows,
    }
    _write_json(output_dir / "export_eligibility_report.json", export_report)
    summary = _summary(
        artifact_path=artifact_path,
        artifact=artifact,
        trajectories=trajectories,
        audit_gates=audit_gates,
        export_rows=export_rows,
        sft_positive_count=sft_positive_count,
    )
    _write_json(output_dir / "demo_summary.json", summary)
    (output_dir / "binary20_governed_judge_report.md").write_text(
        _report(summary, export_rows), encoding="utf-8"
    )
    _write_harness_artifacts_if_available(artifact_path=artifact_path, output_dir=output_dir)
    return summary


def _write_harness_artifacts_if_available(*, artifact_path: Path, output_dir: Path) -> None:
    cohort_dir = artifact_path.parent
    diagnostics_dir = cohort_dir.parent
    row_packets = cohort_dir / "row_packets.jsonl"
    trace_packet_map = cohort_dir / "trace_to_pxrd_packet_map.jsonl"
    router_dir = diagnostics_dir / "pxrd_failure_router_v0"
    router_decisions = router_dir / "router_decisions.jsonl"
    router_summary = router_dir / "summary.json"
    required = [row_packets, trace_packet_map, router_decisions, router_summary]
    if not all(path.exists() for path in required):
        return

    from detrix.agentxrd.drift_replay import run_drift_replay
    from detrix.agentxrd.failure_patterns import build_failure_pattern_corpus
    from detrix.agentxrd.next_actions import build_governed_next_actions
    from detrix.agentxrd.promotion_packet import (
        AgentXRDPromotionMetrics,
        build_promotion_packet,
    )
    from detrix.agentxrd.provenance import build_agentxrd_provenance_dag

    normalized_observations = output_dir / "normalized_observations.jsonl"
    if not normalized_observations.exists():
        _write_jsonl(normalized_observations, [])
    summary = build_failure_pattern_corpus(
        binary20_artifact=artifact_path,
        row_packets=row_packets,
        trace_packet_map=trace_packet_map,
        router_decisions=router_decisions,
        router_summary=router_summary,
        normalized_observations=normalized_observations,
        output_dir=output_dir,
    )
    (output_dir / "trace_to_agentxrd_packet_map.jsonl").write_text(
        trace_packet_map.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    build_governed_next_actions(
        output_dir / "failure_patterns.jsonl",
        output_dir / "governed_next_actions.jsonl",
    )
    build_agentxrd_provenance_dag(
        detrix_artifact=artifact_path,
        trace_packet_map=trace_packet_map,
        row_packets=row_packets,
        output_path=output_dir / "provenance_dag.jsonl",
    )
    router = json.loads(router_summary.read_text(encoding="utf-8"))
    packet = build_promotion_packet(
        AgentXRDPromotionMetrics(
            row_count=summary.row_count,
            wrong_accept_count=int(router.get("wrong_accept_count", 0)),
            support_only_accept_violation_count=int(
                router.get("support_only_accept_violation_count", 0)
            ),
            accept_ineligible_accept_violation_count=int(
                router.get("accept_ineligible_accept_violation_count", 0)
            ),
            truth_blocked_positive_count=0,
            provisional_positive_count=0,
            sft_positive_count=summary.sft_positive_count,
        )
    )
    _write_json(output_dir / "promotion_packet.json", packet.model_dump())
    run_drift_replay(
        binary20_artifact=artifact_path,
        router_summary=router_summary,
        output_path=output_dir / "drift_replay_report.json",
        proposed_metrics={"sft_positive_count": summary.sft_positive_count},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--domain", default="xrd")
    parser.add_argument("--local", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_demo(
            artifact_path=args.artifact,
            output_dir=args.output_dir,
            domain=args.domain,
            local=args.local,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
