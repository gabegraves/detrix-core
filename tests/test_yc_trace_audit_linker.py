from __future__ import annotations

import subprocess
from pathlib import Path

from detrix.yc_trace_audit.schema import SourceRecord


def test_build_audit_units_groups_parent_and_child_sessions() -> None:
    from detrix.yc_trace_audit.linker import build_audit_units

    records = [
        SourceRecord(
            source_id="parent",
            source_kind="claude_jsonl",
            project_id="detrix-core",
            session_id="parent-session",
            title="plan yc trace audit",
            started_at="2026-05-04T10:00:00-04:00",
            ended_at="2026-05-04T10:20:00-04:00",
        ),
        SourceRecord(
            source_id="child",
            source_kind="codex_jsonl",
            project_id="detrix-core",
            session_id="child-session",
            parent_session_id="parent-session",
            title="execute yc trace audit",
            started_at="2026-05-04T10:21:00-04:00",
            ended_at="2026-05-04T11:00:00-04:00",
        ),
    ]

    units = build_audit_units(records)

    assert len(units) == 1
    assert units[0].source_ids == ["parent", "child"]
    assert "plan yc trace audit" in units[0].intent_summary
    assert "execute yc trace audit" in units[0].outcome_summary


def test_build_audit_units_keeps_different_projects_separate() -> None:
    from detrix.yc_trace_audit.linker import build_audit_units

    records = [
        SourceRecord(
            source_id="a",
            source_kind="codex_jsonl",
            project_id="agentxrd-v2",
            title="row blocker",
            started_at="2026-04-01T00:00:00-04:00",
        ),
        SourceRecord(
            source_id="b",
            source_kind="codex_jsonl",
            project_id="parabolahunter",
            title="sniper replay",
            started_at="2026-04-01T00:05:00-04:00",
        ),
    ]

    units = build_audit_units(records)

    assert {unit.project_id for unit in units} == {"agentxrd-v2", "parabolahunter"}


def _init_temp_repo_with_commit(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "--date", "2026-04-01T12:00:00-04:00", "-m", "Initial test commit"],
        cwd=repo,
        check=True,
        env={"GIT_COMMITTER_DATE": "2026-04-01T12:00:00-04:00"},
    )
    return repo


def test_collect_git_commits_returns_hash_subject_and_date(tmp_path: Path) -> None:
    from detrix.yc_trace_audit.correlator import collect_git_commits

    repo = _init_temp_repo_with_commit(tmp_path)
    commits = collect_git_commits(repo, since="2026-02-01", until="2026-05-05")

    assert commits[0]["hash"]
    assert commits[0]["subject"] == "Initial test commit"


def test_collect_plan_docs_and_beads_fail_closed(tmp_path: Path) -> None:
    from detrix.yc_trace_audit.correlator import collect_beads, collect_plan_docs

    repo = tmp_path / "repo"
    (repo / ".omx" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "specs").mkdir(parents=True)
    (repo / ".omx" / "plans" / "prd-test.md").write_text("# Plan\n", encoding="utf-8")
    (repo / "docs" / "demo-plan.md").parent.mkdir(exist_ok=True)
    (repo / "docs" / "demo-plan.md").write_text("# Demo Plan\n", encoding="utf-8")

    docs = collect_plan_docs(repo)

    assert {doc["path"] for doc in docs} >= {".omx/plans/prd-test.md", "docs/demo-plan.md"}
    assert collect_beads(repo) == []
