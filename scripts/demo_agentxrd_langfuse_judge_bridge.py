#!/usr/bin/env python3
"""Replay AgentXRD Langfuse-style judge scores as governed Detrix evidence."""

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

SCHEMA_VERSION = "agentxrd_langfuse_judge_bridge_v0.1"
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
    "langfuse_score_schema_version",
    "langfuse_score_evidence",
    "langfuse_trace_fixture",
    "deterministic_gate_reconciliation",
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


def _sample_id_for_trajectory(trajectory, terminals: dict[str, dict[str, Any]]) -> str:
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
        sample_id = _sample_id_for_trajectory(trajectory, terminals)
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
        elif eligibility.get("dpo") is True and trajectory.rejection_type == "output_quality":
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
    verdict_counts = Counter(str(row.get("terminal_verdict", "UNKNOWN")) for row in export_rows)
    row_count = len(artifact["terminal_routes"])
    reconciliation = artifact["deterministic_gate_reconciliation"]
    return {
        "artifact_path": str(artifact_path),
        "run_id": artifact["run_id"],
        "row_count": row_count,
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
        "strongest_claim": (
            "Detrix can ingest Langfuse-style LLM-as-a-Judge score evidence for AgentXRD "
            "traces while preserving deterministic PXRD gate authority over training/export eligibility."
        ),
        "not_proven": NOT_PROVEN,
        "exit_status": "ok",
    }


def _report(summary: dict[str, Any], export_rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# AgentXRD Langfuse Judge Bridge",
            "",
            "## What did Langfuse-style scoring add?",
            "",
            (
                f"The demo preserved {summary['score_count']} advisory score rows and "
                f"{summary['trace_count']} trace fixtures."
            ),
            "",
            "## What did deterministic gates decide?",
            "",
            (
                f"Deterministic AgentXRD gates produced {summary['audit_gate_count']} audit rows. "
                f"SFT-positive count is {summary['sft_positive_count']}."
            ),
            "",
            "## Judge/gate disagreements",
            "",
            (
                f"Judge/gate conflicts: {summary['judge_gate_conflict_count']}; "
                f"over-promoted blocked rows: {summary['judge_over_promote_count']}."
            ),
            "",
            "## Export eligibility",
            "",
            "\n".join(
                f"- {row['sample_id']}: score={row['score_value']} "
                f"{row['judge_recommendation']} -> {row['export_label']} "
                f"({row['judge_gate_classification']})"
                for row in export_rows
            ),
            "",
            "## Strongest claim",
            "",
            summary["strongest_claim"],
            "",
            "## Not proven",
            "",
            "\n".join(f"- {item}" for item in NOT_PROVEN),
            "",
        ]
    )


def run_demo(*, artifact_path: Path, output_dir: Path, domain: str, local: bool) -> dict[str, Any]:
    if not local:
        raise ValueError("Only --local replay is supported for this Langfuse score bridge demo")
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

    export_report = {
        "artifact_path": str(artifact_path),
        "run_id": artifact["run_id"],
        "langfuse_score_schema_version": artifact["langfuse_score_schema_version"],
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
    (output_dir / "langfuse_judge_report.md").write_text(
        _report(summary, export_rows), encoding="utf-8"
    )
    return summary


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
