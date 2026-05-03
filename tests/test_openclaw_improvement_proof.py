from __future__ import annotations

from detrix.openclaw.improvement_proof import (
    GeneratedOutput,
    ProofCase,
    TargetScore,
    _autocast_dtype,
    compare_candidates,
    compare_target_scores,
    evaluate_candidate,
    generate_outputs,
    validate_output_coverage,
)


def test_improvement_proof_promotes_gate_score_gain_without_precision_regression() -> None:
    cases = [
        ProofCase(
            case_id="c1",
            prompt="Draft: I'm sorry for the confusion. Build succeeded.",
            expected_contains=["Build succeeded"],
            forbidden_contains=["sorry", "apologize"],
        ),
        ProofCase(
            case_id="c2",
            prompt="Draft: Do A • Do B • Do C • Do D in one long line.",
            expected_contains=["Do A"],
            forbidden_contains=["•"],
        ),
    ]
    baseline = evaluate_candidate(
        "baseline",
        cases,
        {
            "c1": "I'm sorry for the confusion. Build succeeded.",
            "c2": "Do A • Do B • Do C • Do D " * 8,
        },
        gate_config={"max_paragraph_chars": 80},
    )
    challenger = evaluate_candidate(
        "adapter",
        cases,
        {
            "c1": "Build succeeded.",
            "c2": "Do A\nDo B\nDo C\nDo D",
        },
        gate_config={"max_paragraph_chars": 80},
    )

    report = compare_candidates(baseline, challenger)

    assert report.improved is True
    assert report.precision_regression is False
    assert report.promotion_allowed is True
    assert report.metric_deltas["mean_gate_score"] > 0


def test_generate_outputs_uses_injected_callable_for_unit_speed() -> None:
    cases = [ProofCase(case_id="c1", prompt="Draft: sorry hi")]

    generated = generate_outputs(cases, lambda prompt: "Clean reply" if "sorry" in prompt else "")

    assert generated == [GeneratedOutput(case_id="c1", output="Clean reply")]


def test_empty_output_is_rejected_and_not_promoted() -> None:
    cases = [
        ProofCase(
            case_id="c1",
            prompt="Draft: Build passed.",
            expected_contains=["Build passed"],
            forbidden_contains=["sorry"],
        )
    ]
    baseline = evaluate_candidate(
        "baseline",
        cases,
        {"c1": "Build passed."},
    )
    challenger = evaluate_candidate(
        "adapter",
        cases,
        {"c1": ""},
    )

    report = compare_candidates(baseline, challenger)

    assert challenger.reject_rate == 1.0
    assert challenger.reason_counts["empty_output"] == 1
    assert report.promotion_allowed is False
    assert report.precision_regression is True


def test_empty_challenger_cannot_promote_when_baseline_also_rejects() -> None:
    cases = [
        ProofCase(
            case_id="c1",
            prompt="Draft: sorry",
            expected_contains=[],
            forbidden_contains=["sorry"],
        )
    ]
    baseline = evaluate_candidate(
        "baseline",
        cases,
        {"c1": "sorry " * 900},
    )
    challenger = evaluate_candidate(
        "adapter",
        cases,
        {"c1": ""},
    )

    report = compare_candidates(baseline, challenger)

    assert baseline.reject_rate == 1.0
    assert challenger.reject_rate == 1.0
    assert challenger.reason_counts["empty_output"] == 1
    assert report.metric_deltas["forbidden_absent_rate"] > 0
    assert report.improved is False
    assert report.promotion_allowed is False


def test_target_score_comparison_requires_loss_delta() -> None:
    baseline = TargetScore(name="baseline", mean_loss=2.0, case_losses={"c1": 2.0})
    challenger = TargetScore(name="adapter", mean_loss=1.5, case_losses={"c1": 1.5})

    report = compare_target_scores(baseline, challenger, min_loss_delta=0.1)

    assert report.improved is True
    assert report.loss_delta == 0.5
    assert report.proof_type == "target_likelihood"
    assert report.promotion_allowed is False


def test_output_coverage_fails_closed_for_missing_or_extra_outputs() -> None:
    cases = [ProofCase(case_id="c1", prompt="Draft: Build passed.")]

    try:
        validate_output_coverage(cases, {"c2": "Build passed."})
    except ValueError as exc:
        assert "missing=['c1']" in str(exc)
        assert "unexpected=['c2']" in str(exc)
    else:
        raise AssertionError("expected missing/extra output coverage failure")


def test_expected_phrase_gain_does_not_promote_gate_regression() -> None:
    cases = [
        ProofCase(
            case_id="c1",
            prompt="Draft: Build passed.",
            expected_contains=["Build passed"],
            forbidden_contains=["sorry"],
        )
    ]
    baseline = evaluate_candidate(
        "baseline",
        cases,
        {"c1": "Build passed."},
    )
    challenger = evaluate_candidate(
        "adapter",
        cases,
        {"c1": "Build passed. " * 80},
        gate_config={"max_message_chars": 120},
    )

    report = compare_candidates(baseline, challenger)

    assert report.improved is False
    assert report.precision_regression is True
    assert report.promotion_allowed is False


def test_autocast_dtype_falls_back_when_bf16_is_unavailable() -> None:
    class FakeCuda:
        @staticmethod
        def is_bf16_supported() -> bool:
            return False

    class FakeTorch:
        cuda = FakeCuda()
        bfloat16 = object()
        float16 = "fp16"

    assert _autocast_dtype(FakeTorch, "cuda") == "fp16"
    assert _autocast_dtype(FakeTorch, "cpu") is None
