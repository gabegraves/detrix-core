from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from detrix.yc_trace_audit.projects import AUDIT_WINDOW, CORE_PROJECTS, project_for_path


def test_core_projects_are_exact_four() -> None:
    assert set(CORE_PROJECTS) == {
        "detrix-core",
        "agentxrd-v2",
        "parabolahunter",
        "mission-control",
    }


def test_audit_window_covers_feb_1_through_may_5_local() -> None:
    assert AUDIT_WINDOW.start_iso == "2026-02-01T00:00:00-05:00"
    assert AUDIT_WINDOW.end_iso == "2026-05-05T23:59:59-04:00"


def test_project_for_path_resolves_aliases() -> None:
    assert project_for_path(Path("/home/gabriel/Desktop/AgentXRD_v2/docs/x.md")).project_id == "agentxrd-v2"
    assert project_for_path(Path("/home/gabriel/mission-control/my-app")).project_id == "mission-control"


def _write_sample_mission_control_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "mission_control_sample.db"
    con = sqlite3.connect(db_path)
    con.execute(
        "create table langfuse_traces (id text, name text, timestamp text, project text, metadata text, tags text)"
    )
    con.execute(
        "create table coding_sessions (id text, title text, started_at text, ended_at text, cwd text, metadata text)"
    )
    con.execute(
        "insert into langfuse_traces values (?, ?, ?, ?, ?, ?)",
        (
            "trace-detrix",
            "Detrix governed admission trace",
            "2026-05-04T10:00:00-04:00",
            "detrix-core",
            json.dumps({"cwd": "/home/gabriel/Desktop/detrix-core"}),
            "[]",
        ),
    )
    con.execute(
        "insert into langfuse_traces values (?, ?, ?, ?, ?, ?)",
        (
            "trace-cron",
            "nightly cron detrix",
            "2026-05-04T11:00:00-04:00",
            "detrix-core",
            json.dumps({"cwd": "/home/gabriel/Desktop/detrix-core", "source": "cron"}),
            json.dumps(["cron"]),
        ),
    )
    con.execute(
        "insert into langfuse_traces values (?, ?, ?, ?, ?, ?)",
        (
            "trace-old",
            "AgentXRD old trace",
            "2026-01-30T11:00:00-05:00",
            "agentxrd-v2",
            json.dumps({"cwd": "/home/gabriel/Desktop/AgentXRD_v2"}),
            "[]",
        ),
    )
    con.execute(
        "insert into coding_sessions values (?, ?, ?, ?, ?, ?)",
        (
            "coding-ph",
            "ParabolaHunter sniper replay",
            "2026-04-01T09:00:00-04:00",
            "2026-04-01T10:00:00-04:00",
            "/home/gabriel/Desktop/ParabolaHunter",
            "{}",
        ),
    )
    con.commit()
    con.close()
    return db_path


def _write_sample_jsonl_sessions(tmp_path: Path) -> Path:
    root = tmp_path / "sessions"
    codex_dir = root / "codex"
    claude_dir = root / "claude"
    codex_dir.mkdir(parents=True)
    claude_dir.mkdir(parents=True)
    (codex_dir / "codex_session_sample.jsonl").write_text(
        json.dumps(
            {
                "type": "session_meta",
                "session_id": "codex-agentxrd",
                "timestamp": "2026-04-02T12:00:00-04:00",
                "cwd": "/home/gabriel/Desktop/AgentXRD_v2",
                "title": "AgentXRD support-only provenance probe",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (claude_dir / "claude_session_sample.jsonl").write_text(
        json.dumps(
            {
                "sessionId": "claude-mc",
                "timestamp": "2026-04-03T12:00:00-04:00",
                "cwd": "/home/gabriel/mission-control",
                "message": {"content": "Mission Control trace readback repair"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return root


def test_load_mission_control_sources_filters_window_projects_and_cron(tmp_path: Path) -> None:
    from detrix.yc_trace_audit.session_sources import load_mission_control_sources

    db_path = _write_sample_mission_control_db(tmp_path)
    records = load_mission_control_sources(db_path=db_path)

    assert [record.project_id for record in records] == ["detrix-core", "parabolahunter"]
    assert all(not record.cron_excluded for record in records)
    assert {record.source_kind for record in records} == {"langfuse_trace", "coding_session"}


def test_load_jsonl_session_sources_reads_codex_and_claude_metadata(tmp_path: Path) -> None:
    from detrix.yc_trace_audit.session_sources import load_jsonl_session_sources

    session_root = _write_sample_jsonl_sessions(tmp_path)
    records = load_jsonl_session_sources(session_roots=[session_root])

    assert {record.source_kind for record in records} == {"codex_jsonl", "claude_jsonl"}
    assert {record.project_id for record in records} == {"agentxrd-v2", "mission-control"}
    assert all(record.session_id for record in records)
