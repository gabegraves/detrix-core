"""Shared enums and verdict types for the detrix runtime."""

from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    """Outcome of a model promotion comparison."""

    PROMOTE = "promote"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"
