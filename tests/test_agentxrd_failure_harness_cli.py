import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from detrix.cli.main import cli

FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"
ROUTER = FIXTURE_ROOT / "pxrd_failure_router_v0"


def test_agentxrd_harness_cli_emits_required_artifacts(tmp_path):
    db_path = tmp_path / "mc.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE langfuse_traces (
                id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL,
                name TEXT,
                project TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_cost REAL,
                latency_ms INTEGER,
                status TEXT,
                started_at TEXT,
                metadata TEXT,
                ingested_at TEXT
            )"""
        )
        conn.execute(
            """INSERT INTO langfuse_traces
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "trace-1",
                "langfuse-general",
                "AgentXRD_v2 session",
                "AgentXRD_v2",
                "qwen-test",
                10,
                5,
                0.0,
                123,
                None,
                "2026-04-28T00:00:00Z",
                json.dumps(
                    {
                        "cwd": "/home/gabriel/Desktop/AgentXRD_v2",
                        "source": "codex",
                        "model": "gpt-5.4",
                    }
                ),
                "2026-04-28T00:00:01Z",
            ),
        )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "agentxrd",
            "build-harness-evidence",
            "--binary20-artifact",
            str(BINARY20 / "detrix_run_artifact.json"),
            "--row-packets",
            str(BINARY20 / "row_packets.jsonl"),
            "--trace-packet-map",
            str(BINARY20 / "trace_to_pxrd_packet_map.jsonl"),
            "--router-decisions",
            str(ROUTER / "router_decisions.jsonl"),
            "--router-summary",
            str(ROUTER / "summary.json"),
            "--mission-control-db",
            str(db_path),
            "--langfuse-project",
            "AgentXRD_v2",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    for name in [
        "failure_patterns.jsonl",
        "failure_pattern_summary.json",
        "raw_langfuse_traces.jsonl",
        "normalized_observations.jsonl",
        "trace_to_agentxrd_packet_map.jsonl",
        "governed_next_actions.jsonl",
        "provenance_dag.jsonl",
        "promotion_packet.json",
        "drift_replay_report.json",
    ]:
        assert (tmp_path / name).exists()
    packet = json.loads((tmp_path / "promotion_packet.json").read_text())
    assert packet["promote"] is False
    summary = json.loads((tmp_path / "failure_pattern_summary.json").read_text())
    assert summary["langfuse_observation_count"] == 1
    assert summary["unjoinable_langfuse_trace_count"] == 1
    assert summary["unjoinable_langfuse_trace_patterns"]["AgentXRD_v2 session"] == 1
