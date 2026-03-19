"""RunArtifact — immutable bundle capturing everything about a pipeline run."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from detrix.core.cache import _stable_hash
from detrix.core.models import RunRecord, StepResult


class RunArtifact(BaseModel):
    """Immutable, versioned bundle of a complete pipeline run."""

    run_id: str
    workflow_name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    inputs_hash: str
    outputs_hash: str
    code_revision: Optional[str] = None
    env_spec: Dict[str, str] = Field(default_factory=dict)
    step_results: List[StepResult] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def save(self, path: str | Path) -> Path:
        """Write artifact as JSON bundle."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2))
        return p

    @classmethod
    def load(cls, path: str | Path) -> "RunArtifact":
        """Read artifact from JSON bundle."""
        p = Path(path)
        return cls.model_validate_json(p.read_text())

    @classmethod
    def from_run_record(
        cls,
        record: RunRecord,
        git_sha: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "RunArtifact":
        """Capture a RunArtifact from a completed RunRecord."""
        import platform
        import sys

        inputs_hash = _stable_hash(record.inputs)

        all_outputs = {}
        for sr in record.step_results:
            all_outputs[sr.step_id] = sr.output_data
        outputs_hash = _stable_hash(all_outputs)

        code_rev = git_sha
        if code_rev is None:
            try:
                code_rev = (
                    subprocess.check_output(
                        ["git", "rev-parse", "HEAD"],
                        stderr=subprocess.DEVNULL,
                    )
                    .decode()
                    .strip()
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                code_rev = None

        env_spec = {
            "python_version": sys.version,
            "platform": platform.platform(),
        }

        return cls(
            run_id=record.run_id,
            workflow_name=record.workflow_name,
            started_at=record.started_at,
            ended_at=record.finished_at,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            code_revision=code_rev,
            env_spec=env_spec,
            step_results=record.step_results,
            metadata=metadata or {},
        )
