from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "demo_binary20_governed_judge_cohort.py"
SCHEMA_VERSION = "binary20_governed_judge_cohort_v0.1"
NOT_PROVEN = [
    "live Langfuse managed evaluator reliability",
    "Qwen judge reliability",
    "autonomous self-improvement",
    "production AgentXRD readiness",
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


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_binary20_demo_exits_zero_and_writes_required_outputs(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _binary20_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    for filename in {
        "demo_summary.json",
        "trace_scores.jsonl",
        "governed_trajectories.jsonl",
        "audit_gates.jsonl",
        "export_eligibility_report.json",
        "judge_gate_disagreement_matrix.json",
        "training_route_recommendations.json",
        "binary20_governed_judge_report.md",
    }:
        assert (output_dir / filename).exists(), filename


def test_binary20_demo_preserves_governance_counts_and_blocks_sft(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _binary20_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((output_dir / "demo_summary.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "export_eligibility_report.json").read_text(encoding="utf-8"))
    matrix = json.loads((output_dir / "judge_gate_disagreement_matrix.json").read_text(encoding="utf-8"))

    assert summary["row_count"] == 20
    assert summary["trace_count"] == 20
    assert summary["score_count"] == 20
    assert summary["governed_trajectory_count"] == 20
    assert summary["audit_gate_count"] == 20
    assert summary["sft_positive_count"] == 0
    assert summary["rejected_or_eval_only_count"] == 20
    assert summary["judge_over_promote_count"] == 1
    assert summary["judge_gate_conflict_count"] >= 1
    assert matrix["classifications"]["judge_over_promotes_blocked_row"] == 1
    assert all(row["export_label"] != "sft_positive" for row in report["rows"])
    for item in NOT_PROVEN:
        assert item in summary["not_proven"]


def test_over_promoted_blocked_rows_keep_deterministic_reasons(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _binary20_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((output_dir / "export_eligibility_report.json").read_text(encoding="utf-8"))
    over_promoted = [
        row
        for row in report["rows"]
        if row["judge_gate_classification"] == "judge_over_promotes_blocked_row"
    ]

    assert len(over_promoted) == 1
    row = over_promoted[0]
    assert row["score_value"] >= 0.9
    assert row["judge_recommendation"] == "accept_like"
    assert row["deterministic_block_reasons"]
    assert row["training_eligibility"]["sft"] is False
    assert row["export_label"] != "sft_positive"


def test_clean_low_score_fixture_can_still_be_sft_positive(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _clean_artifact_with_low_score())

    assert result.returncode == 0, result.stderr + result.stdout
    summary = json.loads((output_dir / "demo_summary.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "export_eligibility_report.json").read_text(encoding="utf-8"))

    assert summary["row_count"] == 1
    assert summary["sft_positive_count"] == 1
    assert summary["rejected_or_eval_only_count"] == 0
    assert report["rows"][0]["judge_recommendation"] == "unknown"
    assert report["rows"][0]["score_value"] == 0.0
    assert report["rows"][0]["export_label"] == "sft_positive"


def test_trace_scores_and_recommendations_are_preserved(tmp_path: Path) -> None:
    result, output_dir = _run_demo(tmp_path, _binary20_artifact())

    assert result.returncode == 0, result.stderr + result.stdout
    scores = _jsonl(output_dir / "trace_scores.jsonl")
    recommendations = json.loads(
        (output_dir / "training_route_recommendations.json").read_text(encoding="utf-8")
    )

    assert len(scores) == 20
    assert scores[0]["score_name"] == "pxrd_binary20_scientist_judge_v0"
    assert scores[0]["score_comment"]
    for key in {
        "eval_only",
        "dpo_negative",
        "future_calibration",
        "future_human_truth_audit",
        "possible_reference_promotion_audit",
    }:
        assert key in recommendations
        assert isinstance(recommendations[key], list)


def test_binary20_demo_script_is_local_only() -> None:
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


def _binary20_artifact() -> dict[str, Any]:
    rows = []
    for index in range(20):
        if index == 0:
            rows.append(
                (
                    f"sample-{index:02d}",
                    "UNKNOWN",
                    True,
                    False,
                    "support_only_public_cif_not_accept_eligible",
                    "halt_unknown",
                    ["support_only", "accept_eligible_false"],
                    0.97,
                    "accept_like",
                    "judge_over_promotes_blocked_row",
                )
            )
        elif index in {1, 2, 3, 4}:
            rows.append(
                (
                    f"sample-{index:02d}",
                    "REQUEST_MORE_DATA",
                    False,
                    True,
                    "truth_or_provisional_blocked",
                    "request_more_data",
                    ["truth_blocked"],
                    0.2,
                    "request_more_data",
                    "judge_requests_more_data",
                )
            )
        elif index in {5, 6, 7}:
            rows.append(
                (
                    f"sample-{index:02d}",
                    "SET",
                    False,
                    False,
                    "ambiguous_set_not_sft_positive",
                    "downgrade_set",
                    ["ambiguous_set", "accept_eligible_false"],
                    0.62,
                    "set_like",
                    "judge_set_pressure_blocked_row",
                )
            )
        else:
            rows.append(
                (
                    f"sample-{index:02d}",
                    "UNKNOWN",
                    False,
                    False,
                    "accept_eligible_false",
                    "halt_unknown",
                    ["accept_eligible_false"],
                    0.35,
                    "unknown",
                    "judge_agrees_block",
                )
            )
    return _artifact_from_rows(rows, schema_version=SCHEMA_VERSION)


def _clean_artifact_with_low_score() -> dict[str, Any]:
    return _artifact_from_rows(
        [
            (
                "clean",
                "ACCEPT_TEST_READY",
                False,
                True,
                "deterministic_gates_reference_eligible",
                "continue",
                [],
                0.0,
                "unknown",
                "deterministic_gate_allows",
            )
        ],
        schema_version=SCHEMA_VERSION,
    )


def _artifact_from_rows(
    rows: list[tuple[str, str, bool, bool, str, str, list[str], float, str, str]],
    *,
    schema_version: str,
) -> dict[str, Any]:
    gate_history = []
    terminal_routes = {}
    sample_prompts = {}
    traces = []
    scores = []
    reconciliation_rows = []
    for (
        sample_id,
        verdict,
        support_only,
        accept_eligible,
        reason,
        decision,
        reason_codes,
        score_value,
        judge_recommendation,
        classification,
    ) in rows:
        truth_blocked = "truth" in reason or "provisional" in reason
        sft = reason == "deterministic_gates_reference_eligible"
        eligibility = {
            "sft": sft,
            "dpo": not sft,
            "grpo": sft,
            "eval_only": not sft,
            "reason": reason,
        }
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
        gate_history.append(
            {
                "sample_id": sample_id,
                "gate_name": "agentxrd_scientist_review_gate_v0",
                "status": "passed" if decision == "continue" else "rejected",
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
            "truth_flags": {
                "truth_grade": "provisional_or_conflicted" if truth_blocked else "benchmark_input",
                "truth_blocked": truth_blocked,
                "provisional": truth_blocked,
            },
            "training_eligibility": eligibility,
        }
        sample_prompts[sample_id] = f"Review {sample_id}"
        traces.append(
            {
                "trace_id": trace_id,
                "observation_id": observation_id,
                "sample_id": sample_id,
                "input": {"prompt": sample_prompts[sample_id]},
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
                "score_name": "pxrd_binary20_scientist_judge_v0",
                "score_value": score_value,
                "score_comment": f"score for {sample_id}",
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
                "score_name": "pxrd_binary20_scientist_judge_v0",
                "score_value": score_value,
                "score_comment": f"score for {sample_id}",
                "judge_recommendation": judge_recommendation,
                "deterministic_gate_decision": "blocks" if block_reasons else "allows",
                "deterministic_gate_allows_training": not block_reasons,
                "final_training_export_label": "sft_positive" if sft else "dpo_negative",
                "block_reasons": block_reasons,
                "classification": classification,
            }
        )
    classifications = {}
    for row in reconciliation_rows:
        classifications[row["classification"]] = classifications.get(row["classification"], 0) + 1
    recommendations = {
        "eval_only": [{"sample_id": sample_id} for sample_id in terminal_routes],
        "dpo_negative": [{"sample_id": sample_id} for sample_id in terminal_routes],
        "future_calibration": [{"sample_id": sample_id} for sample_id in terminal_routes],
        "future_human_truth_audit": [
            {"sample_id": sample_id}
            for sample_id, route in terminal_routes.items()
            if route["truth_flags"]["truth_blocked"]
        ],
        "possible_reference_promotion_audit": [{"sample_id": sample_id} for sample_id in terminal_routes],
        "not_proven": NOT_PROVEN,
    }
    return {
        "run_id": "binary20-test-artifact",
        "timestamp": "2026-04-28T00:00:00+00:00",
        "workflow_name": "binary20_governed_judge_cohort_v0",
        "pipeline_version": "test",
        "steps": [{"name": "DETERMINISTIC_GATE", "status": "success", "duration_ms": 0.0}],
        "success": True,
        "total_duration_ms": 0.0,
        "model_versions": {"deterministic_gate": {"name": "fixture", "version": "v0"}},
        "gate_history": gate_history,
        "terminal_routes": terminal_routes,
        "sample_prompts": sample_prompts,
        "binary20_cohort_schema_version": schema_version,
        "langfuse_score_schema_version": schema_version,
        "langfuse_trace_fixture": traces,
        "langfuse_score_evidence": scores,
        "deterministic_gate_reconciliation": {
            "workflow_name": "binary20_governed_judge_cohort_v0",
            "row_count": len(rows),
            "score_count": len(rows),
            "judge_gate_conflict_count": len(
                [
                    row
                    for row in reconciliation_rows
                    if row["classification"]
                    in {
                        "judge_over_promotes_blocked_row",
                        "judge_requests_more_data",
                        "judge_set_pressure_blocked_row",
                    }
                ]
            ),
            "judge_over_promote_count": classifications.get("judge_over_promotes_blocked_row", 0),
            "rows": reconciliation_rows,
        },
        "judge_gate_disagreement_matrix": {
            "schema_version": schema_version,
            "row_count": len(rows),
            "classifications": classifications,
            "final_training_export_labels": {
                "sft_positive": len([row for row in reconciliation_rows if row["final_training_export_label"] == "sft_positive"]),
                "dpo_negative": len([row for row in reconciliation_rows if row["final_training_export_label"] == "dpo_negative"]),
                "eval_only": 0,
            },
        },
        "training_route_recommendations": recommendations,
    }
