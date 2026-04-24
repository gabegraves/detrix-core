"""Append-only SQLite store for governed trajectories."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from detrix.core.trajectory import GovernedTrajectory

_UNSET = "__unset__"


class TrajectoryStore:
    """Append-only evidence store backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governed_trajectories (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    trajectory_id    TEXT NOT NULL UNIQUE,
                    run_id           TEXT NOT NULL,
                    domain           TEXT NOT NULL,
                    schema_version   INTEGER NOT NULL,
                    governance_score REAL NOT NULL,
                    gate_pass_rate   REAL NOT NULL,
                    rejection_type   TEXT,
                    model_version    TEXT,
                    started_at       TEXT NOT NULL,
                    finished_at      TEXT,
                    trajectory_json  TEXT NOT NULL,
                    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_traj_run_id ON governed_trajectories(run_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_traj_domain ON governed_trajectories(domain)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_traj_rejection "
                "ON governed_trajectories(rejection_type)"
            )

    def append(self, trajectory: GovernedTrajectory) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO governed_trajectories
                   (trajectory_id, run_id, domain, schema_version,
                    governance_score, gate_pass_rate, rejection_type,
                    model_version, started_at, finished_at, trajectory_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trajectory.trajectory_id,
                    trajectory.run_id,
                    trajectory.domain,
                    trajectory.schema_version,
                    trajectory.governance_score,
                    trajectory.gate_pass_rate,
                    trajectory.rejection_type,
                    trajectory.model_version,
                    trajectory.started_at.isoformat(),
                    trajectory.finished_at.isoformat() if trajectory.finished_at else None,
                    trajectory.model_dump_json(),
                ),
            )

    def get(self, trajectory_id: str) -> GovernedTrajectory | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT trajectory_json FROM governed_trajectories WHERE trajectory_id = ?",
                (trajectory_id,),
            ).fetchone()
            if row is None:
                return None
            return GovernedTrajectory.model_validate_json(row[0])

    def list_by_run(self, run_id: str) -> list[GovernedTrajectory]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT trajectory_json FROM governed_trajectories WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
            return [GovernedTrajectory.model_validate_json(row[0]) for row in rows]

    def query(
        self,
        domain: str | None = None,
        min_score: float | None = None,
        rejection_type: str | None = _UNSET,
        limit: int = 100,
    ) -> list[GovernedTrajectory]:
        conditions: list[str] = []
        params: list[Any] = []

        if domain is not None:
            conditions.append("domain = ?")
            params.append(domain)
        if min_score is not None:
            conditions.append("governance_score >= ?")
            params.append(min_score)
        if rejection_type != _UNSET:
            if rejection_type is None:
                conditions.append("rejection_type IS NULL")
            else:
                conditions.append("rejection_type = ?")
                params.append(rejection_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT trajectory_json FROM governed_trajectories "
                f"{where} ORDER BY id LIMIT ?",
                params,
            ).fetchall()
            return [GovernedTrajectory.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM governed_trajectories").fetchone()
            return int(row[0]) if row else 0
