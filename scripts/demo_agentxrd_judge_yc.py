#!/usr/bin/env python3
"""Replay an AgentXRD scientist-judge artifact as a local Detrix YC demo."""

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

REPORT_QUESTIONS = [
    "What did AgentXRD produce?",
    "What did the judge recommend?",
    "What did deterministic gates allow/block?",
    "What did Detrix store?",
    "What was export/training eligibility?",
    "Why is this not generic trace logging?",
    "What remains before Qwen/Langfuse/self-improvement claims?",
]
NOT_PROVEN = [
    "Qwen judge reliability",
    "live Langfuse ingestion",
    "autonomous self-improvement",
    "AgentXRD production readiness",
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
    return payload


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
    result = []
    for row in rows:
        payload = dict(row)
        payload["gate_verdict"] = json.loads(payload.pop("gate_verdict_json"))
        result.append(payload)
    return result


def _terminal_by_sample(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes = artifact.get("terminal_routes", {})
    if not isinstance(routes, dict):
        raise ValueError("Artifact terminal_routes must be an object")
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


def _eligibility_rows(trajectories, terminals: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for trajectory in trajectories:
        sample_id = _sample_id_for_trajectory(trajectory, terminals)
        terminal = terminals.get(sample_id, {})
        eligibility = terminal.get("training_eligibility", {})
        if not isinstance(eligibility, dict):
            eligibility = {}
        sft_positive = trajectory.rejection_type is None and eligibility.get("sft") is True
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
                "export_label": label,
            }
        )
    return rows


def _count_truth_blocked(rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        flags = row.get("truth_flags", {})
        reason = str(row.get("training_eligibility", {}).get("reason", ""))
        if (
            isinstance(flags, dict)
            and (flags.get("truth_blocked") is True or flags.get("provisional") is True)
        ) or "truth" in reason or "provisional" in reason:
            count += 1
    return count


def _conflict_count(artifact: dict[str, Any]) -> int:
    count = 0
    for gate in artifact.get("gate_history", []):
        if not isinstance(gate, dict):
            continue
        codes = [str(code) for code in gate.get("reason_codes", [])]
        if any("conflict" in code or "despite" in code for code in codes):
            count += 1
    return count


def _summary(
    *,
    artifact_path: Path,
    artifact: dict[str, Any],
    trajectories,
    audit_gates: list[dict[str, Any]],
    eligibility_rows: list[dict[str, Any]],
    sft_positive_count: int,
) -> dict[str, Any]:
    verdict_counts = Counter(str(row.get("terminal_verdict", "UNKNOWN")) for row in eligibility_rows)
    training_counts = Counter()
    for row in eligibility_rows:
        eligibility = row.get("training_eligibility", {})
        if isinstance(eligibility, dict):
            for key in ("sft", "dpo", "grpo", "eval_only"):
                training_counts[f"{key}_{bool(eligibility.get(key))}"] += 1
            training_counts[f"reason:{eligibility.get('reason', 'unknown')}"] += 1
    row_count = len(artifact.get("terminal_routes", {}))
    return {
        "artifact_path": str(artifact_path),
        "run_id": artifact["run_id"],
        "row_count": row_count,
        "governed_trajectory_count": len(trajectories),
        "audit_gate_count": len(audit_gates),
        "sft_positive_count": sft_positive_count,
        "rejected_or_eval_only_count": sum(
            1 for row in eligibility_rows if row["export_label"] != "sft_positive"
        ),
        "deterministic_gate_conflict_count": _conflict_count(artifact),
        "support_only_blocked_count": sum(1 for row in eligibility_rows if row.get("support_only") is True),
        "accept_ineligible_blocked_count": sum(
            1 for row in eligibility_rows if row.get("accept_eligible") is False
        ),
        "truth_or_provisional_blocked_count": _count_truth_blocked(eligibility_rows),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "training_eligibility_counts": dict(sorted(training_counts.items())),
        "strongest_claim": (
            "Detrix now has a replayable local demo proving that AgentXRD scientist-judge "
            "traces become governed trajectories only after explicit deterministic PXRD "
            "eligibility gates decide whether they are training/export eligible."
        ),
        "not_proven": NOT_PROVEN,
        "exit_status": "ok",
    }


def _report(summary: dict[str, Any], eligibility_rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# AgentXRD Scientist Judge YC Demo",
            "",
            f"## 1. {REPORT_QUESTIONS[0]}",
            "",
            (
                f"AgentXRD produced {summary['row_count']} scientist-judge trace rows with "
                "PXRD gate evidence, terminal routes, sample prompts, and explicit training eligibility."
            ),
            "",
            f"## 2. {REPORT_QUESTIONS[1]}",
            "",
            "Judge recommendations are stored as advisory context inside the AgentXRD artifact.",
            "",
            f"## 3. {REPORT_QUESTIONS[2]}",
            "",
            (
                f"Deterministic gates produced {summary['audit_gate_count']} audit gate rows and kept "
                f"{summary['rejected_or_eval_only_count']} rows rejected or eval-only."
            ),
            "",
            f"## 4. {REPORT_QUESTIONS[3]}",
            "",
            (
                f"Detrix stored {summary['governed_trajectory_count']} governed trajectories plus "
                "gate verdict JSON in the local audit store."
            ),
            "",
            f"## 5. {REPORT_QUESTIONS[4]}",
            "",
            (
                f"SFT-positive count is {summary['sft_positive_count']}. Export labels are: "
                + ", ".join(f"{row['sample_id']}={row['export_label']}" for row in eligibility_rows)
                + "."
            ),
            "",
            f"## 6. {REPORT_QUESTIONS[5]}",
            "",
            (
                "The demo does not stop at traces. It records domain gate outcomes, rejection reasons, "
                "training eligibility, and audit evidence before any positive export label is assigned."
            ),
            "",
            f"## 7. {REPORT_QUESTIONS[6]}",
            "",
            "\n".join(f"- {item}" for item in NOT_PROVEN),
            "",
        ]
    )


def run_demo(*, artifact_path: Path, output_dir: Path, domain: str, local: bool) -> dict[str, Any]:
    if not local:
        raise ValueError("Only --local replay is supported for this deterministic YC demo")
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

    terminals = _terminal_by_sample(artifact)
    audit_gates = _load_audit_gates(audit_db, str(artifact["run_id"]))
    eligibility_rows = _eligibility_rows(trajectories, terminals)
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
        "rows": eligibility_rows,
    }
    _write_json(output_dir / "export_eligibility_report.json", export_report)

    summary = _summary(
        artifact_path=artifact_path,
        artifact=artifact,
        trajectories=trajectories,
        audit_gates=audit_gates,
        eligibility_rows=eligibility_rows,
        sft_positive_count=sft_positive_count,
    )
    _write_json(output_dir / "demo_summary.json", summary)
    (output_dir / "yc_demo_report.md").write_text(
        _report(summary, eligibility_rows), encoding="utf-8"
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
