"""Scoring and grading types for the detrix runtime."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApproachGrade(str, Enum):
    """Symbol-based scoring grade for a session prompt."""

    MAJOR_POSITIVE = "!!"
    POSITIVE = "!"
    NEUTRAL = "="
    NEGATIVE = "?"
    MAJOR_NEGATIVE = "??"


class ConfidenceLevel(str, Enum):
    """Confidence level for a Haiku judgment."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HaikuPromptGrade(BaseModel):
    """Grade assigned to a single prompt by Haiku."""

    prompt_index: int
    grade: ApproachGrade
    reasoning: str
    file_references: List[str] = Field(default_factory=list)


class HaikuOverride(BaseModel):
    """Manual override to a Haiku-assigned grade."""

    prompt_index: int
    grade: ApproachGrade
    reason: str


class HaikuScorecard(BaseModel):
    """Complete scoring breakdown for a session from Haiku."""

    score: int  # 0-100
    prompt_grades: List[HaikuPromptGrade] = Field(default_factory=list)
    went_right: List[str] = Field(default_factory=list)
    went_wrong: List[str] = Field(default_factory=list)
    overrides: List[HaikuOverride] = Field(default_factory=list)
    digest_tokens: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    notes: Optional[str] = None


class SessionGradeRecord(BaseModel):
    """Complete grading record for a session."""

    session_id: str
    mechanical_grades: Dict[int, ApproachGrade] = Field(default_factory=dict)
    haiku_scorecard: Optional[HaikuScorecard] = None
    final_score: Optional[int] = None
    created_at: str = Field(default_factory=lambda: "")
    notes: Optional[str] = None


class PromptChange(BaseModel):
    """File changes for a single prompt."""

    prompt_index: int
    files_added: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    errors: int = 0
    test_failures: int = 0
    test_passes: int = 0


class SessionDigest(BaseModel):
    """Compressed representation of session activity for Haiku review."""

    session_id: str
    prompt_count: int
    prompt_changes: List[PromptChange] = Field(default_factory=list)
    mechanical_grades: Dict[int, ApproachGrade] = Field(default_factory=dict)
    reverted_prompts: List[int] = Field(default_factory=list)
    consecutive_failures: Dict[int, int] = Field(default_factory=dict)
    estimated_tokens: int = 0
