from __future__ import annotations

from detrix.core.governance import Decision, GateContext
from detrix.openclaw.advisory import ReadabilityAdvisoryGate


def _context() -> GateContext:
    return GateContext(run_id="test", step_index=0, prior_verdicts=[], config={"advisory_min_score": 6})


def test_advisory_gate_accepts_without_configured_model() -> None:
    verdict = ReadabilityAdvisoryGate().evaluate({"message": "text"}, _context())

    assert verdict.decision == Decision.ACCEPT
    assert verdict.evidence["readability_score"] is None


def test_advisory_gate_returns_caution_but_never_reject_for_low_score() -> None:
    gate = ReadabilityAdvisoryGate(lambda _: {"readability_score": 3, "assessment_text": "poor"})

    verdict = gate.evaluate({"message": "text"}, _context())

    assert verdict.decision == Decision.CAUTION
    assert verdict.decision != Decision.REJECT
    assert "low_readability_advisory" in verdict.reason_codes


def test_advisory_gate_fails_open_on_model_error() -> None:
    def broken(_: str) -> dict[str, object]:
        raise RuntimeError("model down")

    verdict = ReadabilityAdvisoryGate(broken, model_id="local-qwen").evaluate(
        {"message": "text"},
        _context(),
    )

    assert verdict.decision == Decision.ACCEPT
    assert verdict.evidence["fallback"] == "model_unavailable"
