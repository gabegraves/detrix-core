import json
from pathlib import Path

from detrix.agentxrd.failure_patterns import (
    FailurePatternSummary,
    build_failure_pattern_corpus,
)

FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"
ROUTER = FIXTURE_ROOT / "pxrd_failure_router_v0"


def test_build_failure_pattern_corpus_preserves_high_and_low_level_patterns(tmp_path):
    output_dir = tmp_path / "patterns"

    summary = build_failure_pattern_corpus(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        row_packets=BINARY20 / "row_packets.jsonl",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        router_decisions=ROUTER / "router_decisions.jsonl",
        router_summary=ROUTER / "summary.json",
        normalized_observations=None,
        output_dir=output_dir,
    )

    assert isinstance(summary, FailurePatternSummary)
    assert summary.row_count == 20
    assert summary.high_level_counts["SUPPORT_ONLY_BLOCKED"] >= 1
    assert summary.high_level_counts["TRUTH_CONFLICT"] >= 1
    assert summary.low_level_counts
    assert summary.judge_gate_conflict_count == 8
    assert summary.sft_positive_count == 0
    assert summary.langfuse_observation_count == 0

    rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 20
    assert all(row["sample_id"] for row in rows)
    assert all(row["deterministic_export_label"] != "sft_positive" for row in rows)
    assert (output_dir / "failure_pattern_summary.json").exists()


def test_build_failure_pattern_corpus_merges_langfuse_observation_hints(tmp_path):
    output_dir = tmp_path / "patterns"
    observations = tmp_path / "normalized_observations.jsonl"
    observations.write_text(
        json.dumps(
            {
                "trace_id": "trace-live-1",
                "sample_id": "dara_2Fe3O4-3Y2O3_1000C_60min",
                "status": "ERROR",
                "failure_hint": "context-window",
                "advisory_only": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_failure_pattern_corpus(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        row_packets=BINARY20 / "row_packets.jsonl",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        router_decisions=ROUTER / "router_decisions.jsonl",
        router_summary=ROUTER / "summary.json",
        normalized_observations=observations,
        output_dir=output_dir,
    )

    assert summary.langfuse_observation_count == 1
    assert summary.joinable_langfuse_trace_count == 1
    assert summary.langfuse_failure_hint_counts["context-window"] == 1
    rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl").read_text().splitlines()
    ]
    assert any(row["low_level_bucket"] == "context-window" for row in rows)


def test_build_failure_pattern_corpus_keeps_unjoinable_langfuse_patterns(tmp_path):
    output_dir = tmp_path / "patterns"
    observations = tmp_path / "normalized_observations.jsonl"
    observations.write_text(
        json.dumps(
            {
                "trace_id": "trace-cache-1",
                "project": "AgentXRD_v2",
                "name": "AgentXRD_v2 session",
                "status": None,
                "failure_hint": "cache_summary_trace",
                "sample_id": None,
                "join_status": "unjoinable_cache_summary",
                "advisory_only": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_failure_pattern_corpus(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        row_packets=BINARY20 / "row_packets.jsonl",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        router_decisions=ROUTER / "router_decisions.jsonl",
        router_summary=ROUTER / "summary.json",
        normalized_observations=observations,
        output_dir=output_dir,
    )

    assert summary.langfuse_observation_count == 1
    assert summary.joinable_langfuse_trace_count == 0
    assert summary.unjoinable_langfuse_trace_count == 1
    assert summary.unjoinable_langfuse_trace_patterns["cache_summary_trace"] == 1
    assert summary.missing_join_key_reasons[
        "metadata_missing_sample_id_or_agentxrd_sample_id"
    ] == 1
    rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 21
    assert any(
        row["sample_id"] == "unjoinable:trace-cache-1"
        and row["high_level_bucket"] == "LANGFUSE_TRACE_UNJOINABLE"
        and row["deterministic_export_label"] == "eval_only"
        and row["langfuse_join_status"] == "unjoinable_cache_summary"
        and row["advisory_only"] is True
        for row in rows
    )
