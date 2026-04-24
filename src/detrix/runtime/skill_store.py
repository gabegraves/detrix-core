"""SQLite-backed registry for deterministic tools, skills, and routes."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from detrix.core.skill_registry import (
    DeterministicTool,
    SkillDefinition,
    SkillRouting,
)


class SkillStore:
    """Evidence-backed skill registry.

    Tools and skills are append-only unique records. Routing entries are keyed by
    intent pattern and upserted so validators can repair route targets in place.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deterministic_tools (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id     TEXT NOT NULL UNIQUE,
                    domain      TEXT NOT NULL,
                    version     TEXT NOT NULL,
                    tool_json   TEXT NOT NULL,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id    TEXT NOT NULL UNIQUE,
                    domain      TEXT NOT NULL,
                    status      TEXT NOT NULL,
                    version     TEXT NOT NULL,
                    skill_json  TEXT NOT NULL,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_routings (
                    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_pattern        TEXT NOT NULL UNIQUE,
                    normalized_pattern    TEXT NOT NULL,
                    skill_id              TEXT NOT NULL,
                    confidence_threshold  REAL NOT NULL,
                    routing_json          TEXT NOT NULL,
                    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tools_domain ON deterministic_tools(domain)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_domain ON skills(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_skill_id ON skills(skill_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_routings_skill_id ON skill_routings(skill_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_routings_pattern "
                "ON skill_routings(normalized_pattern)"
            )

    def register_tool(self, tool: DeterministicTool) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO deterministic_tools
                   (tool_id, domain, version, tool_json)
                   VALUES (?, ?, ?, ?)""",
                (tool.tool_id, tool.domain, tool.version, tool.model_dump_json()),
            )

    def register_skill(self, skill: SkillDefinition) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO skills
                   (skill_id, domain, status, version, skill_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    skill.skill_id,
                    skill.domain,
                    skill.status,
                    skill.version,
                    skill.model_dump_json(),
                ),
            )

    def add_routing(self, routing: SkillRouting) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO skill_routings
                   (intent_pattern, normalized_pattern, skill_id,
                    confidence_threshold, routing_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(intent_pattern) DO UPDATE SET
                       normalized_pattern = excluded.normalized_pattern,
                       skill_id = excluded.skill_id,
                       confidence_threshold = excluded.confidence_threshold,
                       routing_json = excluded.routing_json,
                       updated_at = datetime('now')""",
                (
                    routing.intent_pattern,
                    _normalize_intent(routing.intent_pattern),
                    routing.skill_id,
                    routing.confidence_threshold,
                    routing.model_dump_json(),
                ),
            )

    def get_skill(self, skill_id: str) -> SkillDefinition | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT skill_json FROM skills WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
            if row is None:
                return None
            return SkillDefinition.model_validate_json(row[0])

    def list_skills(
        self,
        domain: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[SkillDefinition]:
        conditions: list[str] = []
        params: list[Any] = []

        if domain is not None:
            conditions.append("domain = ?")
            params.append(domain)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT skill_json FROM skills {where} ORDER BY id LIMIT ?",
                params,
            ).fetchall()
            return [SkillDefinition.model_validate_json(row[0]) for row in rows]

    def get_tools_for_domain(self, domain: str) -> list[DeterministicTool]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT tool_json FROM deterministic_tools WHERE domain = ? ORDER BY id",
                (domain,),
            ).fetchall()
            return [DeterministicTool.model_validate_json(row[0]) for row in rows]

    def find_routing(self, intent: str) -> SkillRouting | None:
        normalized_intent = _normalize_intent(intent)
        if normalized_intent == "":
            return None

        with sqlite3.connect(self.db_path) as conn:
            exact = conn.execute(
                """SELECT routing_json FROM skill_routings
                   WHERE normalized_pattern = ?
                   ORDER BY id
                   LIMIT 1""",
                (normalized_intent,),
            ).fetchone()
            if exact is not None:
                return SkillRouting.model_validate_json(exact[0])

            rows = conn.execute(
                "SELECT normalized_pattern, routing_json FROM skill_routings ORDER BY id"
            ).fetchall()

        for pattern, routing_json in rows:
            if pattern and (pattern in normalized_intent or normalized_intent in pattern):
                return SkillRouting.model_validate_json(routing_json)
        return None


def _normalize_intent(intent: str) -> str:
    return " ".join(intent.casefold().split())
