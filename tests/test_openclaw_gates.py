from __future__ import annotations

from detrix.core.governance import Decision, GateContext
from detrix.openclaw.gates import (
    ApologyGate,
    InlineBulletGate,
    MessageLengthGate,
    OpenClawGovernanceGate,
    ParagraphDensityGate,
)


def _context(**config: object) -> GateContext:
    return GateContext(run_id="test", step_index=0, prior_verdicts=[], config=dict(config))


def test_message_length_gate_uses_configured_thresholds_and_telegram_limit() -> None:
    gate = MessageLengthGate()

    assert gate.evaluate({"message": "x" * 20}, _context(max_length=50)).decision == Decision.ACCEPT

    caution = gate.evaluate({"message": "x" * 60}, _context(max_length=50))
    assert caution.decision == Decision.CAUTION
    assert "needs_chunking" in caution.reason_codes

    reject = gate.evaluate({"message": "x" * 4097}, _context(max_length=50))
    assert reject.decision == Decision.REJECT
    assert reject.rejection_type == "output_quality"


def test_paragraph_density_gate_detects_wall_of_text() -> None:
    verdict = ParagraphDensityGate().evaluate(
        {"message": "This paragraph is too dense. " * 40},
        _context(max_paragraph_chars=120),
    )

    assert verdict.decision == Decision.CAUTION
    assert "paragraph_density_exceeded" in verdict.reason_codes
    assert verdict.evidence["dense_paragraphs"] == 1


def test_inline_bullet_gate_detects_inline_separator_antipattern() -> None:
    text = "Alert summary: • alpha detail • beta detail • gamma detail • delta detail " * 2

    verdict = InlineBulletGate().evaluate({"message": text}, _context())

    assert verdict.decision == Decision.CAUTION
    assert "inline_bullet_anti_pattern" in verdict.reason_codes
    assert verdict.evidence["inline_bullet_count"] >= 3


def test_apology_gate_detects_leading_apology_as_content() -> None:
    verdict = ApologyGate().evaluate(
        {"message": "I apologize for the formatting. Here is the answer."},
        _context(),
    )

    assert verdict.decision == Decision.CAUTION
    assert "apology_as_content" in verdict.reason_codes
    assert verdict.evidence["has_apology_prefix"] is True


def test_openclaw_composite_aggregates_child_verdicts_and_preserves_reject_priority() -> None:
    caution = OpenClawGovernanceGate().evaluate(
        {"message": "Alert summary: • alpha detail • beta detail • gamma detail • delta detail " * 2},
        _context(),
    )
    assert caution.decision == Decision.CAUTION
    assert len(caution.evidence["child_verdicts"]) == 4

    reject = OpenClawGovernanceGate().evaluate({"message": "x" * 4097}, _context())
    assert reject.decision == Decision.REJECT
    assert "message_length_exceeded" in reject.reason_codes
