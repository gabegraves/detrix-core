"""Deterministic OpenClaw readability governance gates."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from detrix.core.governance import Decision, GateContext, GovernanceGate, VerdictContract, _verdict

TELEGRAM_LIMIT = 4096


def _message_text(inputs: dict[str, Any]) -> str:
    for key in ("message", "agent_output", "completion", "output", "text"):
        value = inputs.get(key)
        if value is not None:
            return str(value)
    return ""


class MessageLengthGate(GovernanceGate):
    """Detect messages that are too long for delivery or comfortable reading."""

    @property
    def gate_id(self) -> str:
        return "openclaw_message_length_gate"

    @property
    def version(self) -> str:
        return "0.1"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        text = _message_text(inputs)
        max_length = int(context.config.get("max_length", 2000))
        char_count = len(text)
        evidence = {
            "char_count": char_count,
            "word_count": len(text.split()),
            "max_length": max_length,
            "telegram_limit": TELEGRAM_LIMIT,
        }
        if char_count > TELEGRAM_LIMIT:
            return _verdict(
                gate=self,
                decision=Decision.REJECT,
                evidence=evidence,
                reason_codes=["message_length_exceeded"],
                recommended_actions=["split_message_before_telegram_delivery"],
                rejection_type="output_quality",
            )
        if char_count > max_length:
            return _verdict(
                gate=self,
                decision=Decision.CAUTION,
                evidence=evidence,
                reason_codes=["needs_chunking"],
                recommended_actions=["chunk_or_summarize_message"],
            )
        return _verdict(gate=self, decision=Decision.ACCEPT, evidence=evidence)


class ParagraphDensityGate(GovernanceGate):
    """Detect dense wall-of-text paragraphs."""

    @property
    def gate_id(self) -> str:
        return "openclaw_paragraph_density_gate"

    @property
    def version(self) -> str:
        return "0.1"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        text = _message_text(inputs)
        max_paragraph_chars = int(context.config.get("max_paragraph_chars", 500))
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
        lengths = [len(p) for p in paragraphs]
        dense = [length for length in lengths if length > max_paragraph_chars]
        evidence = {
            "paragraph_count": len(paragraphs),
            "max_paragraph_length": max(lengths, default=0),
            "avg_paragraph_length": (sum(lengths) / len(lengths)) if lengths else 0.0,
            "dense_paragraphs": len(dense),
            "max_paragraph_chars": max_paragraph_chars,
        }
        if dense:
            return _verdict(
                gate=self,
                decision=Decision.CAUTION,
                evidence=evidence,
                reason_codes=["paragraph_density_exceeded", "needs_chunking"],
                recommended_actions=["insert_paragraph_breaks_or_bullets"],
            )
        return _verdict(gate=self, decision=Decision.ACCEPT, evidence=evidence)


class InlineBulletGate(GovernanceGate):
    """Detect inline bullet separators that should be line breaks."""

    @property
    def gate_id(self) -> str:
        return "openclaw_inline_bullet_gate"

    @property
    def version(self) -> str:
        return "0.1"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        del context
        text = _message_text(inputs)
        bullet_char = "•"
        runs = [line for line in text.splitlines() if len(line) >= 80 and line.count(bullet_char) >= 3]
        evidence = {
            "inline_bullet_count": sum(line.count(bullet_char) for line in runs),
            "longest_bullet_run_chars": max((len(line) for line in runs), default=0),
            "bullet_char": bullet_char,
        }
        if runs:
            return _verdict(
                gate=self,
                decision=Decision.CAUTION,
                evidence=evidence,
                reason_codes=["inline_bullet_anti_pattern", "needs_reformat"],
                recommended_actions=["replace_inline_bullets_with_newline_list"],
            )
        return _verdict(gate=self, decision=Decision.ACCEPT, evidence=evidence)


class ApologyGate(GovernanceGate):
    """Detect apology boilerplate that consumes the response."""

    APOLOGY_RE = re.compile(r"^\s*(i apologize|sorry for|i['’]m sorry)\b", re.IGNORECASE)

    @property
    def gate_id(self) -> str:
        return "openclaw_apology_gate"

    @property
    def version(self) -> str:
        return "0.1"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        del context
        text = _message_text(inputs)
        match = self.APOLOGY_RE.search(text)
        evidence = {
            "has_apology_prefix": match is not None,
            "apology_text": match.group(0).strip() if match else "",
            "content_after_apology_chars": len(text[match.end() :].strip()) if match else len(text),
        }
        if match:
            return _verdict(
                gate=self,
                decision=Decision.CAUTION,
                evidence=evidence,
                reason_codes=["apology_as_content", "needs_reformat"],
                recommended_actions=["remove_apology_boilerplate_and_answer_directly"],
            )
        return _verdict(gate=self, decision=Decision.ACCEPT, evidence=evidence)


class OpenClawGovernanceGate(GovernanceGate):
    """Composite OpenClaw readability gate suite."""

    def __init__(self, gates: Iterable[GovernanceGate] | None = None) -> None:
        self.gates = list(
            gates
            if gates is not None
            else (
                MessageLengthGate(),
                ParagraphDensityGate(),
                InlineBulletGate(),
                ApologyGate(),
            )
        )

    @property
    def gate_id(self) -> str:
        return "openclaw_governance_gate_suite"

    @property
    def version(self) -> str:
        child_versions = ",".join(f"{gate.gate_id}:{gate.version}" for gate in self.gates)
        return f"0.1[{child_versions}]"

    def evaluate(self, inputs: dict[str, Any], context: GateContext) -> VerdictContract:
        child_verdicts = [gate.evaluate(inputs, context) for gate in self.gates]
        rejects = [verdict for verdict in child_verdicts if verdict.decision == Decision.REJECT]
        cautions = [verdict for verdict in child_verdicts if verdict.decision == Decision.CAUTION]
        failing = rejects or cautions
        decision = Decision.ACCEPT if not failing else failing[0].decision
        return VerdictContract(
            decision=decision,
            gate_id=self.gate_id,
            evidence={"child_verdicts": [verdict.to_dict() for verdict in child_verdicts]},
            reason_codes=[reason for verdict in failing for reason in verdict.reason_codes],
            recommended_actions=[
                action for verdict in failing for action in verdict.recommended_actions
            ],
            evaluator_version=self.version,
            rejection_type=failing[0].rejection_type if failing else None,
        )
