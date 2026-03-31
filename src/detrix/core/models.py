"""Data models for the workflow engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CACHED = "cached"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RetryConfig(BaseModel):
    max_attempts: int = 1
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0


class StepDef(BaseModel):
    """A single step in a workflow definition."""

    id: str
    name: str
    function: str  # dotted path: "mypackage.steps.process"
    inputs: Dict[str, str] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    timeout_seconds: Optional[float] = None
    approval_required: bool = False


class WorkflowDef(BaseModel):
    """A complete workflow definition parsed from YAML."""

    name: str
    version: str = "1.0"
    description: str = ""
    steps: List[StepDef]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Outcome of executing a single step."""

    step_id: str
    status: StepStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    input_hash: str = ""
    output_hash: str = ""
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    attempt: int = 1
    cached: bool = False
    gate_verdict: Optional[Dict[str, Any]] = None


class RunRecord(BaseModel):
    """Complete record of a workflow run."""

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_name: str
    workflow_version: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    status: StepStatus = StepStatus.PENDING
    step_results: List[StepResult] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return 0.0

    @property
    def failed_steps(self) -> List[StepResult]:
        return [s for s in self.step_results if s.status == StepStatus.FAILED]
