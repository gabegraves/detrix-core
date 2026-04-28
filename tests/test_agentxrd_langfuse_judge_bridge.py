from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "demo_agentxrd_langfuse_judge_bridge.py"
SCHEMA_VERSION = "agentxrd_langfuse_judge_bridge_v0.1"
NOT_PROVEN = [
    "live Langfuse managed evaluator reliability",
    "Qwen judge reliability",
    "autonomous self-improvement",
    "production AgentXRD readiness",
]


def _run_bridge(tmp_path: Path, artifact: dict[str, Any]) -> tuple[subprocess.CompletedProcess[str], Path]:
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


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_langfuse_bridge_exits_zero_and_preserves_score_evidence(tmp_path: Path) -> None:
    result, output_dir = _run_bridge(tmp_path, _unsafe_artifact_with_scores())

    assert result.returncode == 0, result.stderr + result.stdout
    for filename in {
        "demo_summary.json",
        "trace_scores.jsonl",
        "governed_trajectories.jsonl",
        "audit_gates.jsonl",
        "export_eligibility_report.json",
        "langfuse_judge_report.md",
    }:
        assert (output_dir / filename).exists(), filename
    scores = _jsonl(output_dir / "trace_scores.jsonl")
    assert scores[0]["score_name"] == "pxrd_scientist_judge_v0"
    assert scores[0]["score_value"] == 0.95
    assert scores[0]["score_comment"]


