"""Append-only SQLite audit log for workflow execution.

Records every step execution with timing, hashes, and status.
Designed for governance: who ran what, when, with what inputs/outputs.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from detrix.core.models import RunRecord, StepResult


class AuditLog:
    """Append-only audit log backed by SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id            TEXT PRIMARY KEY,
                    workflow_name     TEXT NOT NULL,
                    workflow_version  TEXT NOT NULL,
                    started_at        TEXT NOT NULL,
                    finished_at       TEXT,
                    status            TEXT NOT NULL,
                    inputs_json       TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS step_executions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id        TEXT NOT NULL REFERENCES workflow_runs(run_id),
                    step_id       TEXT NOT NULL,
                    status        TEXT NOT NULL,
                    started_at    TEXT NOT NULL,
                    finished_at   TEXT NOT NULL,
                    duration_ms   REAL NOT NULL,
                    input_hash    TEXT,
                    output_hash   TEXT,
                    error         TEXT,
                    attempt       INTEGER DEFAULT 1,
                    cached        INTEGER DEFAULT 0,
                    gate_decision TEXT,
                    gate_id       TEXT,
                    gate_verdict_json TEXT
                )
            """)

    def record_run_start(self, record: RunRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO workflow_runs
                   (run_id, workflow_name, workflow_version, started_at, status, inputs_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    record.run_id,
                    record.workflow_name,
                    record.workflow_version,
                    record.started_at.isoformat(),
                    record.status.value,
                    json.dumps(record.inputs, default=str),
                ),
            )

    def record_run_end(self, record: RunRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE workflow_runs
                   SET finished_at = ?, status = ?
                   WHERE run_id = ?""",
                (
                    record.finished_at.isoformat() if record.finished_at else None,
                    record.status.value,
                    record.run_id,
                ),
            )

    def record_step(self, run_id: str, result: StepResult) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO step_executions
                   (run_id, step_id, status, started_at, finished_at,
                    duration_ms, input_hash, output_hash, error, attempt, cached,
                    gate_decision, gate_id, gate_verdict_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    result.step_id,
                    result.status.value,
                    result.started_at.isoformat(),
                    result.finished_at.isoformat(),
                    result.duration_ms,
                    result.input_hash,
                    result.output_hash,
                    result.error,
                    result.attempt,
                    1 if result.cached else 0,
                    result.gate_verdict["decision"] if result.gate_verdict else None,
                    result.gate_verdict["gate_id"] if result.gate_verdict else None,
                    (
                        json.dumps(result.gate_verdict, default=str)
                        if result.gate_verdict is not None
                        else None
                    ),
                ),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not row:
                return None
            run = dict(row)
            steps = conn.execute(
                "SELECT * FROM step_executions WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
            run["steps"] = [dict(s) for s in steps]
            return run

    def list_runs(
        self,
        workflow_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if workflow_name:
                rows = conn.execute(
                    """SELECT * FROM workflow_runs
                       WHERE workflow_name = ?
                       ORDER BY started_at DESC LIMIT ?""",
                    (workflow_name, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workflow_runs ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
