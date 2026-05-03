"""Trace Triage Report generator — the free tier deliverable."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from detrix.core.governance import Decision, GateContext, GovernanceGate, VerdictContract
from detrix.demo.support_triage import ConfidenceGate, PiiGate
from detrix.triage.gates import CostAnomalyGate, LatencyAnomalyGate, OutputFormatGate


@dataclass
class Trace:
    trace_id: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class ScoredTrace:
    trace: Trace
    verdicts: list[VerdictContract]
    classification: str  # "safe", "agent_wrong", "bad_input", "needs_review"
    rejection_type: str | None  # "output_quality", "input_quality", None
    failed_gates: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)


def load_traces_jsonl(path: Path) -> list[Trace]:
    traces = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            traces.append(Trace(
                trace_id=row.get("trace_id", str(uuid.uuid4())[:8]),
                inputs=row.get("inputs", {}),
                outputs=row.get("outputs", {}),
                tool_calls=row.get("tool_calls", []),
                metadata=row.get("metadata", {}),
                timestamp=row.get("timestamp", ""),
            ))
    return traces


def default_gates() -> list[GovernanceGate]:
    return [
        ConfidenceGate(),
        PiiGate(),
        OutputFormatGate(),
        LatencyAnomalyGate(),
        CostAnomalyGate(),
    ]


def _build_gate_inputs(trace: Trace) -> dict[str, Any]:
    """Flatten trace into the dict shape gates expect."""
    gate_inputs: dict[str, Any] = {}
    gate_inputs.update(trace.inputs)
    gate_inputs.update(trace.outputs)
    gate_inputs.update(trace.metadata)
    if trace.tool_calls:
        gate_inputs["tool_calls"] = trace.tool_calls
    return gate_inputs


def _classify(verdicts: list[VerdictContract]) -> tuple[str, str | None]:
    """Classify a trace based on its gate verdicts.

    Returns (classification, rejection_type) where:
    - "safe" / None = all gates passed, safe to deploy and train on (SFT-positive)
    - "agent_wrong" / "output_quality" = agent produced bad output (DPO-negative)
    - "bad_input" / "input_quality" = bad input data, not agent's fault (exclude)
    - "needs_review" / None = gate couldn't evaluate, needs human review
    """
    for v in verdicts:
        if v.decision == Decision.REJECT:
            return ("agent_wrong", "output_quality") if v.rejection_type == "output_quality" else ("bad_input", "input_quality")
    for v in verdicts:
        if v.decision == Decision.REQUEST_MORE_DATA:
            return "needs_review", None
    for v in verdicts:
        if v.decision == Decision.CAUTION:
            rt = v.rejection_type
            if rt == "output_quality":
                return "agent_wrong", "output_quality"
            if rt == "input_quality":
                return "bad_input", "input_quality"
            return "agent_wrong", "output_quality"
    return "safe", None


def score_traces(
    traces: list[Trace],
    gates: list[GovernanceGate] | None = None,
    config: dict[str, Any] | None = None,
) -> list[ScoredTrace]:
    gates = gates or default_gates()
    config = config or {}
    scored = []

    for trace in traces:
        gate_inputs = _build_gate_inputs(trace)
        ctx = GateContext(
            run_id=trace.trace_id,
            step_index=0,
            prior_verdicts=[],
            config=config,
        )
        verdicts = []
        for gate in gates:
            if gate.can_evaluate(gate_inputs):
                verdict = gate.evaluate(gate_inputs, ctx)
                verdicts.append(verdict)
                ctx.prior_verdicts.append(verdict)

        classification, rejection_type = _classify(verdicts)
        failed = [v.gate_id for v in verdicts if v.decision not in {Decision.ACCEPT}]
        reasons = [r for v in verdicts for r in v.reason_codes]

        scored.append(ScoredTrace(
            trace=trace,
            verdicts=verdicts,
            classification=classification,
            rejection_type=rejection_type,
            failed_gates=failed,
            reason_codes=reasons,
        ))

    return scored


_CLASSIFICATION_LABELS = {
    "safe": ("✅ Safe to deploy & train", "SFT-positive"),
    "agent_wrong": ("❌ Agent was wrong", "DPO-negative — use as rejected example"),
    "bad_input": ("⚠️ Bad input data", "Exclude from training entirely"),
    "needs_review": ("🔍 Needs human review", "Cannot classify automatically"),
}

_CLASSIFICATION_ORDER = ["safe", "agent_wrong", "bad_input", "needs_review"]


def generate_report(
    scored: list[ScoredTrace],
    gates: list[GovernanceGate] | None = None,
    title: str = "Detrix Trace Triage Report",
) -> str:
    gates = gates or default_gates()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gate_names = ", ".join(g.gate_id for g in gates)
    counts = Counter(s.classification for s in scored)
    total = len(scored)

    lines = [
        f"# {title}",
        "",
        f"Generated: {now}  ",
        f"Traces scored: {total}  ",
        f"Gates applied: {gate_names}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Classification | Deployment | Training | Count | % |",
        "|---------------|------------|----------|-------|---|",
    ]

    for cls in _CLASSIFICATION_ORDER:
        count = counts.get(cls, 0)
        if total > 0:
            pct = f"{count / total * 100:.0f}%"
        else:
            pct = "0%"
        label, training = _CLASSIFICATION_LABELS[cls]
        lines.append(f"| {label} | {'Safe' if cls == 'safe' else 'Risk'} | {training} | {count} | {pct} |")

    lines.extend(["", "---", "", "## Top Failure Patterns", ""])

    reason_counts = Counter(r for s in scored for r in s.reason_codes)
    if reason_counts:
        for i, (reason, count) in enumerate(reason_counts.most_common(10), 1):
            lines.append(f"{i}. **{reason}** ({count} traces)")
    else:
        lines.append("No failures detected across all traces.")

    lines.extend(["", "---", "", "## Per-Trace Details", ""])
    lines.append("| Trace ID | Classification | Gates Failed | Top Reason |")
    lines.append("|----------|---------------|-------------|------------|")

    for s in scored:
        label, _ = _CLASSIFICATION_LABELS[s.classification]
        failed_str = f"{len(s.failed_gates)}/{len(s.verdicts)}"
        top_reason = s.reason_codes[0] if s.reason_codes else "—"
        lines.append(f"| {s.trace.trace_id} | {label} | {failed_str} | {top_reason} |")

    lines.extend([
        "",
        "---",
        "",
        "## What This Means",
        "",
        "### For Deployment",
        f"- **{counts.get('safe', 0)} traces** are safe to deploy — gates found no issues.",
        f"- **{counts.get('agent_wrong', 0)} traces** show the agent producing wrong outputs. "
        "These are deployment risks that should be caught before reaching users.",
        f"- **{counts.get('bad_input', 0)} traces** failed because of bad input data, "
        "not bad agent behavior. Fix the data pipeline, not the model.",
        f"- **{counts.get('needs_review', 0)} traces** could not be classified automatically "
        "and need human expert review.",
        "",
        "### For Training",
        f"- **{counts.get('safe', 0)} traces** are SFT-positive — safe to use as training examples.",
        f"- **{counts.get('agent_wrong', 0)} traces** are DPO-negative — the agent was wrong. "
        "Use as rejected examples in preference training (DPO/RLHF).",
        f"- **{counts.get('bad_input', 0)} traces** should be excluded from training entirely. "
        "Training on bad-input traces teaches the model to handle garbage, not to be accurate.",
        f"- **{counts.get('needs_review', 0)} traces** should not be used for training "
        "until a human expert classifies them.",
        "",
        "---",
        "",
        "*Generated by Detrix — governance infrastructure for AI agents.*  ",
        "*Want domain-specific gates for your workflow? Contact us.*",
        "",
    ])

    return "\n".join(lines)


def run_triage(
    traces_path: Path,
    output_path: Path | None = None,
    gates: list[GovernanceGate] | None = None,
    config: dict[str, Any] | None = None,
    title: str = "Detrix Trace Triage Report",
) -> str:
    traces = load_traces_jsonl(traces_path)
    gates = gates or default_gates()
    scored = score_traces(traces, gates, config)
    report = generate_report(scored, gates, title)

    if output_path:
        output_path.write_text(report)

    return report
