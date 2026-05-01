"""Tests for the Trace Triage Report generator."""

from __future__ import annotations

import json
from pathlib import Path

from detrix.triage.gates import CostAnomalyGate, LatencyAnomalyGate, OutputFormatGate
from detrix.triage.report import Trace, generate_report, load_traces_jsonl, score_traces
from detrix.core.governance import Decision, GateContext


def _sample_traces() -> list[dict]:
    return [
        {
            "trace_id": "safe_001",
            "inputs": {"prompt": "Analyze the XRD pattern for NaCl"},
            "outputs": {"completion": "NaCl identified with cubic structure. [kb:nacl-reference]"},
            "metadata": {"confidence": 0.95},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:00:00Z",
        },
        {
            "trace_id": "safe_002",
            "inputs": {"prompt": "Identify phases in sample"},
            "outputs": {"completion": "BaTiO3 tetragonal phase confirmed. [source:icdd-01-075-0461]"},
            "metadata": {"confidence": 0.88},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:01:00Z",
        },
        {
            "trace_id": "low_conf_003",
            "inputs": {"prompt": "Analyze mixed-phase sample"},
            "outputs": {"completion": "Possibly ZnO wurtzite but uncertain. [kb:zno-patterns]"},
            "metadata": {"confidence": 0.42},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:02:00Z",
        },
        {
            "trace_id": "pii_leak_004",
            "inputs": {"prompt": "Draft response to customer"},
            "outputs": {"completion": "Send results to jane.doe@example.com and call 555-123-4567"},
            "metadata": {"confidence": 0.91},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:03:00Z",
        },
        {
            "trace_id": "empty_005",
            "inputs": {"prompt": "Process batch"},
            "outputs": {"completion": ""},
            "metadata": {"confidence": 0.80},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:04:00Z",
        },
        {
            "trace_id": "no_conf_006",
            "inputs": {"prompt": "Identify unknown pattern"},
            "outputs": {"completion": "Cannot determine phase. Insufficient data."},
            "metadata": {},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:05:00Z",
        },
        {
            "trace_id": "high_latency_007",
            "inputs": {"prompt": "Run refinement"},
            "outputs": {"completion": "Refinement complete. R_wp = 4.2%"},
            "metadata": {"confidence": 0.92, "duration_ms": 45000},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:06:00Z",
        },
        {
            "trace_id": "high_cost_008",
            "inputs": {"prompt": "Enumerate all candidate phases"},
            "outputs": {"completion": "Found 47 candidate phases after exhaustive search."},
            "metadata": {"confidence": 0.85, "total_tokens": 120000},
            "tool_calls": [],
            "timestamp": "2026-05-01T00:07:00Z",
        },
    ]


def _write_traces_jsonl(path: Path, traces: list[dict]) -> None:
    with path.open("w") as f:
        for t in traces:
            f.write(json.dumps(t) + "\n")


def test_load_traces_jsonl(tmp_path: Path) -> None:
    traces_file = tmp_path / "traces.jsonl"
    _write_traces_jsonl(traces_file, _sample_traces())
    traces = load_traces_jsonl(traces_file)
    assert len(traces) == 8
    assert traces[0].trace_id == "safe_001"
    assert traces[3].trace_id == "pii_leak_004"


def test_score_traces_classifications(tmp_path: Path) -> None:
    traces_file = tmp_path / "traces.jsonl"
    _write_traces_jsonl(traces_file, _sample_traces())
    traces = load_traces_jsonl(traces_file)
    scored = score_traces(traces)

    by_id = {s.trace.trace_id: s for s in scored}

    assert by_id["safe_001"].classification == "safe"
    assert by_id["safe_002"].classification == "safe"
    assert by_id["low_conf_003"].classification == "agent_wrong"
    assert by_id["low_conf_003"].rejection_type == "output_quality"
    assert by_id["pii_leak_004"].classification == "agent_wrong"
    assert by_id["pii_leak_004"].rejection_type == "output_quality"
    assert by_id["empty_005"].classification == "agent_wrong"
    assert by_id["no_conf_006"].classification == "needs_review"


def test_generate_report_has_sections(tmp_path: Path) -> None:
    traces_file = tmp_path / "traces.jsonl"
    _write_traces_jsonl(traces_file, _sample_traces())
    traces = load_traces_jsonl(traces_file)
    scored = score_traces(traces)
    report = generate_report(scored)

    assert "# Detrix Trace Triage Report" in report
    assert "## Summary" in report
    assert "## Top Failure Patterns" in report
    assert "## Per-Trace Details" in report
    assert "## What This Means" in report
    assert "### For Deployment" in report
    assert "### For Training" in report
    assert "SFT-positive" in report
    assert "DPO-negative" in report
    assert "safe_001" in report
    assert "pii_leak_004" in report


def test_generate_report_writes_to_file(tmp_path: Path) -> None:
    traces_file = tmp_path / "traces.jsonl"
    _write_traces_jsonl(traces_file, _sample_traces())

    from detrix.triage.report import run_triage

    output = tmp_path / "report.md"
    report = run_triage(traces_file, output)

    assert output.exists()
    content = output.read_text()
    assert content == report
    assert "Traces scored: 8" in content


def test_output_format_gate_empty_output() -> None:
    gate = OutputFormatGate()
    ctx = GateContext(run_id="test", step_index=0, prior_verdicts=[], config={})
    result = gate.evaluate({"completion": ""}, ctx)
    assert result.decision == Decision.REJECT
    assert "empty_output" in result.reason_codes


def test_output_format_gate_missing_keys() -> None:
    gate = OutputFormatGate(required_keys={"phase", "confidence"})
    ctx = GateContext(run_id="test", step_index=0, prior_verdicts=[], config={})
    result = gate.evaluate({"completion": '{"phase": "NaCl"}'}, ctx)
    assert result.decision == Decision.REJECT
    assert "missing_required_keys" in result.reason_codes


def test_output_format_gate_valid() -> None:
    gate = OutputFormatGate()
    ctx = GateContext(run_id="test", step_index=0, prior_verdicts=[], config={})
    result = gate.evaluate({"completion": "NaCl identified"}, ctx)
    assert result.decision == Decision.ACCEPT


def test_latency_anomaly_gate() -> None:
    gate = LatencyAnomalyGate(max_latency_ms=10000)
    ctx = GateContext(run_id="test", step_index=0, prior_verdicts=[], config={})

    result = gate.evaluate({"duration_ms": 5000}, ctx)
    assert result.decision == Decision.ACCEPT

    result = gate.evaluate({"duration_ms": 15000}, ctx)
    assert result.decision == Decision.CAUTION
    assert "latency_anomaly" in result.reason_codes


def test_cost_anomaly_gate() -> None:
    gate = CostAnomalyGate(max_tokens=50000)
    ctx = GateContext(run_id="test", step_index=0, prior_verdicts=[], config={})

    result = gate.evaluate({"total_tokens": 10000}, ctx)
    assert result.decision == Decision.ACCEPT

    result = gate.evaluate({"total_tokens": 80000}, ctx)
    assert result.decision == Decision.CAUTION
    assert "token_usage_anomaly" in result.reason_codes
