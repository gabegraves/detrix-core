"""TraceCollector — extract training examples from completed runs.

Stub interface. Full implementation will convert RunArtifact step
traces into SFT-ready training examples for model improvement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from detrix.runtime.artifact import RunArtifact


class TrainingExample(BaseModel):
    """A single training example extracted from a run trace."""

    prompt: str
    completion: str
    metadata: dict[str, Any] = {}


class TraceCollector(ABC):
    """Abstract base for collecting training data from run artifacts."""

    @abstractmethod
    def collect(self, run_artifact: RunArtifact) -> list[TrainingExample]:
        """Extract training examples from a completed run."""
        ...
