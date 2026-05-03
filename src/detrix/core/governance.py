"""Deterministic governance primitives for the detrix runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Decision(str, Enum):
    """Gate decision for a pipeline output."""

    ACCEPT = "accept"
    REJECT = "reject"
    CAUTION = "caution"
    REQUEST_MORE_DATA = "request_more_data"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VerdictContract:
    """Structured output of a governance gate."""

    decision: Decision
    gate_id: str
    evidence: dict[str, Any]
    reason_codes: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    confidence: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    input_hash: str = ""
    evaluator_version: str = ""
    human_override: bool = False
    override_reason: str = ""
    rejection_type: str | None = None
    is_labeled: bool = False
    expert_decision: Decision | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "gate_id": self.gate_id,
            "evidence": self.evidence,
            "reason_codes": self.reason_codes,
            "recommended_actions": self.recommended_actions,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "input_hash": self.input_hash,
            "evaluator_version": self.evaluator_version,
            "human_override": self.human_override,
            "override_reason": self.override_reason,
            "rejection_type": self.rejection_type,
            "is_labeled": self.is_labeled,
            "expert_decision": (
                self.expert_decision.value if self.expert_decision is not None else None
            ),
        }


@dataclass
class GateContext:
    """Pipeline context passed to governance gates."""

    run_id: str
    step_index: int
    prior_verdicts: list[VerdictContract]
    config: dict[str, Any]
    goal_mode: str = ""


class GovernanceGate(ABC):
    """Deterministic checkpoint for a pipeline output."""

    @property
    @abstractmethod
    def gate_id(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        ...

    def can_evaluate(self, inputs: dict[str, Any]) -> bool:
        return True


def _verdict(
    *,
    gate: GovernanceGate,
    decision: Decision,
    evidence: dict[str, Any],
    reason_codes: list[str] | None = None,
    recommended_actions: list[str] | None = None,
    rejection_type: str | None = None,
    confidence: float | None = None,
) -> VerdictContract:
    """Build a standard gate verdict from a GovernanceGate instance."""
    return VerdictContract(
        decision=decision,
        gate_id=gate.gate_id,
        evidence=evidence,
        reason_codes=reason_codes or [],
        recommended_actions=recommended_actions or [],
        confidence=confidence,
        evaluator_version=gate.version,
        rejection_type=rejection_type,
    )


@dataclass(frozen=True)
class EvaluatorResult:
    """Structured output from a domain evaluator."""

    metrics: dict[str, float]
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_output: Any = None


class DomainEvaluator(ABC):
    """Domain-specific validator used by governance gates."""

    @property
    @abstractmethod
    def domain(self) -> str:
        ...

    @property
    @abstractmethod
    def evaluator_id(self) -> str:
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        ...

    @abstractmethod
    def evaluate(self, data: Any, **kwargs: Any) -> EvaluatorResult:
        ...
