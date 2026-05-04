import json
import sqlite3

from detrix.agentxrd.langfuse_importer import (
    MissionControlLangfuseSource,
    import_agentxrd_langfuse_traces,
)


def test_importer_reads_mission_control_cache_without_live_calls(tmp_path):
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

    source = MissionControlLangfuseSource(db_path=db_path, live_enabled=False)
    report = import_agentxrd_langfuse_traces(
        source=source,
        project="AgentXRD_v2",
        output_dir=tmp_path / "out",
        limit=50,
    )

    assert report.live_enabled is False
    assert report.raw_trace_count == 1
    assert report.normalized_observation_count == 1
    assert report.project_aliases == ["AgentXRD_v2", "mc-agentxrd_v2"]
    assert report.joinable_trace_count == 0
    assert report.unjoinable_trace_count == 1
    assert report.missing_join_key_reasons == {
        "metadata_missing_sample_id_or_agentxrd_sample_id": 1
    }
    assert report.advisory_only is True
    assert (tmp_path / "out" / "raw_langfuse_traces.jsonl").exists()
    observations = [
        json.loads(line)
        for line in (tmp_path / "out" / "normalized_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert observations[0]["join_status"] == "unjoinable_cache_summary"
    assert (
        observations[0]["missing_join_key_reason"]
        == "metadata_missing_sample_id_or_agentxrd_sample_id"
    )
    assert observations[0]["sample_id"] is None
    assert observations[0]["failure_hint"] == "AgentXRD_v2 session"


def test_importer_counts_joinable_sample_metadata(tmp_path):
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
                "trace-joined",
                "langfuse-general",
                "AgentXRD_v2 sample",
                "AgentXRD_v2",
                "qwen-test",
                10,
                5,
                0.0,
                123,
                "OK",
                "2026-04-28T00:00:00Z",
                json.dumps({"sample_id": "sample-1"}),
                "2026-04-28T00:00:01Z",
            ),
        )

    report = import_agentxrd_langfuse_traces(
        source=MissionControlLangfuseSource(db_path=db_path, live_enabled=False),
        project="AgentXRD_v2",
        output_dir=tmp_path / "out",
    )

    assert report.joinable_trace_count == 1
    assert report.unjoinable_trace_count == 0
    observations = [
        json.loads(line)
        for line in (tmp_path / "out" / "normalized_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert observations[0]["sample_id"] == "sample-1"
    assert observations[0]["join_status"] == "joined"
    assert observations[0]["advisory_only"] is True
