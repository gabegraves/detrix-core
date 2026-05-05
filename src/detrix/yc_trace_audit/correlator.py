"""Read-only correlation helpers for YC trace audit units."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from detrix.yc_trace_audit.projects import AUDIT_WINDOW, CORE_PROJECTS
from detrix.yc_trace_audit.schema import AuditUnit


def collect_git_commits(repo: Path, since: str, until: str) -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "log",
            f"--since={since}",
            f"--until={until}",
            "--date=iso-strict",
            "--format=%H%x1f%ad%x1f%s",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return []
    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        commits.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return commits


def collect_plan_docs(repo: Path) -> list[dict[str, str]]:
    patterns = [
        ".omc/plans/*.md",
        ".omx/plans/*.md",
        "docs/**/*plan*.md",
        "docs/superpowers/specs/*.md",
    ]
    docs: dict[str, dict[str, str]] = {}
    for pattern in patterns:
        for path in repo.glob(pattern):
            if path.is_file():
                rel = path.relative_to(repo).as_posix()
                docs[rel] = {"path": rel, "title": _first_heading(path) or path.stem}
    return [docs[key] for key in sorted(docs)]


def collect_beads(repo: Path) -> list[dict[str, object]]:
    result = subprocess.run(
        ["bd", "list", "--json"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def attach_correlations(units: list[AuditUnit]) -> list[AuditUnit]:
    commits_by_project = {
        project_id: collect_git_commits(
            project.root,
            since=AUDIT_WINDOW.start_iso[:10],
            until=AUDIT_WINDOW.end_iso[:10],
        )
        for project_id, project in CORE_PROJECTS.items()
    }
    plans_by_project = {project_id: collect_plan_docs(project.root) for project_id, project in CORE_PROJECTS.items()}
    beads_by_project = {project_id: collect_beads(project.root) for project_id, project in CORE_PROJECTS.items()}
    updated: list[AuditUnit] = []
    for unit in units:
        keywords = _keywords(unit.intent_summary + " " + unit.outcome_summary)
        correlation_ids = dict(unit.correlation_ids)
        git_ids = [commit["hash"][:12] for commit in commits_by_project[unit.project_id] if _overlaps(commit["subject"], keywords)][:5]
        plan_ids = [doc["path"] for doc in plans_by_project[unit.project_id] if _overlaps(doc["title"] + " " + doc["path"], keywords)][:5]
        bead_ids = [str(bead.get("id")) for bead in beads_by_project[unit.project_id] if _overlaps(str(bead.get("title", "")), keywords)][:5]
        weak_git_ids = [commit["hash"][:12] for commit in commits_by_project[unit.project_id]][:3]
        if git_ids:
            correlation_ids["git"] = git_ids
        elif weak_git_ids:
            correlation_ids["weak_git"] = weak_git_ids
        if plan_ids:
            correlation_ids["plans"] = plan_ids
        if bead_ids:
            correlation_ids["beads"] = bead_ids
        updated.append(unit.model_copy(update={"correlation_ids": correlation_ids}))
    return updated


def _first_heading(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8") as handle:
            for _ in range(40):
                line = handle.readline()
                if not line:
                    return None
                stripped = line.strip()
                if stripped.startswith("#"):
                    return stripped.lstrip("# ").strip()
    except OSError:
        return None
    return None


def _keywords(text: str) -> set[str]:
    return {token for token in text.lower().replace("-", " ").split() if len(token) >= 4}


def _overlaps(text: str, keywords: set[str]) -> bool:
    if not keywords:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)
