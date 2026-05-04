from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class MissionControlLangfuseSource(BaseModel):
    db_path: Path = Path("/home/gabriel/.mission-control/data.db")
    base_url: str = "http://localhost:3100"
    live_enabled: bool = False


class LangfuseImportReport(BaseModel):
    raw_trace_count: int
    normalized_observation_count: int
    project: str
    project_aliases: list[str]
    joinable_trace_count: int
    unjoinable_trace_count: int
    missing_join_key_reasons: dict[str, int]
    live_enabled: bool
    advisory_only: bool = True


def import_agentxrd_langfuse_traces(
    *,
    source: MissionControlLangfuseSource,
    project: str,
    output_dir: Path,
    limit: int = 1000,
) -> LangfuseImportReport:
    traces = _read_cached_traces(source.db_path, _project_aliases(project), limit)
    observations = [_normalize_trace(row) for row in traces]
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "raw_langfuse_traces.jsonl", traces)
    _write_jsonl(output_dir / "normalized_observations.jsonl", observations)
    return LangfuseImportReport(
        raw_trace_count=len(traces),
        normalized_observation_count=len(observations),
        project=project,
        project_aliases=_project_aliases(project),
        joinable_trace_count=sum(1 for obs in observations if obs.get("sample_id")),
        unjoinable_trace_count=sum(
            1
            for obs in observations
            if str(obs.get("join_status", "")).startswith("unjoinable")
        ),
        missing_join_key_reasons=_missing_join_key_reasons(observations),
        live_enabled=source.live_enabled,
    )


def _project_aliases(project: str) -> list[str]:
    aliases = [project]
    if project == "mc-agentxrd_v2":
        aliases.append("AgentXRD_v2")
    if project == "AgentXRD_v2":
        aliases.append("mc-agentxrd_v2")
    return aliases


def _read_cached_traces(
    db_path: Path, projects: list[str], limit: int
) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in projects)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT id, instance_id, name, project, model, input_tokens, output_tokens,
                      total_cost, latency_ms, status, started_at, metadata, ingested_at
               FROM langfuse_traces
               WHERE project IN ({placeholders})
               ORDER BY datetime(COALESCE(started_at, ingested_at)) DESC
               LIMIT ?""",
            (*projects, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def _normalize_trace(row: dict[str, Any]) -> dict[str, Any]:
    metadata = {}
    if row.get("metadata"):
        try:
            metadata = json.loads(str(row["metadata"]))
        except json.JSONDecodeError:
            metadata = {"raw_metadata": row["metadata"]}
    sample_id = metadata.get("sample_id") or metadata.get("agentxrd_sample_id")
    failure_hint = (
        metadata.get("error")
        or metadata.get("failure_mode")
        or row.get("status")
        or row.get("name")
        or "cache_summary_trace"
    )
    return {
        "schema_version": "agentxrd_langfuse_observation_v0.1",
        "trace_id": row["id"],
        "project": row.get("project"),
        "name": row.get("name"),
        "model": row.get("model"),
        "status": row.get("status"),
        "latency_ms": row.get("latency_ms"),
        "input_tokens": row.get("input_tokens") or 0,
        "output_tokens": row.get("output_tokens") or 0,
        "sample_id": sample_id,
        "join_status": "joined" if sample_id else "unjoinable_cache_summary",
        "missing_join_key_reason": None
        if sample_id
        else "metadata_missing_sample_id_or_agentxrd_sample_id",
        "failure_hint": failure_hint,
        "metadata": metadata,
        "advisory_only": True,
    }


def _missing_join_key_reasons(observations: list[dict[str, Any]]) -> dict[str, int]:
    reasons: dict[str, int] = {}
    for observation in observations:
        if observation.get("sample_id"):
            continue
        reason = str(
            observation.get("missing_join_key_reason")
            or "metadata_missing_sample_id_or_agentxrd_sample_id"
        )
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
