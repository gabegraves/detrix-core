"""Tests for ModelPromoter and evaluation harness."""

import pytest

from detrix.core.types import Verdict
from detrix.improvement.promoter import ModelPromoter, PromotionResult
from detrix.improvement.eval_harness import (
    JSONEvaluator,
    ToolCallEvaluator,
    canonical_json,
)


class TestModelPromoter:
    def test_challenger_promoted_when_close(self):
        promoter = ModelPromoter()
        result = promoter.compare(
            challenger={"accuracy": 0.90, "f1": 0.88},
            incumbent={"accuracy": 0.92, "f1": 0.89},
            threshold=0.1,
        )
        assert result.verdict == Verdict.PROMOTE
        assert len(result.metrics_exceeding_threshold) == 0

    def test_challenger_rejected_when_gap_too_large(self):
        promoter = ModelPromoter()
        result = promoter.compare(
            challenger={"accuracy": 0.70},
            incumbent={"accuracy": 0.95},
            threshold=0.1,
        )
        assert result.verdict == Verdict.REJECT
        assert "accuracy" in result.metrics_exceeding_threshold

    def test_custom_metric_names(self):
        promoter = ModelPromoter(metric_names=["precision", "recall"])
        result = promoter.compare(
            challenger={"precision": 0.85, "recall": 0.80, "f1": 0.50},
            incumbent={"precision": 0.90, "recall": 0.82, "f1": 0.95},
            threshold=0.1,
        )
        # Only checks precision and recall, not f1
        assert result.verdict == Verdict.PROMOTE
        assert "precision" in result.metric_deltas
        assert "recall" in result.metric_deltas

    def test_missing_metric_defaults_to_zero(self):
        promoter = ModelPromoter(metric_names=["accuracy"])
        result = promoter.compare(
            challenger={},
            incumbent={"accuracy": 0.5},
            threshold=0.1,
        )
        assert result.verdict == Verdict.REJECT

    def test_exact_threshold_boundary(self):
        promoter = ModelPromoter()
        # Gap == threshold exactly should NOT reject (must exceed)
        result = promoter.compare(
            challenger={"acc": 0.80},
            incumbent={"acc": 0.90},
            threshold=0.10,
        )
        assert result.verdict == Verdict.PROMOTE


class TestCanonicalJSON:
    def test_valid_json(self):
        ok, canon = canonical_json('{"b": 2, "a": 1}')
        assert ok
        assert canon == '{"a":1,"b":2}'

    def test_invalid_json(self):
        ok, canon = canonical_json("not json")
        assert not ok
        assert canon == ""

    def test_nested_json(self):
        ok, canon = canonical_json('{"a": {"c": 3, "b": 2}}')
        assert ok
        assert '"b":2' in canon


class TestJSONEvaluator:
    def test_perfect_match(self):
        evaluator = JSONEvaluator()
        preds = ['{"a": 1}', '{"b": 2}']
        refs = ['{"a": 1}', '{"b": 2}']
        metrics = evaluator.evaluate(preds, refs)
        assert metrics["json_valid_rate"] == 1.0
        assert metrics["exact_match_rate"] == 1.0

    def test_partial_match(self):
        evaluator = JSONEvaluator()
        preds = ['{"a": 1}', '{"b": 99}']
        refs = ['{"a": 1}', '{"b": 2}']
        metrics = evaluator.evaluate(preds, refs)
        assert metrics["json_valid_rate"] == 1.0
        assert metrics["exact_match_rate"] == 0.5

    def test_invalid_json_pred(self):
        evaluator = JSONEvaluator()
        preds = ["not json", '{"b": 2}']
        refs = ['{"a": 1}', '{"b": 2}']
        metrics = evaluator.evaluate(preds, refs)
        assert metrics["json_valid_rate"] == 0.5

    def test_empty_lists(self):
        evaluator = JSONEvaluator()
        metrics = evaluator.evaluate([], [])
        assert metrics["json_valid_rate"] == 0.0
        assert metrics["exact_match_rate"] == 0.0


class TestToolCallEvaluator:
    def test_valid_tool_call(self):
        evaluator = ToolCallEvaluator()
        pred = '<tool_call name="search">{"query": "test"}</tool_call>'
        ref = '<tool_call name="search">{"query": "test"}</tool_call>'
        metrics = evaluator.evaluate([pred], [ref])
        assert metrics["valid_call_rate"] == 1.0
        assert metrics["name_match_rate"] == 1.0
        assert metrics["args_exact_rate"] == 1.0

    def test_name_mismatch(self):
        evaluator = ToolCallEvaluator()
        pred = '<tool_call name="lookup">{"query": "test"}</tool_call>'
        ref = '<tool_call name="search">{"query": "test"}</tool_call>'
        metrics = evaluator.evaluate([pred], [ref])
        assert metrics["valid_call_rate"] == 1.0
        assert metrics["name_match_rate"] == 0.0

    def test_invalid_format(self):
        evaluator = ToolCallEvaluator()
        pred = "just plain text"
        ref = '<tool_call name="search">{"query": "test"}</tool_call>'
        metrics = evaluator.evaluate([pred], [ref])
        assert metrics["valid_call_rate"] == 0.0
