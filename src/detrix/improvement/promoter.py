"""ModelPromoter — compare challenger vs incumbent models on named metrics.

Generalized from Fledgling's compare.py. Works with any metric names,
no external dependencies required.
"""

from __future__ import annotations

from pydantic import BaseModel

from detrix.core.types import Verdict


class PromotionResult(BaseModel):
    """Outcome of a challenger-vs-incumbent comparison."""

    verdict: Verdict
    metric_deltas: dict[str, float]
    threshold: float
    metrics_exceeding_threshold: list[str]


class ModelPromoter:
    """Compare two sets of metrics and decide whether to promote the challenger."""

    def __init__(self, metric_names: list[str] | None = None):
        self.metric_names = metric_names

    def compare(
        self,
        challenger: dict[str, float],
        incumbent: dict[str, float],
        threshold: float = 0.1,
    ) -> PromotionResult:
        """Compare challenger against incumbent.

        The challenger should be promoted if the incumbent does NOT beat it
        by more than `threshold` on any tracked metric. In other words,
        if incumbent - challenger > threshold for any metric, reject.
        """
        metrics_to_check = self.metric_names or sorted(
            set(challenger.keys()) | set(incumbent.keys())
        )

        deltas: dict[str, float] = {}
        exceeding: list[str] = []

        for metric in metrics_to_check:
            inc_val = incumbent.get(metric, 0.0)
            chal_val = challenger.get(metric, 0.0)
            gap = inc_val - chal_val
            deltas[metric] = gap
            if gap > threshold:
                exceeding.append(metric)

        if exceeding:
            verdict = Verdict.REJECT
        else:
            verdict = Verdict.PROMOTE

        return PromotionResult(
            verdict=verdict,
            metric_deltas=deltas,
            threshold=threshold,
            metrics_exceeding_threshold=exceeding,
        )
