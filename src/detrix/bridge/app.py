"""Detrix governance bridge: dual-write AXV2 artifacts to audit and evidence stores."""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from detrix.adapters.axv2 import project_to_audit_log, run_artifact_to_trajectories
from detrix.runtime.audit import AuditLog
from detrix.runtime.trajectory_store import TrajectoryStore

app = FastAPI(title="detrix-bridge", version="0.1.0")

_store: TrajectoryStore | None = None
_audit: AuditLog | None = None


class IngestRequest(BaseModel):
    run_artifact: dict[str, Any]
    domain: str = "xrd"


class IngestResponse(BaseModel):
    trajectory_ids: list[str]
    count: int


@app.post("/ingest", response_model=IngestResponse)  # type: ignore[untyped-decorator]
async def ingest(request: IngestRequest) -> IngestResponse:
    run_id = str(request.run_artifact.get("run_id", ""))
    audit = _get_audit()

    if run_id and audit.get_run(run_id) is not None:
        raise HTTPException(status_code=409, detail=f"Duplicate run_id: {run_id}")

    trajectories = run_artifact_to_trajectories(
        request.run_artifact,
        domain=request.domain,
    )
    store = _get_store()

    try:
        project_to_audit_log(request.run_artifact, audit)
        for trajectory in trajectories:
            store.append(trajectory)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate run_id or trajectory_id: {run_id}",
        ) from exc

    return IngestResponse(
        trajectory_ids=[trajectory.trajectory_id for trajectory in trajectories],
        count=len(trajectories),
    )


@app.get("/health")  # type: ignore[untyped-decorator]
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


def _get_store() -> TrajectoryStore:
    global _store
    if _store is None:
        db_path = os.environ.get("DETRIX_EVIDENCE_DB", ".detrix/evidence.db")
        _store = TrajectoryStore(db_path)
    return _store


def _get_audit() -> AuditLog:
    global _audit
    if _audit is None:
        db_path = os.environ.get("DETRIX_AUDIT_DB", ".detrix/audit.db")
        _audit = AuditLog(db_path)
    return _audit
