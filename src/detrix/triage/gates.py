"""Generic triage gates that work across any agent domain."""

from __future__ import annotations

import json
from typing import Any

from detrix.core.governance import Decision, GateContext, GovernanceGate, VerdictContract


class OutputFormatGate(GovernanceGate):
    """Check that agent output is well-formed JSON with expected keys."""

    def __init__(self, required_keys: set[str] | None = None) -> None:
        self._required_keys = required_keys or set()

    @property
    def gate_id(self) -> str:
        return "output_format"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        completion = inputs.get("completion", "")

        if not completion or not str(completion).strip():
            return VerdictContract(
                decision=Decision.REJECT,
                gate_id=self.gate_id,
                evidence={"completion_length": 0, "required_keys": sorted(self._required_keys)},
                reason_codes=["empty_output"],
                recommended_actions=["check_agent_produced_output"],
                evaluator_version=self.version,
                rejection_type="output_quality",
            )

        parsed = None
        if isinstance(completion, str):
            try:
                parsed = json.loads(completion)
            except (json.JSONDecodeError, ValueError):
                pass
        elif isinstance(completion, dict):
            parsed = completion

        if self._required_keys and parsed is not None and isinstance(parsed, dict):
            missing = self._required_keys - set(parsed.keys())
            if missing:
                return VerdictContract(
                    decision=Decision.REJECT,
                    gate_id=self.gate_id,
                    evidence={
                        "missing_keys": sorted(missing),
                        "present_keys": sorted(parsed.keys()),
                        "required_keys": sorted(self._required_keys),
                    },
                    reason_codes=["missing_required_keys"],
                    recommended_actions=["fix_output_schema"],
                    evaluator_version=self.version,
                    rejection_type="output_quality",
                )

        return VerdictContract(
            decision=Decision.ACCEPT,
            gate_id=self.gate_id,
            evidence={
                "completion_length": len(str(completion)),
                "is_json": parsed is not None,
            },
            evaluator_version=self.version,
        )


class LatencyAnomalyGate(GovernanceGate):
    """Flag traces where response latency is anomalously high."""

    def __init__(self, max_latency_ms: float = 120_000) -> None:
        self.max_latency_ms = max_latency_ms

    @property
    def gate_id(self) -> str:
        return "latency_anomaly"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        latency = inputs.get("latency_ms") or inputs.get("duration_ms")

        if latency is None:
            return VerdictContract(
                decision=Decision.ACCEPT,
                gate_id=self.gate_id,
                evidence={"latency_ms": None, "max_latency_ms": self.max_latency_ms},
                evaluator_version=self.version,
            )

        latency_val = float(latency)
        if latency_val > self.max_latency_ms:
            return VerdictContract(
                decision=Decision.CAUTION,
                gate_id=self.gate_id,
                evidence={"latency_ms": latency_val, "max_latency_ms": self.max_latency_ms},
                reason_codes=["latency_anomaly"],
                recommended_actions=["investigate_retry_storm_or_timeout"],
                evaluator_version=self.version,
                rejection_type="input_quality",
            )

        return VerdictContract(
            decision=Decision.ACCEPT,
            gate_id=self.gate_id,
            evidence={"latency_ms": latency_val, "max_latency_ms": self.max_latency_ms},
            evaluator_version=self.version,
        )


class CostAnomalyGate(GovernanceGate):
    """Flag traces where token usage is anomalously high (possible infinite loop)."""

    def __init__(self, max_tokens: int = 50_000) -> None:
        self.max_tokens = max_tokens

    @property
    def gate_id(self) -> str:
        return "cost_anomaly"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        tokens = inputs.get("total_tokens") or inputs.get("token_count")

        if tokens is None:
            return VerdictContract(
                decision=Decision.ACCEPT,
                gate_id=self.gate_id,
                evidence={"total_tokens": None, "max_tokens": self.max_tokens},
                evaluator_version=self.version,
            )

        token_val = int(tokens)
        if token_val > self.max_tokens:
            return VerdictContract(
                decision=Decision.CAUTION,
                gate_id=self.gate_id,
                evidence={"total_tokens": token_val, "max_tokens": self.max_tokens},
                reason_codes=["token_usage_anomaly"],
                recommended_actions=["investigate_infinite_loop_or_excessive_retries"],
                evaluator_version=self.version,
                rejection_type="input_quality",
            )

        return VerdictContract(
            decision=Decision.ACCEPT,
            gate_id=self.gate_id,
            evidence={"total_tokens": token_val, "max_tokens": self.max_tokens},
            evaluator_version=self.version,
        )
