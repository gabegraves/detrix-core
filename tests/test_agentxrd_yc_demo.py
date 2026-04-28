from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "demo_agentxrd_judge_yc.py"
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


def _run_demo(tmp_path: Path, artifact: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str], Path]:
    artifact_path = tmp_path / "artifact.json"
    output_dir = tmp_path / "demo"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--artifact",
            str(artifact_path),
            "--output-dir",
            str(output_dir),
            "--local",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, output_dir


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_demo_script_exits_zero_and_writes_required_reports(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _unsafe_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    for filename in {
        "demo_summary.json",
        "governed_trajectories.jsonl",
        "audit_gates.jsonl",
        "export_eligibility_report.json",
        "yc_demo_report.md",
    }:
        assert (output_dir / filename).exists(), filename
    report = (output_dir / "yc_demo_report.md").read_text(encoding="utf-8")
    for question in REPORT_QUESTIONS:
        assert question in report


def test_demo_summary_blocks_unsafe_agentxrd_rows(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _unsafe_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((output_dir / "demo_summary.json").read_text(encoding="utf-8"))
    assert summary["row_count"] >= 5
    assert summary["governed_trajectory_count"] == summary["row_count"]
    assert summary["audit_gate_count"] == summary["row_count"]
    assert summary["sft_positive_count"] == 0
    assert summary["rejected_or_eval_only_count"] == summary["row_count"]
    assert summary["support_only_blocked_count"] == 1
    assert summary["accept_ineligible_blocked_count"] == 3
    assert summary["truth_or_provisional_blocked_count"] == 1
    assert summary["deterministic_gate_conflict_count"] == 1
    for item in NOT_PROVEN:
        assert item in summary["not_proven"]


def test_demo_outputs_one_trajectory_gate_and_eligibility_row_per_input(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _unsafe_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    trajectories = _read_jsonl(output_dir / "governed_trajectories.jsonl")
    gates = _read_jsonl(output_dir / "audit_gates.jsonl")
    eligibility = json.loads(
        (output_dir / "export_eligibility_report.json").read_text(encoding="utf-8")
    )

    assert len(trajectories) == 5
    assert len(gates) == 5
    assert len(eligibility["rows"]) == 5
    by_sample = {row["sample_id"]: row for row in eligibility["rows"]}
    assert by_sample["support"]["rejection_type"] == "output_quality"
    assert by_sample["support"]["training_eligibility"]["reason"] == "support_only_public_cif_not_accept_eligible"
    assert by_sample["truth"]["rejection_type"] == "input_quality"
    assert by_sample["set"]["training_eligibility"]["reason"] == "accept_eligible_false"
    assert all(row["export_label"] != "sft_positive" for row in eligibility["rows"])


def test_clean_reference_fixture_can_still_be_sft_positive(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _clean_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((output_dir / "demo_summary.json").read_text(encoding="utf-8"))
    eligibility = json.loads(
        (output_dir / "export_eligibility_report.json").read_text(encoding="utf-8")
    )

    assert summary["row_count"] == 1
    assert summary["sft_positive_count"] == 1
    assert summary["rejected_or_eval_only_count"] == 0
    assert eligibility["rows"][0]["export_label"] == "sft_positive"
    assert eligibility["rows"][0]["training_eligibility"]["sft"] is True


def test_missing_artifact_fails_fast_with_clear_message(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--artifact",
            str(missing),
            "--output-dir",
            str(tmp_path / "demo"),
            "--local",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Artifact not found" in result.stderr


def _unsafe_artifact() -> dict[str, Any]:
    rows = [
        ("support", "UNKNOWN", True, False, "support_only_public_cif_not_accept_eligible", "halt_unknown", ["support_only", "accept_eligible_false"]),
        ("set", "SET", False, False, "accept_eligible_false", "downgrade_set", ["ambiguous_set", "accept_eligible_false"]),
        ("truth", "REQUEST_MORE_DATA", False, True, "truth_or_provisional_blocked", "request_more_data", ["provisional_labels", "truth_blocked"]),
        ("failed", "UNKNOWN", False, True, "candidate_absent_or_failed", "halt_unknown", ["not_exact_match"]),
        ("conflict", "UNKNOWN", False, False, "accept_eligible_false", "halt_unknown", ["accept_eligible_false", "accept_ready_despite_deterministic_blockers"]),
    ]
    return _artifact_from_rows(rows)


def _clean_artifact() -> dict[str, Any]:
    return _artifact_from_rows(
        [("clean", "ACCEPT", False, True, "deterministic_gates_reference_eligible", "continue", [])]
    )


def _artifact_from_rows(rows: list[tuple[str, str, bool, bool, str, str, list[str]]]) -> dict[str, Any]:
    gate_history = []
    terminal_routes = {}
    sample_prompts = {}
    for sample_id, verdict, support_only, accept_eligible, reason, decision, reason_codes in rows:
        truth_blocked = "truth" in reason or "provisional" in reason
        sft = reason == "deterministic_gates_reference_eligible"
        eligibility = {
            "sft": sft,
            "dpo": not sft,
            "grpo": sft,
            "eval_only": not sft,
            "reason": reason,
        }
        status = "passed" if decision == "continue" else "rejected"
        gate_history.append(
            {
                "sample_id": sample_id,
                "gate_name": "agentxrd_scientist_review_gate_v0",
                "status": status,
                "decision": decision,
                "reason_codes": reason_codes,
                "input_hash": f"hash-{sample_id}",
                "evidence": {
                    "sample_id": sample_id,
                    "current_verdict": verdict,
                    "support_only": support_only,
                    "accept_eligible": accept_eligible,
                    "truth_grade": "provisional_or_conflicted" if truth_blocked else "benchmark_input",
                    "training_eligibility": eligibility,
                },
            }
        )
        terminal_routes[sample_id] = {
            "sample_id": sample_id,
            "verdict": verdict,
            "support_only": support_only,
            "accept_eligible": accept_eligible,
            "truth_flags": {"truth_blocked": truth_blocked, "provisional": truth_blocked},
            "training_eligibility": eligibility,
        }
        sample_prompts[sample_id] = f"Review {sample_id}"
    return {
        "run_id": "agentxrd-yc-fixture",
        "timestamp": "2026-04-28T00:00:00+00:00",
        "workflow_name": "agentxrd_detrix_scientist_judge_yc_demo_v0",
        "pipeline_version": "test",
        "steps": [{"name": "DETERMINISTIC_GATE", "status": "success", "duration_ms": 0.0}],
        "success": True,
        "total_duration_ms": 0.0,
        "model_versions": {"deterministic_gate": {"name": "fixture", "version": "v0"}},
        "gate_history": gate_history,
        "terminal_routes": terminal_routes,
        "sample_prompts": sample_prompts,
    }
