"""Shared enums and verdict types for the detrix runtime."""

from __future__ import annotations

from enum import Enum
from typing import Any


class Verdict(str, Enum):
    """Outcome of a model promotion comparison."""

    PROMOTE = "promote"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"


class StepExecutionError(Exception):
    """Raised when a user-supplied step function fails.

    Wraps the original exception so callers can distinguish "step function
    raised" from governance/framework errors (e.g. GovernanceError) which
    will propagate unwrapped through the pipeline loop.
    """

    def __init__(self, step_id: str, cause: BaseException) -> None:
        super().__init__(f"Step '{step_id}' failed: {cause}")
        self.step_id = step_id
        self.cause = cause


class GovernanceError(Exception):
    """Raised when a governance gate rejects or halts the pipeline.

    Propagates unwrapped through the pipeline loop, bypassing step retry logic.
    """

    def __init__(self, verdict: Any) -> None:
        self.verdict = verdict
        gate_id = getattr(verdict, "gate_id", "unknown")
        decision = getattr(verdict, "decision", "unknown")
        if hasattr(decision, "value"):
            decision = decision.value
        super().__init__(f"Gate '{gate_id}' returned {decision}")
