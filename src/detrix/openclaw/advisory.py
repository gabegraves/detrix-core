"""Fail-open advisory readability scoring for OpenClaw."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from detrix.core.governance import Decision, GateContext, GovernanceGate, VerdictContract, _verdict
from detrix.openclaw.gates import _message_text

AdvisoryScorer = Callable[[str], dict[str, Any]]


class ReadabilityAdvisoryGate(GovernanceGate):
    """Tier-2 LLM/readability advisory gate that never blocks admission."""

    def __init__(self, scorer: AdvisoryScorer | None = None, *, model_id: str = "stub") -> None:
        self.scorer = scorer
        self.model_id = model_id

    @property
    def gate_id(self) -> str:
        return "openclaw_readability_advisory_gate"

    @property
    def version(self) -> str:
        return f"0.1:{self.model_id}"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        min_score = float(context.config.get("advisory_min_score", 6.0))
        text = _message_text(inputs)
        try:
            result = self._score(text)
        except Exception as exc:  # pragma: no cover - defensive fail-open boundary
            return _verdict(
                gate=self,
                decision=Decision.ACCEPT,
                evidence={
                    "readability_score": None,
                    "model_id": self.model_id,
                    "model_version": self.version,
                    "fallback": "model_unavailable",
                    "error": str(exc),
                },
            )
        score = result.get("readability_score")
        evidence = {
            "readability_score": score,
            "model_id": self.model_id,
            "model_version": self.version,
            "assessment_text": result.get("assessment_text", ""),
            "advisory_only": True,
        }
        if isinstance(score, int | float) and float(score) < min_score:
            return _verdict(
                gate=self,
                decision=Decision.CAUTION,
                evidence=evidence,
                reason_codes=["low_readability_advisory"],
                recommended_actions=["human_review_readability_before_using_as_positive_training_row"],
                confidence=0.5,
            )
        return _verdict(gate=self, decision=Decision.ACCEPT, evidence=evidence, confidence=0.5)

    def _score(self, text: str) -> dict[str, Any]:
        if self.scorer is not None:
            return self.scorer(text)
        return {
            "readability_score": None,
            "assessment_text": "No advisory model configured; deterministic gates remain authoritative.",
        }
