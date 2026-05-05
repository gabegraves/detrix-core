"""Read-only source loaders for YC trace audit sessions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from detrix.yc_trace_audit.projects import AUDIT_WINDOW, project_for_path, project_for_text
from detrix.yc_trace_audit.schema import SourceKind, SourceRecord

MISSION_CONTROL_DB = Path("/home/gabriel/.mission-control/data.db")
DEFAULT_SESSION_ROOTS = [
    Path("/home/gabriel/.codex/sessions"),
    Path("/home/gabriel/.claude/projects"),
]


def load_all_sources(
    *,
    db_path: Path = MISSION_CONTROL_DB,
    session_roots: list[Path] | None = None,
) -> list[SourceRecord]:
    roots = DEFAULT_SESSION_ROOTS if session_roots is None else session_roots
    records = load_mission_control_sources(db_path=db_path) + load_jsonl_session_sources(roots)
    dedup: dict[str, SourceRecord] = {}
    for record in records:
        dedup[record.source_id] = record
    return sorted(dedup.values(), key=lambda record: (record.started_at or "", record.source_id))


def load_mission_control_sources(db_path: Path = MISSION_CONTROL_DB) -> list[SourceRecord]:
    if not db_path.exists():
        return []
    rows = _read_table_rows(db_path, "langfuse_traces") + _read_table_rows(db_path, "coding_sessions")
    records = [_row_to_source(row) for row in rows]
    return [
        record
        for record in records
        if record is not None and _in_window(record.started_at) and not record.cron_excluded
    ]


def load_jsonl_session_sources(session_roots: Iterable[Path]) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    for root in session_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.jsonl")):
            record = _jsonl_path_to_source(path)
            if record is not None and _in_window(record.started_at) and not record.cron_excluded:
                records.append(record)
    return records


def _read_table_rows(db_path: Path, table: str) -> list[dict[str, Any]]:
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as con:
            con.row_factory = sqlite3.Row
            exists = con.execute(
                "select name from sqlite_master where type='table' and name=?", (table,)
            ).fetchone()
            if not exists:
                return []
            return [dict(row) | {"__table": table} for row in con.execute(f"select * from {table}")]
    except sqlite3.Error:
        return []


def _row_to_source(row: dict[str, Any]) -> SourceRecord | None:
    table = str(row.get("__table", ""))
    metadata = _jsonish(row.get("metadata"))
    tags = _jsonish(row.get("tags"))
    metadata_dict = metadata if isinstance(metadata, dict) else {}
    cwd = _first_text(metadata_dict.get("cwd"), row.get("cwd"), row.get("working_directory"))
    project = _resolve_project(cwd=cwd, project=row.get("project"), title=_first_text(row.get("title"), row.get("name")))
    if project is None:
        return None
    title = _first_text(row.get("title"), row.get("name"), metadata_dict.get("title"))
    started = _first_text(row.get("started_at"), row.get("timestamp"), row.get("created_at"), row.get("startTime"))
    ended = _first_text(row.get("ended_at"), row.get("updated_at"), row.get("endTime"))
    kind: SourceKind = "langfuse_trace" if table == "langfuse_traces" else "coding_session"
    row_id = _first_text(row.get("id"), row.get("trace_id"), row.get("session_id")) or _stable_id(row)
    source_id = f"{kind}:{row_id}"
    return SourceRecord(
        source_id=source_id,
        source_kind=kind,
        project_id=project.project_id,
        started_at=started,
        ended_at=ended,
        title=title,
        langfuse_trace_id=row_id if kind == "langfuse_trace" else None,
        session_id=_first_text(row.get("session_id"), row_id if kind == "coding_session" else None),
        parent_session_id=_first_text(row.get("parent_session_id"), metadata_dict.get("parentSessionId")),
        cwd=Path(cwd) if cwd else None,
        metadata={"row": _json_safe(row), "metadata": metadata_dict, "tags": tags},
        cron_excluded=_is_cron_signal(title, metadata_dict, tags, row),
    )


def _jsonl_path_to_source(path: Path) -> SourceRecord | None:
    first: dict[str, Any] | None = None
    merged: dict[str, Any] = {}
    line_count = 0
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line_count >= 80:
                    break
                line_count += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                first = obj if first is None else first
                _merge_metadata(merged, obj)
                if merged.get("cwd") and merged.get("timestamp") and merged.get("session_id"):
                    break
    except OSError:
        return None
    if first is None:
        return None
    cwd = _first_text(merged.get("cwd"), merged.get("working_directory"))
    project = _resolve_project(cwd=cwd, project=merged.get("project"), title=merged.get("title"))
    if project is None:
        return None
    started = _first_text(merged.get("timestamp"), merged.get("created_at"), merged.get("started_at"))
    title = _first_text(merged.get("title"), merged.get("summary"), path.stem)
    session_id = _first_text(merged.get("session_id"), merged.get("id"), path.stem)
    kind: SourceKind = "claude_jsonl" if ".claude" in str(path) or "claude" in path.parts else "codex_jsonl"
    return SourceRecord(
        source_id=f"{kind}:{session_id}:{_hash_text(str(path))[:8]}",
        source_kind=kind,
        project_id=project.project_id,
        started_at=started,
        ended_at=_first_text(merged.get("ended_at"), merged.get("updated_at")),
        title=title,
        path=path,
        session_id=session_id,
        parent_session_id=_first_text(merged.get("parent_session_id"), merged.get("parentSessionId")),
        cwd=Path(cwd) if cwd else None,
        metadata={"path": str(path), "sample": _json_safe(first), "line_count_sampled": line_count},
        cron_excluded=_is_cron_signal(title, merged, [], {}),
    )


def _merge_metadata(target: dict[str, Any], obj: dict[str, Any]) -> None:
    payload = cast(dict[str, Any], obj.get("payload")) if isinstance(obj.get("payload"), dict) else {}
    message = cast(dict[str, Any], obj.get("message")) if isinstance(obj.get("message"), dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    candidates = {
        "cwd": obj.get("cwd") or payload.get("cwd") or obj.get("current_working_directory"),
        "timestamp": obj.get("timestamp") or payload.get("timestamp") or obj.get("created_at"),
        "session_id": obj.get("session_id") or obj.get("sessionId") or payload.get("id"),
        "parent_session_id": obj.get("parent_session_id") or obj.get("parentSessionId"),
        "title": obj.get("title") or obj.get("summary") or (content if isinstance(content, str) else None),
        "project": obj.get("project") or payload.get("project"),
    }
    for key, value in candidates.items():
        if value and not target.get(key):
            target[key] = value


def _resolve_project(cwd: str | None, project: object, title: str | None) -> Any | None:
    if cwd:
        try:
            return project_for_path(Path(cwd))
        except ValueError:
            pass
    text_project = project_for_text(_first_text(project))
    if text_project is not None:
        return text_project
    return project_for_text(title)


def _in_window(value: str | None) -> bool:
    if value is None:
        return False
    parsed = _parse_datetime(value)
    start = _parse_datetime(AUDIT_WINDOW.start_iso)
    end = _parse_datetime(AUDIT_WINDOW.end_iso)
    return parsed is not None and start is not None and end is not None and start <= parsed <= end


def _parse_datetime(value: str) -> datetime | None:
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _is_cron_signal(title: str | None, metadata: dict[str, Any], tags: object, row: dict[str, Any]) -> bool:
    haystack = " ".join(
        [
            title or "",
            json.dumps(metadata, default=str),
            json.dumps(tags, default=str),
            str(row.get("source", "")),
        ]
    ).lower()
    return "cron" in haystack or "scheduled" in haystack


def _jsonish(value: object) -> object:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _stable_id(row: dict[str, Any]) -> str:
    return _hash_text(json.dumps(_json_safe(row), sort_keys=True))[:16]


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_safe(value: object) -> object:
    try:
        json.dumps(value, default=str)
        return value
    except TypeError:
        return str(value)
