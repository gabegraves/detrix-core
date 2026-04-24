"""Canonical schema for governance-scored execution traces."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

TRAJECTORY_SCHEMA_VERSION = 1


class GovernedTrajectory(BaseModel):
    """A single governed execution trace, ready for training export."""

    schema_version: int = TRAJECTORY_SCHEMA_VERSION

    trajectory_id: str
    run_id: str
    domain: str

    prompt: str
    completion: str

    verdicts: list[dict[str, Any]]
    governance_score: float
    gate_pass_rate: float

    rejection_type: str | None = None

    evaluator_versions: dict[str, str] = Field(default_factory=dict)
    gate_versions: dict[str, str] = Field(default_factory=dict)
    model_version: str | None = None

    started_at: datetime
    finished_at: datetime | None = None

    def to_sft_row(self) -> dict[str, str]:
        if self.rejection_type is not None:
            raise ValueError(
                f"Cannot use rejected trace for SFT (rejection_type={self.rejection_type})"
            )
        return {"prompt": self.prompt, "completion": self.completion}

    def to_grpo_row(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "governance_score": self.governance_score,
            "gate_verdicts": [v["decision"] for v in self.verdicts],
        }
