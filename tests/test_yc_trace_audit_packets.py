from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from detrix.cli.main import cli
from detrix.yc_trace_audit.schema import AuditUnit


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


def _sample_unit(unit_id: str, project_id: str) -> AuditUnit:
    return AuditUnit(
        unit_id=unit_id,
        project_id=project_id,
        source_ids=[f"source-{unit_id}"],
        intent_summary=f"Intent for {unit_id}",
        outcome_summary=f"Outcome for {unit_id}",
        goal_doc_paths=[Path(f"/tmp/{project_id}/AGENTS.md")],
        correlation_ids={"sessions": [f"session-{unit_id}"]},
    )


def test_write_agent_packets_creates_all_roles(tmp_path: Path) -> None:
    from detrix.yc_trace_audit.packets import write_agent_packets

    units = [_sample_unit("u1", "detrix-core"), _sample_unit("u2", "agentxrd-v2")]
    packets = write_agent_packets(units=units, output_dir=tmp_path)

    assert {packet.role for packet in packets} == {
        "success_patterns",
        "friction_iteration",
        "failure_modes",
        "compounding_decisions",
        "external_research",
        "reviewer",
    }
    assert (tmp_path / "success_patterns.json").exists()
    assert "intent -> outcome -> distance to goal" in (tmp_path / "success_patterns.json").read_text()


def test_specialist_packets_include_failure_examples_and_resolution_paths(tmp_path: Path) -> None:
    from detrix.yc_trace_audit.packets import write_agent_packets

    units = [_sample_unit("u1", "detrix-core")]
    write_agent_packets(units=units, output_dir=tmp_path)

    packet = (tmp_path / "success_patterns.json").read_text(encoding="utf-8")

    assert "Trace Activity Is Not Progress" in packet
    assert "Resolution path:" in packet
    assert "Planning Artifacts Are Not Implementation" in packet
    assert "Support-Only Evidence Cannot Become Promotion Evidence" in packet


def test_yc_trace_audit_extract_command_writes_manifest(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "yc-trace-audit",
            "extract",
            "--mission-control-db",
            str(_write_sample_mission_control_db(tmp_path)),
            "--session-root",
            str(_write_sample_jsonl_sessions(tmp_path)),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "coverage_manifest.json").exists()
