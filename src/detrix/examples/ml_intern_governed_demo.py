"""Governed AgentXRD/AXV2 demo using ml-intern as a training worker.

The demo boundary is intentionally post-hoc: TrainingExporter selects admitted
trajectories, MLInternWorker attempts training work, then Detrix promotion logic
compares held-out/domain metrics. The worker does not evaluate or promote.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from detrix.core.types import Verdict
from detrix.improvement.exporter import TrainingExporter
from detrix.improvement.promoter import ModelPromoter, PromotionResult
from detrix.runtime.trajectory_store import TrajectoryStore
from detrix.workers.ml_intern import MLInternPrivacyError, MLInternResult, MLInternWorker


class GovernedMLInternDemoReport(BaseModel):
    """Report for the governed ml-intern demo handoff."""

    sft_export_path: str
    training_rows: int
    worker_result: MLInternResult
    incumbent_metrics: dict[str, float]
    challenger_metrics: dict[str, float]
    promotion: PromotionResult
    verdict: Verdict
    reason_codes: list[str] = Field(default_factory=list)
    report_path: str | None = None


def run_governed_ml_intern_demo(
    *,
    evidence_db: str,
    output_dir: str,
    worker: MLInternWorker,
    worker_prompt: str,
    incumbent_metrics: dict[str, float],
    challenger_metrics: dict[str, float],
    domain: str = "xrd",
    min_score: float | None = None,
) -> GovernedMLInternDemoReport:
    """Run AXV2 trajectory -> export -> ml-intern worker -> Detrix verdict.

    `incumbent_metrics` and `challenger_metrics` represent post-hoc Detrix/domain
    evaluation on held-out data. A challenger is rejected if `pass_rate` regresses
    by any amount, even if other metrics improve.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    store = TrajectoryStore(evidence_db)
    exporter = TrainingExporter(store)
    sft_export_path = exporter.export_sft(
        str(out / "training" / "sft.jsonl"),
        domain=domain,
        min_score=min_score,
        limit=None,
    )
    training_rows = _count_jsonl_rows(sft_export_path)

    prompt = (
        f"{worker_prompt}\n\n"
        "Use only the Detrix-exported SFT data at this path: "
        f"{sft_export_path}\n"
        "Write only allowlisted training artifacts under DETRIX_MLINTERN_OUTPUT_DIR."
    )
    worker_result = worker.run(prompt)

    reason_codes: list[str] = []
    if worker_result.redaction_status == "blocked":
        promotion = _reject_promotion(
            incumbent_metrics,
            challenger_metrics,
            reason_metric="artifact_privacy",
        )
        reason_codes.append("ml_intern_artifact_blocked")
    else:
        if _pass_rate_regressed(incumbent_metrics, challenger_metrics):
            promotion = _reject_promotion(
                incumbent_metrics,
                challenger_metrics,
                reason_metric="pass_rate",
            )
            reason_codes.append("pass_rate_regressed")
        else:
            promotion = ModelPromoter(
                metric_names=sorted(set(incumbent_metrics) | set(challenger_metrics))
            ).compare(challenger_metrics, incumbent_metrics, threshold=0.0)
            if promotion.verdict == Verdict.REJECT:
                reason_codes.extend(
                    f"metric_regressed:{metric}"
                    for metric in promotion.metrics_exceeding_threshold
                )

    verdict = promotion.verdict
    report = GovernedMLInternDemoReport(
        sft_export_path=sft_export_path,
        training_rows=training_rows,
        worker_result=worker_result,
        incumbent_metrics=incumbent_metrics,
        challenger_metrics=challenger_metrics,
        promotion=promotion,
        verdict=verdict,
        reason_codes=reason_codes,
    )
    report_path = out / "reports" / "mlintern_governed_demo_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report.report_path = str(report_path)
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def _count_jsonl_rows(path: str) -> int:
    with open(path, encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def _pass_rate_regressed(
    incumbent_metrics: dict[str, float],
    challenger_metrics: dict[str, float],
) -> bool:
    incumbent_pass_rate = incumbent_metrics.get("pass_rate")
    challenger_pass_rate = challenger_metrics.get("pass_rate")
    if incumbent_pass_rate is None or challenger_pass_rate is None:
        return False
    return challenger_pass_rate < incumbent_pass_rate


def _reject_promotion(
    incumbent_metrics: dict[str, float],
    challenger_metrics: dict[str, float],
    *,
    reason_metric: str,
) -> PromotionResult:
    metrics = sorted(set(incumbent_metrics) | set(challenger_metrics) | {reason_metric})
    deltas = {metric: incumbent_metrics.get(metric, 0.0) - challenger_metrics.get(metric, 0.0) for metric in metrics}
    return PromotionResult(
        verdict=Verdict.REJECT,
        metric_deltas=deltas,
        threshold=0.0,
        metrics_exceeding_threshold=[reason_metric],
    )


def ensure_worker_artifacts_can_enter_demo(result: MLInternResult) -> None:
    """Public helper for callers that want explicit fail-closed artifact gating."""
    if result.redaction_status == "blocked":
        raise MLInternPrivacyError("blocked ml-intern result cannot enter governed demo")


def report_to_markdown(report: GovernedMLInternDemoReport) -> str:
    """Render the promote/reject handoff as human-readable markdown."""
    return "\n".join(
        [
            "# Governed ml-intern Demo Report",
            "",
            f"Verdict: **{report.verdict.value}**",
            f"Training rows: {report.training_rows}",
            f"SFT export: `{report.sft_export_path}`",
            f"Worker redaction status: `{report.worker_result.redaction_status}`",
            "",
            "## Incumbent metrics",
            f"```json\n{json.dumps(report.incumbent_metrics, indent=2, sort_keys=True)}\n```",
            "",
            "## Challenger metrics",
            f"```json\n{json.dumps(report.challenger_metrics, indent=2, sort_keys=True)}\n```",
            "",
            "## Reason codes",
            ", ".join(report.reason_codes) or "<none>",
        ]
    )
