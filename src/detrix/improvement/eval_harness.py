"""Evaluation harness — generic step evaluators for pipeline outputs.

Provides an ABC for step evaluation plus concrete implementations
for JSON structure matching and tool call validation.
Generalized from Fledgling's eval.py.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


class StepEvaluator(ABC):
    """Abstract base for evaluating step outputs against references."""

    @abstractmethod
    def evaluate(
        self, predictions: list[Any], references: list[Any]
    ) -> dict[str, float]:
        """Compare predictions to references, return named metrics (0.0–1.0)."""
        ...


def canonical_json(text: str) -> tuple[bool, str]:
    """Attempt to parse JSON and return a canonical form."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return False, ""
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    return True, canonical


class JSONEvaluator(StepEvaluator):
    """Evaluate structured JSON outputs for validity and exact match."""

    def evaluate(
        self, predictions: list[Any], references: list[Any]
    ) -> dict[str, float]:
        valid = 0
        matches = 0
        for pred, ref in zip(predictions, references, strict=False):
            pred_str = pred if isinstance(pred, str) else json.dumps(pred)
            ref_str = ref if isinstance(ref, str) else json.dumps(ref)
            ok, canonical_pred = canonical_json(pred_str)
            if ok:
                valid += 1
            ok_ref, canonical_ref = canonical_json(ref_str)
            if ok and ok_ref and canonical_pred == canonical_ref:
                matches += 1
        total = len(references) or 1
        return {
            "json_valid_rate": valid / total,
            "exact_match_rate": matches / total,
        }


_TOOLCALL_RE = re.compile(
    r'^<tool_call name="(?P<name>[^"]+)">\s*(?P<body>\{.*\})\s*</tool_call>\s*$',
    re.DOTALL,
)


def _parse_tool_call(text: str) -> tuple[bool, str, str]:
    """Parse a tool call from text, returning (valid, name, canonical_args)."""
    match = _TOOLCALL_RE.match(text.strip())
    if not match:
        return False, "", ""
    name = match.group("name")
    body = match.group("body")
    ok, canonical = canonical_json(body)
    if not ok:
        return False, "", ""
    return True, name, canonical


class ToolCallEvaluator(StepEvaluator):
    """Evaluate tool call outputs for format validity, name match, and arg match."""

    def evaluate(
        self, predictions: list[Any], references: list[Any]
    ) -> dict[str, float]:
        valid_calls = 0
        name_matches = 0
        args_matches = 0
        for pred, ref in zip(predictions, references, strict=False):
            pred_str = pred if isinstance(pred, str) else str(pred)
            ref_str = ref if isinstance(ref, str) else str(ref)
            pred_ok, pred_name, pred_args = _parse_tool_call(pred_str)
            ref_ok, ref_name, ref_args = _parse_tool_call(ref_str)
            if pred_ok:
                valid_calls += 1
            if pred_ok and ref_ok and pred_name == ref_name:
                name_matches += 1
            if pred_ok and ref_ok and pred_args == ref_args:
                args_matches += 1
        total = len(references) or 1
        return {
            "valid_call_rate": valid_calls / total,
            "name_match_rate": name_matches / total,
            "args_exact_rate": args_matches / total,
        }