def test_judge_over_promote_is_counted_but_not_exported(tmp_path: Path) -> None:
    result, output_dir = _run_bridge(tmp_path, _unsafe_artifact_with_scores())

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((output_dir / "demo_summary.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "export_eligibility_report.json").read_text(encoding="utf-8"))

    assert summary["row_count"] >= 5
    assert summary["trace_count"] == summary["row_count"]
    assert summary["score_count"] == summary["row_count"]
    assert summary["governed_trajectory_count"] == summary["row_count"]
    assert summary["audit_gate_count"] == summary["row_count"]
    assert summary["judge_over_promote_count"] == 1
    assert summary["judge_gate_conflict_count"] >= 1
    assert summary["sft_positive_count"] == 0
    assert summary["rejected_or_eval_only_count"] == summary["row_count"]
    assert summary["support_only_blocked_count"] == 1
    assert summary["accept_ineligible_blocked_count"] == 3
    assert summary["truth_or_provisional_blocked_count"] == 1
    for item in NOT_PROVEN:
        assert item in summary["not_proven"]
    over_promote = [
        row
        for row in report["rows"]
        if row["judge_gate_classification"] == "judge_over_promotes_blocked_row"
    ]
    assert over_promote
    assert all(row["export_label"] != "sft_positive" for row in over_promote)
    assert all(row["deterministic_block_reasons"] for row in over_promote)


def test_low_score_cannot_demote_clean_safe_fixture(tmp_path: Path) -> None:
    result, output_dir = _run_bridge(tmp_path, _clean_artifact_with_low_score())

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((output_dir / "demo_summary.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "export_eligibility_report.json").read_text(encoding="utf-8"))

    assert summary["row_count"] == 1
    assert summary["score_count"] == 1
    assert summary["sft_positive_count"] == 1
    assert summary["rejected_or_eval_only_count"] == 0
    assert report["rows"][0]["judge_recommendation"] == "unknown"
    assert report["rows"][0]["export_label"] == "sft_positive"


def test_missing_embedded_score_schema_fails_fast(tmp_path: Path) -> None:
    artifact = _unsafe_artifact_with_scores()
    artifact.pop("langfuse_score_schema_version")

    result, _ = _run_bridge(tmp_path, artifact)

    assert result.returncode == 1
    assert "langfuse_score_schema_version" in result.stderr


def test_missing_langfuse_credentials_do_not_block_local_demo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)

    result, output_dir = _run_bridge(tmp_path, _unsafe_artifact_with_scores())

    assert result.returncode == 0, result.stderr + result.stdout
    assert (output_dir / "demo_summary.json").exists()


def test_local_bridge_script_has_no_external_service_launchers() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    lowered = source.lower()

    assert "subprocess" not in source
    assert "Langfuse(" not in source
    assert "import qwen" not in lowered
    assert "qwen(" not in lowered
    assert "benchmark_e2e" not in source
    assert "import ray" not in lowered
    assert "ray." not in lowered
    assert "import bgmn" not in lowered
    assert "bgmn." not in lowered


def _unsafe_artifact_with_scores() -> dict[str, Any]:
    rows = [
        ("support", "UNKNOWN", True, False, "support_only_public_cif_not_accept_eligible", "halt_unknown", ["support_only", "accept_eligible_false"], 0.95, "accept_like"),
        ("set", "SET", False, False, "accept_eligible_false", "downgrade_set", ["accept_eligible_false"], 0.35, "unknown"),
        ("truth", "REQUEST_MORE_DATA", False, True, "truth_or_provisional_blocked", "request_more_data", ["truth_blocked"], 0.2, "request_more_data"),
        ("failed", "UNKNOWN", False, True, "candidate_absent_or_failed", "halt_unknown", ["not_exact_match"], 0.35, "unknown"),
        ("blocked", "UNKNOWN", False, False, "accept_eligible_false", "halt_unknown", ["accept_eligible_false"], 0.35, "unknown"),
    ]
    return _artifact_from_rows(rows)


def _clean_artifact_with_low_score() -> dict[str, Any]:
    rows = [
        (
            "clean",
            "ACCEPT",
            False,
            True,
            "deterministic_gates_reference_eligible",
            "continue",
            [],
            0.0,
            "unknown",
        )
    ]
    return _artifact_from_rows(rows)


def _artifact_from_rows(
    rows: list[tuple[str, str, bool, bool, str, str, list[str], float, str]],
) -> dict[str, Any]:
    gate_history = []
    terminal_routes = {}
    sample_prompts = {}
    traces = []
    scores = []
    reconciliation_rows = []
    for sample_id, verdict, support_only, accept_eligible, reason, decision, reason_codes, score_value, judge_recommendation in rows:
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
        trace_id = f"lf-trace-{sample_id}"
        observation_id = f"lf-obs-{sample_id}"
        block_reasons = []
        if support_only:
            block_reasons.append("support_only")
        if not accept_eligible:
            block_reasons.append("accept_eligible_false")
        if truth_blocked:
            block_reasons.append("truth_or_provisional_blocked")
        if not sft:
            block_reasons.append("training_eligibility_sft_false")
        classification = (
            "deterministic_gate_allows"
            if not block_reasons
            else "judge_over_promotes_blocked_row"
            if judge_recommendation == "accept_like"
            else "judge_requests_more_data"
            if judge_recommendation == "request_more_data"
            else "judge_agrees_block"
        )
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
        traces.append(
            {
                "trace_id": trace_id,
                "observation_id": observation_id,
                "sample_id": sample_id,
                "input": {"prompt": f"Review {sample_id}"},
                "output": {"terminal_verdict": verdict},
                "metadata": {
                    "support_only": support_only,
                    "accept_eligible": accept_eligible,
                    "training_eligibility": eligibility,
                },
            }
        )
        scores.append(
            {
                "trace_id": trace_id,
                "observation_id": observation_id,
                "sample_id": sample_id,
                "score_name": "pxrd_scientist_judge_v0",
                "score_value": score_value,
                "score_comment": f"advisory score for {sample_id}",
                "judge_recommendation": judge_recommendation,
                "must_not_promote": bool(block_reasons),
                "missing_evidence": block_reasons,
            }
        )
        reconciliation_rows.append(
            {
                "trace_id": trace_id,
                "observation_id": observation_id,
                "sample_id": sample_id,
                "score_name": "pxrd_scientist_judge_v0",
                "score_value": score_value,
                "score_comment": f"advisory score for {sample_id}",
                "judge_recommendation": judge_recommendation,
                "deterministic_gate_decision": "blocks" if block_reasons else "allows",
                "deterministic_gate_allows_training": not block_reasons,
                "final_training_export_label": "sft_positive" if sft else "dpo_negative",
                "block_reasons": block_reasons,
                "classification": classification,
            }
        )
        sample_prompts[sample_id] = f"Review {sample_id}"
    return {
        "run_id": "agentxrd-langfuse-fixture",
        "timestamp": "2026-04-28T00:00:00+00:00",
        "workflow_name": "agentxrd_langfuse_judge_bridge_v0",
        "pipeline_version": "test",
        "steps": [{"name": "DETERMINISTIC_GATE", "status": "success", "duration_ms": 0.0}],
        "success": True,
        "total_duration_ms": 0.0,
        "model_versions": {"deterministic_gate": {"name": "fixture", "version": "v0"}},
        "gate_history": gate_history,
        "terminal_routes": terminal_routes,
        "sample_prompts": sample_prompts,
        "langfuse_score_schema_version": SCHEMA_VERSION,
        "langfuse_trace_fixture": traces,
        "langfuse_score_evidence": scores,
        "deterministic_gate_reconciliation": {
            "workflow_name": "agentxrd_langfuse_judge_bridge_v0",
            "row_count": len(rows),
            "score_count": len(rows),
            "judge_gate_conflict_count": sum(
                1
                for row in reconciliation_rows
                if row["classification"] in {"judge_over_promotes_blocked_row", "judge_requests_more_data"}
            ),
            "judge_over_promote_count": sum(
                1 for row in reconciliation_rows if row["classification"] == "judge_over_promotes_blocked_row"
            ),
            "deterministic_gates_authoritative": True,
            "rows": reconciliation_rows,
        },
    }
