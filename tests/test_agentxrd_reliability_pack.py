import json
from pathlib import Path

import pytest

from detrix.agentxrd.drift_replay import DriftReplayReport
from detrix.agentxrd.promotion_packet import AgentXRDPromotionMetrics, build_promotion_packet
from detrix.agentxrd.reliability_pack import (
    MAY_EXPORT_SFT_POSITIVE,
    MAY_PROMOTE_GATE,
    MAY_PROMOTE_MODEL,
    MAY_STORE_EVAL_ONLY,
    MAY_UPDATE_LAB_STATE,
    build_agentxrd_reliability_pack,
    derive_admission,
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _minimal_pack_dir(tmp_path: Path) -> Path:
    _write_jsonl(
        tmp_path / "failure_patterns.jsonl",
        [
            {
                "sample_id": "clean-row",
                "high_level_bucket": "READY",
                "low_level_bucket": "ACCEPT",
                "reason_codes": [],
                "terminal_verdict": "ACCEPT",
                "support_only": False,
                "accept_eligible": True,
                "truth_flags": {"truth_blocked": False, "provisional": False},
                "deterministic_export_label": "sft_positive",
            },
            {
                "sample_id": "support-row",
                "high_level_bucket": "SUPPORT_ONLY_BLOCKED",
                "low_level_bucket": "support_only",
                "reason_codes": ["public_cif_support_only"],
                "terminal_verdict": "UNKNOWN",
                "support_only": True,
                "accept_eligible": False,
                "truth_flags": {"truth_blocked": False, "provisional": False},
                "deterministic_export_label": "eval_only",
            },
            {
                "sample_id": "unjoinable:trace-1",
                "trace_id": "trace-1",
                "high_level_bucket": "LANGFUSE_TRACE_UNJOINABLE",
                "low_level_bucket": "cache_summary_trace",
                "reason_codes": ["unjoinable_langfuse_cache_summary"],
                "deterministic_export_label": "eval_only",
                "advisory_only": True,
            },
        ],
    )
    _write_json(
        tmp_path / "failure_pattern_summary.json",
        {
            "row_count": 3,
            "langfuse_observation_count": 1,
            "joinable_langfuse_trace_count": 0,
            "unjoinable_langfuse_trace_count": 1,
        },
    )
    _write_jsonl(
        tmp_path / "normalized_observations.jsonl",
        [
            {
                "trace_id": "trace-1",
                "sample_id": None,
                "join_status": "unjoinable_cache_summary",
                "advisory_only": True,
            }
        ],
    )
    _write_jsonl(
        tmp_path / "governed_next_actions.jsonl",
        [
            {
                "action_id": "support-row:calibration_only_review",
                "sample_id": "support-row",
                "action_type": "calibration_only_review",
                "training_export_blocked": True,
            }
        ],
    )
    packet = build_promotion_packet(
        AgentXRDPromotionMetrics(
            row_count=2,
            wrong_accept_count=0,
            support_only_accept_violation_count=0,
            accept_ineligible_accept_violation_count=0,
            truth_blocked_positive_count=0,
            provisional_positive_count=0,
            sft_positive_count=1,
        )
    )
    _write_json(tmp_path / "promotion_packet.json", packet.model_dump())
    drift = DriftReplayReport(
        before={"wrong_accept_count": 0, "sft_positive_count": 0},
        after={"wrong_accept_count": 0, "sft_positive_count": 1},
        deltas={"wrong_accept_count": 0, "sft_positive_count": 1},
        release_blocked=False,
        block_reasons=[],
    )
    _write_json(tmp_path / "drift_replay_report.json", drift.model_dump())
    return tmp_path


def test_derive_admission_keeps_domain_state_and_training_route_distinct():
    decision, route, reasons = derive_admission(
        {
            "sample_id": "support-row",
            "support_only": True,
            "accept_eligible": False,
            "truth_flags": {},
            "deterministic_export_label": "eval_only",
            "reason_codes": ["public_cif_support_only"],
        },
        "missing",
    )

    assert decision == "SUPPORT_ONLY"
    assert route == "eval_only"
    assert reasons[:2] == ["support_only", "public_cif_support_only"]


def test_derive_admission_requests_more_data_for_unjoinable_langfuse_trace():
    decision, route, reasons = derive_admission(
        {
            "sample_id": "unjoinable:trace-1",
            "high_level_bucket": "LANGFUSE_TRACE_UNJOINABLE",
            "deterministic_export_label": "eval_only",
            "reason_codes": ["unjoinable_langfuse_cache_summary"],
        },
        "unjoinable_cache_summary",
    )

    assert decision == "REQUEST_MORE_DATA"
    assert route == "eval_only"
    assert reasons[0] == "missing_required_evidence"
    assert "langfuse_unjoinable_advisory_only" in reasons


def test_build_agentxrd_reliability_pack_writes_transition_admission_ledgers(tmp_path):
    output_dir = _minimal_pack_dir(tmp_path)

    pack = build_agentxrd_reliability_pack(
        output_dir=output_dir,
        pack_inputs={"binary20_artifact": Path("detrix_run_artifact.json")},
    )

    assert (output_dir / "reliability_pack.json").exists()
    assert (output_dir / "transition_admissions.jsonl").exists()
    assert (output_dir / "allowed_consequences.jsonl").exists()
    assert (output_dir / "blocked_consequences.jsonl").exists()
    assert pack.buyer_facing_name == "Materials Characterization Admission Pack"
    assert pack.summary["agentxrd_row_count"] == 2
    assert pack.summary["failure_pattern_row_count"] == 3
    assert pack.summary["unjoinable_langfuse_trace_count"] == 1
    assert pack.risk_constraints.max_false_accepts == 0
    assert pack.risk_metrics.unsafe_sft_positive_count == 0

    rows = {row.sample_id: row for row in pack.rows}
    assert rows["clean-row"].admission_decision == "ACCEPT"
    assert MAY_UPDATE_LAB_STATE in rows["clean-row"].allowed_consequences
    assert MAY_EXPORT_SFT_POSITIVE in rows["clean-row"].allowed_consequences
    assert MAY_PROMOTE_MODEL in rows["clean-row"].allowed_consequences
    assert MAY_PROMOTE_GATE in rows["clean-row"].allowed_consequences
    assert rows["clean-row"].promotion_allowed is True
    assert rows["support-row"].admission_decision == "SUPPORT_ONLY"
    assert MAY_STORE_EVAL_ONLY in rows["support-row"].allowed_consequences
    assert MAY_EXPORT_SFT_POSITIVE in rows["support-row"].blocked_consequences
    assert MAY_PROMOTE_MODEL in rows["support-row"].blocked_consequences
    assert MAY_PROMOTE_GATE in rows["support-row"].blocked_consequences
    assert rows["support-row"].promotion_allowed is False
    assert rows["unjoinable:trace-1"].admission_decision == "REQUEST_MORE_DATA"
    assert MAY_PROMOTE_MODEL in rows["unjoinable:trace-1"].blocked_consequences
    assert MAY_PROMOTE_GATE in rows["unjoinable:trace-1"].blocked_consequences
    assert rows["unjoinable:trace-1"].promotion_allowed is False
    assert rows["unjoinable:trace-1"].evidence_authority.deterministic_agentxrd is False
    assert rows["unjoinable:trace-1"].evidence_authority.langfuse_process_trace is True

    admissions = [
        json.loads(line)
        for line in (output_dir / "transition_admissions.jsonl").read_text().splitlines()
    ]
    assert {row["transition_type"] for row in admissions} >= {
        "ACCEPT_PHASE_CLAIM",
        "STORE_SUPPORT_ONLY_EVIDENCE",
        "REQUEST_MORE_DATA",
    }
    assert all("allowed_consequences" in row for row in admissions)
    assert all("blocked_consequences" in row for row in admissions)


def test_build_agentxrd_reliability_pack_fails_closed_when_required_artifact_missing(tmp_path):
    output_dir = _minimal_pack_dir(tmp_path)
    (output_dir / "failure_patterns.jsonl").unlink()

    with pytest.raises(FileNotFoundError, match="failure_patterns.jsonl"):
        build_agentxrd_reliability_pack(
            output_dir=output_dir,
            pack_inputs={"binary20_artifact": Path("detrix_run_artifact.json")},
        )
