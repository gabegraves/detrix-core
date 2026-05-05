"""Deterministic intent/outcome unit linking for YC trace audit sources."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from detrix.yc_trace_audit.projects import CORE_PROJECTS
from detrix.yc_trace_audit.schema import AuditUnit, SourceRecord


def build_audit_units(records: list[SourceRecord]) -> list[AuditUnit]:
    if not records:
        return []
    by_source = {record.source_id: record for record in records}
    parent = {record.source_id: record.source_id for record in records}

    def find(source_id: str) -> str:
        while parent[source_id] != source_id:
            parent[source_id] = parent[parent[source_id]]
            source_id = parent[source_id]
        return source_id

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    session_index: dict[str, str] = {}
    trace_index: dict[str, str] = {}
    for record in records:
        if record.session_id:
            if record.session_id in session_index:
                union(record.source_id, session_index[record.session_id])
            session_index[record.session_id] = record.source_id
        if record.langfuse_trace_id:
            if record.langfuse_trace_id in trace_index:
                union(record.source_id, trace_index[record.langfuse_trace_id])
            trace_index[record.langfuse_trace_id] = record.source_id

    for record in records:
        if record.parent_session_id and record.parent_session_id in session_index:
            union(record.source_id, session_index[record.parent_session_id])

    groups: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in records:
        groups[find(record.source_id)].append(record)

    units = [_build_unit(sorted(group, key=_record_sort_key), by_source) for group in groups.values()]
    return sorted(units, key=lambda unit: (unit.project_id, unit.unit_id))


def _build_unit(group: list[SourceRecord], by_source: dict[str, SourceRecord]) -> AuditUnit:
    source_ids = [record.source_id for record in sorted(group, key=_record_sort_key)]
    project_id = _primary_project(group)
    unit_id = "ycunit-" + hashlib.sha256("\n".join(source_ids).encode("utf-8")).hexdigest()[:12]
    earliest = min(group, key=_record_sort_key)
    latest = max(group, key=_record_sort_key)
    evidence_paths = sorted({record.path for record in group if record.path is not None})
    correlations: dict[str, list[str]] = {
        "sessions": sorted({record.session_id for record in group if record.session_id}),
        "traces": sorted({record.langfuse_trace_id for record in group if record.langfuse_trace_id}),
    }
    correlations = {key: value for key, value in correlations.items() if value}
    return AuditUnit(
        unit_id=unit_id,
        project_id=project_id,
        source_ids=source_ids,
        intent_summary=_summary_for(earliest, prefix="Intent"),
        outcome_summary=_summary_for(latest, prefix="Outcome"),
        goal_doc_paths=CORE_PROJECTS[project_id].goal_docs,
        evidence_paths=evidence_paths,
        correlation_ids=correlations,
    )


def _primary_project(group: list[SourceRecord]) -> str:
    child_records = [record for record in group if record.parent_session_id]
    if child_records:
        return sorted(child_records, key=_record_sort_key)[-1].project_id
    return sorted(group, key=_record_sort_key)[-1].project_id


def _summary_for(record: SourceRecord, *, prefix: str) -> str:
    title = record.title or record.session_id or record.langfuse_trace_id or record.source_id
    status = record.metadata.get("status") if isinstance(record.metadata, dict) else None
    suffix = f" status={status}" if status else ""
    return f"{prefix}: {title}{suffix}"


def _record_sort_key(record: SourceRecord) -> tuple[str, str]:
    return (record.started_at or "", record.source_id)


def normalized_title(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
