"""Append-only SQLite store for governed trajectories."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from detrix.core.trajectory import GovernedTrajectory
from detrix.runtime.version_tracker import (
    VERSION_CONTAMINATED_REJECTION,
    VersionFingerprint,
)

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
            self._ensure_column(conn, "governed_trajectories", "version_hash", "TEXT")
            self._ensure_column(conn, "governed_trajectories", "exported_at", "TEXT")
            self._ensure_column(conn, "governed_trajectories", "contaminated_at", "TEXT")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trace_epochs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_hash    TEXT NOT NULL UNIQUE,
                    fingerprint_json TEXT NOT NULL,
                    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
                    active          INTEGER NOT NULL DEFAULT 1
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

    @staticmethod
    def _ensure_column(
        conn: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def append(self, trajectory: GovernedTrajectory) -> None:
        fingerprint = VersionFingerprint.from_trajectory(trajectory)
        version_hash = fingerprint.hash
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_active_epoch(conn, fingerprint)
            conn.execute(
                """INSERT INTO governed_trajectories
                   (trajectory_id, run_id, domain, schema_version,
                    governance_score, gate_pass_rate, rejection_type,
                    model_version, started_at, finished_at, trajectory_json, version_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    version_hash,
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

    def _ensure_active_epoch(
        self, conn: sqlite3.Connection, fingerprint: VersionFingerprint
    ) -> None:
        active = conn.execute(
            "SELECT version_hash FROM trace_epochs WHERE active = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if active is not None and active[0] == fingerprint.hash:
            return
        self._flush_unexported_for_version_change(conn)
        if active is not None:
            conn.execute("UPDATE trace_epochs SET active = 0 WHERE active = 1")
        conn.execute(
            "INSERT OR IGNORE INTO trace_epochs (version_hash, fingerprint_json, active) "
            "VALUES (?, ?, 1)",
            (fingerprint.hash, fingerprint.to_json()),
        )
        conn.execute("UPDATE trace_epochs SET active = 1 WHERE version_hash = ?", (fingerprint.hash,))

    def _flush_unexported_for_version_change(self, conn: sqlite3.Connection) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            """SELECT trajectory_id, trajectory_json
               FROM governed_trajectories
               WHERE rejection_type IS NULL AND exported_at IS NULL"""
        ).fetchall()
        for trajectory_id, trajectory_json in rows:
            payload = json.loads(trajectory_json)
            payload["rejection_type"] = VERSION_CONTAMINATED_REJECTION
            conn.execute(
                """UPDATE governed_trajectories
                   SET rejection_type = ?, contaminated_at = ?, trajectory_json = ?
                   WHERE trajectory_id = ?""",
                (
                    VERSION_CONTAMINATED_REJECTION,
                    now,
                    json.dumps(payload, default=str),
                    trajectory_id,
                ),
            )

    def mark_exported(self, trajectory_ids: list[str]) -> None:
        """Mark trajectories as flushed/exported from the trace buffer."""
        if not trajectory_ids:
            return
        placeholders = ",".join("?" for _ in trajectory_ids)
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE governed_trajectories SET exported_at = ? "
                f"WHERE trajectory_id IN ({placeholders})",
                [now, *trajectory_ids],
            )

    def current_version_hash(self) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT version_hash FROM trace_epochs WHERE active = 1 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return str(row[0]) if row else None

    def query(
        self,
        domain: str | None = None,
        min_score: float | None = None,
        rejection_type: str | None = _UNSET,
        limit: int | None = 100,
    ) -> list[GovernedTrajectory]:
        conditions: list[str] = []
        params: list[Any] = []
        active_version_hash = self.current_version_hash()

        if domain is not None:
            conditions.append("domain = ?")
            params.append(domain)
        if min_score is not None:
            conditions.append("governance_score >= ?")
            params.append(min_score)
        if rejection_type != _UNSET:
            if rejection_type is None:
                conditions.append("rejection_type IS NULL")
                if active_version_hash is not None:
                    conditions.append("version_hash = ?")
                    params.append(active_version_hash)
            else:
                conditions.append("rejection_type = ?")
                params.append(rejection_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = "SELECT trajectory_json FROM governed_trajectories " f"{where} ORDER BY id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [GovernedTrajectory.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM governed_trajectories").fetchone()
            return int(row[0]) if row else 0
