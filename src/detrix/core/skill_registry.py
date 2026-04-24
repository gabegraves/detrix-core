"""Canonical schemas for deterministic skills and routing."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class DeterministicTool(BaseModel):
    """A deterministic script that a skill can route agent work toward."""

    tool_id: str
    script_path: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    domain: str
    version: str


class SkillDefinition(BaseModel):
    """A reusable skill generated from governance-scored failure evidence."""

    skill_id: str
    name: str
    description: str
    triggers: list[str]
    deterministic_tool_ids: list[str]
    test_intents: list[str]
    domain: str
    version: str
    created_from_trajectory_id: str | None = None
    created_at: datetime
    status: Literal["candidate", "validated", "active", "retired"] = "candidate"


class SkillRouting(BaseModel):
    """Intent pattern mapped to the skill that should handle it."""

    intent_pattern: str
    skill_id: str
    confidence_threshold: float = 0.8
