"""Schemas for the YC trace audit runbook harness."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SourceKind = Literal["langfuse_trace", "coding_session", "codex_jsonl", "claude_jsonl"]
AgentRole = Literal[
    "success_patterns",
    "friction_iteration",
    "failure_modes",
    "compounding_decisions",
    "external_research",
    "reviewer",
]
DistanceToGoal = Literal["closed", "partial", "wide", "zero", "unknown"]
Confidence = Literal["high", "medium", "low"]


class AuditWindow(BaseModel):
    start_iso: str
    end_iso: str


class ProjectDefinition(BaseModel):
    project_id: str
    display_name: str
    root: Path
    aliases: list[str]
    goal_docs: list[Path]


class SourceRecord(BaseModel):
    source_id: str
    source_kind: SourceKind
    project_id: str
    started_at: str | None = None
    ended_at: str | None = None
    title: str | None = None
    path: Path | None = None
    langfuse_trace_id: str | None = None
    session_id: str | None = None
    parent_session_id: str | None = None
    cwd: Path | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    cron_excluded: bool = False


class AuditUnit(BaseModel):
    unit_id: str
    project_id: str
    source_ids: list[str]
    intent_summary: str
    outcome_summary: str
    goal_doc_paths: list[Path]
    evidence_paths: list[Path] = Field(default_factory=list)
    correlation_ids: dict[str, list[str]] = Field(default_factory=dict)


class AgentPacket(BaseModel):
    role: AgentRole
    audit_window: AuditWindow
    project_ids: list[str]
    unit_ids: list[str]
    prompt: str
    manifest_path: Path


class AgentFinding(BaseModel):
    finding_id: str
    role: AgentRole
    unit_ids: list[str]
    project_id: str | None = None
    claim: str
    evidence: list[str]
    distance_to_goal: DistanceToGoal
    confidence: Confidence
    mental_model: str | None = None


class ReviewReport(BaseModel):
    passed: bool
    total_units: int
    covered_units: int
    uncovered_unit_ids: list[str]
    rejected_finding_ids: list[str]
    accepted_finding_ids: list[str]
