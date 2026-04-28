# AgentXRD Failure Governance Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Detrix closed-loop AgentXRD failure-governance harness that first mines as many high-level and low-level failure patterns as possible from Mission Control Langfuse traces plus AgentXRD diagnostic artifacts, then emits governed next actions, provenance DAGs, fail-closed promotion packets, and drift replay reports.

**Architecture:** Treat Mission Control Langfuse data as advisory trace evidence and AgentXRD binary20/router artifacts as deterministic seed evidence. Detrix normalizes both into a stable failure-pattern corpus, preserves deterministic PXRD gates as the export authority, and only then derives governed actions, lineage, promotion decisions, and replay deltas. Live Langfuse import is default-off and never mutates `support_only`, `accept_eligible`, truth status, terminal route, or export eligibility.

**Tech Stack:** Python 3.12, Pydantic, SQLite, pytest, Click CLI, existing Detrix `AXV2` adapter, Mission Control SQLite/Langfuse API contracts, AgentXRD diagnostic JSON/JSONL artifacts, `bd` beads for implementation tracking.

---

## Current Evidence Baseline

Implemented surfaces already present in Detrix:

- `src/detrix/adapters/axv2.py`: converts AXV2 run artifacts into `GovernedTrajectory` rows and audit gates.
- `src/detrix/runtime/langfuse_observer.py`: optional Langfuse observer for Detrix workflow runs.
- `scripts/demo_agentxrd_langfuse_judge_bridge.py`: local Langfuse-style score replay with deterministic gate reconciliation.
- `scripts/demo_binary20_governed_judge_cohort.py`: local binary20 judge cohort replay.
- `src/detrix/core/trajectory.py`, `src/detrix/runtime/trajectory_store.py`, `src/detrix/improvement/exporter.py`: governed trajectory persistence and SFT/DPO/GRPO export.
- `src/detrix/runtime/provenance.py` and `src/detrix/improvement/trace_collector.py`: stubs only.
- `src/detrix/improvement/promoter.py`: generic metric compare only, not AgentXRD promotion packet.

Canonical seed artifacts:

- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/row_packets.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/langfuse_trace_fixture.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/langfuse_judge_scores.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/trace_to_pxrd_packet_map.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/router_decisions.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/ranked_next_actions.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/summary.json`

Mission Control reference surfaces:

- `/home/gabriel/mission-control/AGENTS.md:95-105`: Langfuse instances and API auth pattern.
- `/home/gabriel/mission-control/my-app/app/api/langfuse/traces/route.ts`: live/cache trace endpoint behavior.
- `/home/gabriel/mission-control/my-app/lib/db.ts`: `langfuse_instances`, `langfuse_traces`, `langfuse_backfill_state`, and `coding_sessions` tables.
- `/home/gabriel/mission-control/my-app/lib/collectors/langfuse-collector.ts`: live collector that fetches traces and observations.
- `/home/gabriel/mission-control/my-app/lib/daily-audit/trace-resolver.ts`: trace candidate resolver and fallback behavior.
- `/home/gabriel/.mission-control/data.db`: actual populated Mission Control SQLite DB. Do not default to `/home/gabriel/mission-control/my-app/mc.db`; that file may exist but is empty. Current AgentXRD cache rows are under project `AgentXRD_v2`; treat `mc-agentxrd_v2` as an alias/future live project key, not the only cache filter.

## File Structure

Create focused modules rather than expanding demo scripts:

- Create: `src/detrix/agentxrd/__init__.py`
  - Package marker for AgentXRD-specific governance helpers.
- Create: `src/detrix/agentxrd/failure_patterns.py`
  - Pydantic schemas and normalizer for high-level/low-level failure pattern rows.
- Create: `src/detrix/agentxrd/langfuse_importer.py`
  - Default-off Mission Control/Langfuse trace importer with live API and SQLite cache readers.
- Create: `src/detrix/agentxrd/next_actions.py`
  - Converts blocker classes and observed patterns into bounded governed next actions.
- Create: `src/detrix/agentxrd/provenance.py`
  - Builds AgentXRD provenance DAG rows from trace-to-packet maps, terminal routes, scores, and candidate evidence.
- Create: `src/detrix/agentxrd/promotion_packet.py`
  - AgentXRD fail-closed promotion packet schema and evaluator.
- Create: `src/detrix/agentxrd/drift_replay.py`
  - Replays binary20/router fixtures and compares before/after gate or judge policy deltas.
- Modify: `src/detrix/cli/main.py`
  - Add `agentxrd` command group and subcommands.
- Modify: `scripts/demo_binary20_governed_judge_cohort.py`
  - Reuse new AgentXRD modules while preserving current outputs.
- Test: `tests/test_agentxrd_failure_patterns.py`
- Test: `tests/test_agentxrd_langfuse_importer.py`
- Test: `tests/test_agentxrd_next_actions.py`
- Test: `tests/test_agentxrd_provenance.py`
- Test: `tests/test_agentxrd_promotion_packet.py`
- Test: `tests/test_agentxrd_drift_replay.py`

## Artifact Contracts

The implementation must emit these files for the binary20/router seed corpus:

- `failure_patterns.jsonl`
- `failure_pattern_summary.json`
- `raw_langfuse_traces.jsonl`
- `normalized_observations.jsonl`
- `trace_to_agentxrd_packet_map.jsonl`
- `governed_next_actions.jsonl`
- `provenance_dag.jsonl`
- `promotion_packet.json`
- `drift_replay_report.json`

## Spark Subagent Pattern Ingestion Protocol

Before implementing Task 1, dispatch Spark/explore subagents in parallel. They are read-only and write no code:

1. **Mission Control Langfuse miner**
   - CWD: `/home/gabriel/mission-control`
   - Read: `/home/gabriel/.mission-control/data.db`, `my-app/app/api/langfuse/traces/route.ts`, `my-app/lib/collectors/langfuse-collector.ts`, `my-app/lib/daily-audit/trace-resolver.ts`.
   - Output required: high-level trace failure families by `project`, `status`, `model`, `metadata.failure_mode`, `metadata.error`, plus low-level observation/span fields available through live observations.

2. **AgentXRD packet miner**
   - CWD: `/home/gabriel/Desktop/AgentXRD_v2`
   - Read: `binary20_governed_judge_cohort_v0`, `pxrd_failure_router_v0`, and `agentxrd_langfuse_judge_bridge_v0` artifacts.
   - Output required: high-level blocker classes, low-level packet fields, candidate/CIF/source evidence fields, and trace-to-packet join keys.

3. **Detrix implementation mapper**
   - CWD: `/home/gabriel/Desktop/detrix-core`
   - Read: AXV2 adapter, Langfuse observer, trajectory/export/promoter/provenance modules, and demo scripts.
   - Output required: what is implemented, what is stubbed, exact modules to modify, and tests to extend.

Task 1 must incorporate all three reports. If the reports disagree, prefer deterministic AgentXRD artifacts over live/cache Langfuse fields and record the disagreement in `failure_pattern_summary.json`.

The implementation must preserve these fail-closed rules:

- Live Langfuse evidence is advisory only.
- Qwen judge output is advisory only.
- Deterministic PXRD eligibility controls SFT/DPO/export labels.
- Missing required safety metrics fail promotion closed.
- `support_only=true`, `accept_eligible=false`, truth-blocked, provisional, or `must_not_promote=true` rows cannot become SFT positives.

## Beads Plan

Created implementation beads:

- `detrix-core-4g4`: Epic: AgentXRD failure-governance harness
- `detrix-core-59s`: Mine AgentXRD failure patterns from Langfuse and diagnostic artifacts
- `detrix-core-dbm`: Emit governed next actions for AgentXRD blockers
- `detrix-core-ten`: Build AgentXRD provenance DAG export
- `detrix-core-dj4`: Add AgentXRD fail-closed promotion packets
- `detrix-core-0jj`: Add AgentXRD threshold and judge drift replay
- `detrix-core-0xz`: Wire AgentXRD harness CLI and demo scripts

If recreating the tracker from scratch, create one parent epic and six implementation beads:

```bash
bd create "Epic: AgentXRD failure-governance harness" \
  --description="Closed-loop Detrix harness for AgentXRD trace-pattern mining, governed next actions, provenance DAG, fail-closed promotion packets, and drift replay. Start with Mission Control Langfuse traces plus binary20/router seed artifacts; preserve deterministic PXRD gates as authority." \
  -t epic -p 1 --json
```

Use the returned epic ID as `<EPIC_ID>` for the dependency commands below.

```bash
bd create "Mine AgentXRD failure patterns from Langfuse and diagnostic artifacts" \
  --description="Build AgentXRD failure-pattern schemas, Mission Control Langfuse/cache importer, and seed-artifact normalizer. Emit raw_langfuse_traces.jsonl, normalized_observations.jsonl, trace_to_agentxrd_packet_map.jsonl, failure_patterns.jsonl, and failure_pattern_summary.json. Live import default-off and advisory only." \
  -t feature -p 1 --deps discovered-from:<EPIC_ID> --json

bd create "Emit governed next actions for AgentXRD blockers" \
  --description="Convert blocker classes and mined failure patterns into bounded GovernedNextAction rows with source artifacts, allowed commands, kill criteria, expected evidence delta, and training/export block status." \
  -t feature -p 1 --deps discovered-from:<EPIC_ID> --json

bd create "Build AgentXRD provenance DAG export" \
  --description="Construct provenance_dag.jsonl linking samples, traces, packets, candidates, CIF/source provenance, truth grade, support-only status, accept eligibility, refinement evidence, judge scores, and export routes." \
  -t feature -p 1 --deps discovered-from:<EPIC_ID> --json

bd create "Add AgentXRD fail-closed promotion packets" \
  --description="Implement promotion_packet.json with required wrong_accept/support_only/accept_ineligible/truth-blocked safety metrics and fail-closed behavior when metrics are missing." \
  -t feature -p 1 --deps discovered-from:<EPIC_ID> --json

bd create "Add AgentXRD threshold and judge drift replay" \
  --description="Replay binary20 governed cohort and pxrd_failure_router corpus after gate, threshold, judge, or metric-policy changes. Emit before/after deltas and block unsafe promotion." \
  -t feature -p 1 --deps discovered-from:<EPIC_ID> --json

bd create "Wire AgentXRD harness CLI and demo scripts" \
  --description="Add detrix agentxrd commands and refactor existing demo scripts to call AgentXRD harness modules while preserving current local replay outputs." \
  -t task -p 2 --deps discovered-from:<EPIC_ID> --json
```

## Task 1: Failure Pattern Corpus First

**Files:**
- Create: `src/detrix/agentxrd/__init__.py`
- Create: `src/detrix/agentxrd/failure_patterns.py`
- Create: `src/detrix/agentxrd/langfuse_importer.py`
- Test: `tests/test_agentxrd_failure_patterns.py`
- Test: `tests/test_agentxrd_langfuse_importer.py`

- [ ] **Step 1: Write failing tests for high-level and low-level failure extraction**

Add to `tests/test_agentxrd_failure_patterns.py`:

```python
import json
from pathlib import Path

from detrix.agentxrd.failure_patterns import (
    FailurePatternSummary,
    build_failure_pattern_corpus,
)


FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"
ROUTER = FIXTURE_ROOT / "pxrd_failure_router_v0"


def test_build_failure_pattern_corpus_preserves_high_and_low_level_patterns(tmp_path):
    output_dir = tmp_path / "patterns"

    summary = build_failure_pattern_corpus(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        row_packets=BINARY20 / "row_packets.jsonl",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        router_decisions=ROUTER / "router_decisions.jsonl",
        router_summary=ROUTER / "summary.json",
        normalized_observations=None,
        output_dir=output_dir,
    )

    assert isinstance(summary, FailurePatternSummary)
    assert summary.row_count == 20
    assert summary.high_level_counts["SUPPORT_ONLY_BLOCKED"] >= 1
    assert summary.high_level_counts["TRUTH_CONFLICT"] >= 1
    assert summary.low_level_counts
    assert summary.judge_gate_conflict_count == 8
    assert summary.sft_positive_count == 0
    assert summary.langfuse_observation_count == 0

    rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 20
    assert all(row["sample_id"] for row in rows)
    assert all(row["deterministic_export_label"] != "sft_positive" for row in rows)
    assert (output_dir / "failure_pattern_summary.json").exists()


def test_build_failure_pattern_corpus_merges_langfuse_observation_hints(tmp_path):
    output_dir = tmp_path / "patterns"
    observations = tmp_path / "normalized_observations.jsonl"
    observations.write_text(
        json.dumps(
            {
                "trace_id": "trace-live-1",
                "sample_id": "dara_2Fe3O4-3Y2O3_1000C_60min",
                "status": "ERROR",
                "failure_hint": "context-window",
                "advisory_only": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_failure_pattern_corpus(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        row_packets=BINARY20 / "row_packets.jsonl",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        router_decisions=ROUTER / "router_decisions.jsonl",
        router_summary=ROUTER / "summary.json",
        normalized_observations=observations,
        output_dir=output_dir,
    )

    assert summary.langfuse_observation_count == 1
    assert summary.langfuse_failure_hint_counts["context-window"] == 1
    rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl").read_text().splitlines()
    ]
    assert any(row["low_level_bucket"] == "context-window" for row in rows)


def test_build_failure_pattern_corpus_keeps_unjoinable_langfuse_patterns(tmp_path):
    output_dir = tmp_path / "patterns"
    observations = tmp_path / "normalized_observations.jsonl"
    observations.write_text(
        json.dumps(
            {
                "trace_id": "trace-cache-1",
                "project": "AgentXRD_v2",
                "name": "AgentXRD_v2 session",
                "status": None,
                "failure_hint": "cache_summary_trace",
                "sample_id": None,
                "join_status": "unjoinable_cache_summary",
                "advisory_only": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_failure_pattern_corpus(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        row_packets=BINARY20 / "row_packets.jsonl",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        router_decisions=ROUTER / "router_decisions.jsonl",
        router_summary=ROUTER / "summary.json",
        normalized_observations=observations,
        output_dir=output_dir,
    )

    assert summary.langfuse_observation_count == 1
    assert summary.unjoinable_langfuse_trace_count == 1
    assert summary.unjoinable_langfuse_trace_patterns["cache_summary_trace"] == 1
    rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 21
    assert any(
        row["sample_id"] == "unjoinable:trace-cache-1"
        and row["high_level_bucket"] == "LANGFUSE_TRACE_UNJOINABLE"
        and row["deterministic_export_label"] == "eval_only"
        for row in rows
    )
```

- [ ] **Step 2: Write failing tests for default-off Langfuse/Mission Control import**

Add to `tests/test_agentxrd_langfuse_importer.py`:

```python
import json
import sqlite3
from pathlib import Path

from detrix.agentxrd.langfuse_importer import (
    MissionControlLangfuseSource,
    import_agentxrd_langfuse_traces,
)


def test_importer_reads_mission_control_cache_without_live_calls(tmp_path):
    db_path = tmp_path / "mc.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE langfuse_traces (
                id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL,
                name TEXT,
                project TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_cost REAL,
                latency_ms INTEGER,
                status TEXT,
                started_at TEXT,
                metadata TEXT,
                ingested_at TEXT
            )"""
        )
        conn.execute(
            """INSERT INTO langfuse_traces
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "trace-1",
                "langfuse-general",
                "AgentXRD_v2 session",
                "AgentXRD_v2",
                "qwen-test",
                10,
                5,
                0.0,
                123,
                None,
                "2026-04-28T00:00:00Z",
                json.dumps(
                    {
                        "cwd": "/home/gabriel/Desktop/AgentXRD_v2",
                        "source": "codex",
                        "model": "gpt-5.4",
                    }
                ),
                "2026-04-28T00:00:01Z",
            ),
        )

    source = MissionControlLangfuseSource(db_path=db_path, live_enabled=False)
    report = import_agentxrd_langfuse_traces(
        source=source,
        project="AgentXRD_v2",
        output_dir=tmp_path / "out",
        limit=50,
    )

    assert report.live_enabled is False
    assert report.raw_trace_count == 1
    assert report.normalized_observation_count == 1
    assert report.project_aliases == ["AgentXRD_v2", "mc-agentxrd_v2"]
    assert report.unjoinable_trace_count == 1
    assert report.advisory_only is True
    assert (tmp_path / "out" / "raw_langfuse_traces.jsonl").exists()
    observations = [
        json.loads(line)
        for line in (tmp_path / "out" / "normalized_observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert observations[0]["join_status"] == "unjoinable_cache_summary"
    assert observations[0]["sample_id"] is None
    assert observations[0]["failure_hint"] == "AgentXRD_v2 session"
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_agentxrd_failure_patterns.py tests/test_agentxrd_langfuse_importer.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'detrix.agentxrd'`.

- [ ] **Step 4: Implement schemas and corpus builder**

Create `src/detrix/agentxrd/__init__.py`:

```python
"""AgentXRD-specific Detrix governance helpers."""
```

Create `src/detrix/agentxrd/failure_patterns.py` with these public models and functions:

```python
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class FailurePatternRow(BaseModel):
    schema_version: str = "agentxrd_failure_patterns_v0.1"
    sample_id: str
    trace_id: str | None = None
    observation_id: str | None = None
    high_level_bucket: str
    low_level_bucket: str
    blocker_class: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    blocking_fields: list[str] = Field(default_factory=list)
    next_allowed_action: str | None = None
    terminal_verdict: str | None = None
    support_only: bool | None = None
    accept_eligible: bool | None = None
    truth_flags: dict[str, Any] = Field(default_factory=dict)
    wrong_accept_risk: bool | None = None
    judge_recommendation: str | None = None
    judge_gate_classification: str | None = None
    deterministic_export_label: str
    source_artifacts: list[str] = Field(default_factory=list)


class FailurePatternSummary(BaseModel):
    schema_version: str = "agentxrd_failure_patterns_v0.1"
    row_count: int
    high_level_counts: dict[str, int]
    low_level_counts: dict[str, int]
    blocker_counts: dict[str, int]
    judge_gate_conflict_count: int
    judge_over_promote_count: int
    sft_positive_count: int
    langfuse_observation_count: int
    langfuse_failure_hint_counts: dict[str, int] = Field(default_factory=dict)
    unjoinable_langfuse_trace_count: int = 0
    unjoinable_langfuse_trace_patterns: dict[str, int] = Field(default_factory=dict)
    trace_cache_miss_reason: str | None = None
    advisory_sources: list[str]
    deterministic_gates_authoritative: bool


def build_failure_pattern_corpus(
    *,
    binary20_artifact: Path,
    row_packets: Path,
    trace_packet_map: Path,
    router_decisions: Path,
    router_summary: Path,
    normalized_observations: Path | None,
    output_dir: Path,
) -> FailurePatternSummary:
    artifact = _load_json(binary20_artifact)
    packets = _load_jsonl(row_packets)
    trace_map = {row["sample_id"]: row for row in _load_jsonl(trace_packet_map)}
    router_rows = {row["sample_id"]: row for row in _load_jsonl(router_decisions)}
    router = _load_json(router_summary)
    observations = _load_jsonl(normalized_observations) if normalized_observations else []
    observations_by_sample = _observations_by_sample(observations)
    reconciliation = {
        row["sample_id"]: row
        for row in artifact["deterministic_gate_reconciliation"]["rows"]
    }
    scores = {row["sample_id"]: row for row in artifact["langfuse_score_evidence"]}
    terminals = artifact["terminal_routes"]

    rows: list[FailurePatternRow] = []
    for packet in packets:
        sample_id = str(packet["sample_id"])
        terminal = terminals.get(sample_id, {})
        router_row = router_rows.get(sample_id, {})
        recon = reconciliation.get(sample_id, {})
        score = scores.get(sample_id, {})
        mapped = trace_map.get(sample_id, {})
        observation = observations_by_sample.get(sample_id, {})

        high_level = str(
            router_row.get("blocker_class")
            or recon.get("classification")
            or _fallback_bucket(terminal)
        )
        low_level = _low_level_bucket(packet, router_row, terminal, recon)

        rows.append(
            FailurePatternRow(
                sample_id=sample_id,
                trace_id=score.get("trace_id") or mapped.get("trace_id"),
                observation_id=score.get("observation_id") or mapped.get("observation_id"),
                high_level_bucket=high_level,
                low_level_bucket=low_level,
                blocker_class=router_row.get("blocker_class"),
                reason_codes=list(packet.get("reason_codes", [])),
                blocking_fields=list(router_row.get("blocking_fields", [])),
                next_allowed_action=router_row.get("next_allowed_action"),
                terminal_verdict=terminal.get("verdict"),
                support_only=terminal.get("support_only"),
                accept_eligible=terminal.get("accept_eligible"),
                truth_flags=terminal.get("truth_flags", {}),
                wrong_accept_risk=router_row.get("wrong_accept_risk"),
                judge_recommendation=score.get("judge_recommendation"),
                judge_gate_classification=recon.get("classification"),
                deterministic_export_label=str(
                    recon.get("final_training_export_label", "eval_only")
                ),
                source_artifacts=[
                    str(binary20_artifact),
                    str(row_packets),
                    str(trace_packet_map),
                    str(router_decisions),
                    str(router_summary),
                ],
            )
        )
        if observation:
            rows[-1].low_level_bucket = str(
                observation.get("failure_hint")
                or observation.get("status")
                or rows[-1].low_level_bucket
            )

    unjoinable_observations = [
        obs
        for obs in observations
        if not obs.get("sample_id")
        or str(obs.get("join_status", "")).startswith("unjoinable")
    ]
    for observation in unjoinable_observations:
        trace_id = str(observation.get("trace_id") or "unknown-trace")
        failure_hint = str(
            observation.get("failure_hint")
            or observation.get("status")
            or observation.get("name")
            or "unclassified_trace"
        )
        rows.append(
            FailurePatternRow(
                sample_id=f"unjoinable:{trace_id}",
                trace_id=trace_id,
                high_level_bucket="LANGFUSE_TRACE_UNJOINABLE",
                low_level_bucket=failure_hint,
                reason_codes=["unjoinable_langfuse_cache_summary"],
                deterministic_export_label="eval_only",
                source_artifacts=[str(normalized_observations)]
                if normalized_observations
                else [],
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "failure_patterns.jsonl", [row.model_dump() for row in rows])

    high_counts = Counter(row.high_level_bucket for row in rows)
    low_counts = Counter(row.low_level_bucket for row in rows)
    failure_hint_counts = Counter(
        str(obs.get("failure_hint") or obs.get("status") or "unknown")
        for obs in observations
    )
    unjoinable_counts = Counter(row.low_level_bucket for row in rows if row.high_level_bucket == "LANGFUSE_TRACE_UNJOINABLE")
    summary = FailurePatternSummary(
        row_count=len(rows),
        high_level_counts=dict(high_counts),
        low_level_counts=dict(low_counts),
        blocker_counts=dict(router.get("blocker_counts", {})),
        judge_gate_conflict_count=int(
            artifact["deterministic_gate_reconciliation"]["judge_gate_conflict_count"]
        ),
        judge_over_promote_count=int(
            artifact["deterministic_gate_reconciliation"]["judge_over_promote_count"]
        ),
        sft_positive_count=sum(
            1 for row in rows if row.deterministic_export_label == "sft_positive"
        ),
        langfuse_observation_count=len(observations),
        langfuse_failure_hint_counts=dict(failure_hint_counts),
        unjoinable_langfuse_trace_count=sum(unjoinable_counts.values()),
        unjoinable_langfuse_trace_patterns=dict(unjoinable_counts),
        trace_cache_miss_reason=None
        if observations
        else "no Mission Control Langfuse cache rows matched the selected AgentXRD project aliases",
        advisory_sources=["langfuse_trace_fixture", "langfuse_score_evidence"],
        deterministic_gates_authoritative=True,
    )
    _write_json(output_dir / "failure_pattern_summary.json", summary.model_dump())
    return summary


def _fallback_bucket(terminal: dict[str, Any]) -> str:
    if terminal.get("support_only") is True:
        return "SUPPORT_ONLY_BLOCKED"
    if terminal.get("accept_eligible") is False:
        return "ACCEPT_INELIGIBLE_BLOCKED"
    flags = terminal.get("truth_flags", {})
    if isinstance(flags, dict) and (flags.get("truth_blocked") or flags.get("provisional")):
        return "TRUTH_CONFLICT"
    return "UNCLASSIFIED"


def _low_level_bucket(
    packet: dict[str, Any],
    router_row: dict[str, Any],
    terminal: dict[str, Any],
    recon: dict[str, Any],
) -> str:
    for field in ("reason_codes", "deterministic_blockers"):
        values = packet.get(field)
        if isinstance(values, list) and values:
            return str(values[0])
    fields = router_row.get("blocking_fields")
    if isinstance(fields, list) and fields:
        return str(fields[0])
    reasons = recon.get("block_reasons")
    if isinstance(reasons, list) and reasons:
        return str(reasons[0])
    return str(terminal.get("verdict", "UNKNOWN"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _observations_by_sample(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        sample_id = row.get("sample_id")
        if sample_id and sample_id not in result:
            result[str(sample_id)] = row
    return result


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
```

- [ ] **Step 5: Implement Mission Control Langfuse/cache importer**

Create `src/detrix/agentxrd/langfuse_importer.py`:

```python
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class MissionControlLangfuseSource(BaseModel):
    db_path: Path = Path("/home/gabriel/.mission-control/data.db")
    base_url: str = "http://localhost:3100"
    live_enabled: bool = False


class LangfuseImportReport(BaseModel):
    raw_trace_count: int
    normalized_observation_count: int
    project: str
    project_aliases: list[str]
    unjoinable_trace_count: int
    live_enabled: bool
    advisory_only: bool = True


def import_agentxrd_langfuse_traces(
    *,
    source: MissionControlLangfuseSource,
    project: str,
    output_dir: Path,
    limit: int = 1000,
) -> LangfuseImportReport:
    traces = _read_cached_traces(source.db_path, _project_aliases(project), limit)
    observations = [_normalize_trace(row) for row in traces]
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "raw_langfuse_traces.jsonl", traces)
    _write_jsonl(output_dir / "normalized_observations.jsonl", observations)
    return LangfuseImportReport(
        raw_trace_count=len(traces),
        normalized_observation_count=len(observations),
        project=project,
        project_aliases=_project_aliases(project),
        unjoinable_trace_count=sum(
            1
            for obs in observations
            if str(obs.get("join_status", "")).startswith("unjoinable")
        ),
        live_enabled=source.live_enabled,
    )


def _project_aliases(project: str) -> list[str]:
    aliases = [project]
    if project == "mc-agentxrd_v2":
        aliases.append("AgentXRD_v2")
    if project == "AgentXRD_v2":
        aliases.append("mc-agentxrd_v2")
    return aliases


def _read_cached_traces(db_path: Path, projects: list[str], limit: int) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in projects)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT id, instance_id, name, project, model, input_tokens, output_tokens,
                      total_cost, latency_ms, status, started_at, metadata, ingested_at
               FROM langfuse_traces
               WHERE project IN ({placeholders})
               ORDER BY datetime(COALESCE(started_at, ingested_at)) DESC
               LIMIT ?""",
            (*projects, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def _normalize_trace(row: dict[str, Any]) -> dict[str, Any]:
    metadata = {}
    if row.get("metadata"):
        try:
            metadata = json.loads(str(row["metadata"]))
        except json.JSONDecodeError:
            metadata = {"raw_metadata": row["metadata"]}
    sample_id = metadata.get("sample_id") or metadata.get("agentxrd_sample_id")
    failure_hint = (
        metadata.get("error")
        or metadata.get("failure_mode")
        or row.get("status")
        or row.get("name")
        or "cache_summary_trace"
    )
    return {
        "schema_version": "agentxrd_langfuse_observation_v0.1",
        "trace_id": row["id"],
        "project": row.get("project"),
        "name": row.get("name"),
        "model": row.get("model"),
        "status": row.get("status"),
        "latency_ms": row.get("latency_ms"),
        "input_tokens": row.get("input_tokens") or 0,
        "output_tokens": row.get("output_tokens") or 0,
        "sample_id": sample_id,
        "join_status": "joined" if sample_id else "unjoinable_cache_summary",
        "failure_hint": failure_hint,
        "metadata": metadata,
        "advisory_only": True,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_agentxrd_failure_patterns.py tests/test_agentxrd_langfuse_importer.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/detrix/agentxrd tests/test_agentxrd_failure_patterns.py tests/test_agentxrd_langfuse_importer.py
git commit -m "feat: mine AgentXRD failure patterns"
```

## Task 2: Governed Next Action Ledger

**Files:**
- Create: `src/detrix/agentxrd/next_actions.py`
- Test: `tests/test_agentxrd_next_actions.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_agentxrd_next_actions.py`:

```python
import json
from pathlib import Path

from detrix.agentxrd.next_actions import build_governed_next_actions


def test_next_actions_are_bounded_and_keep_training_blocked(tmp_path):
    patterns = tmp_path / "failure_patterns.jsonl"
    patterns.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": "row-truth",
                        "high_level_bucket": "TRUTH_CONFLICT",
                        "low_level_bucket": "truth_flags",
                        "blocker_class": "TRUTH_CONFLICT",
                        "deterministic_export_label": "eval_only",
                        "source_artifacts": ["artifact.json"],
                    }
                ),
                json.dumps(
                    {
                        "sample_id": "row-prov",
                        "high_level_bucket": "PROVENANCE_GAP",
                        "low_level_bucket": "candidate_cif_provenance",
                        "blocker_class": "PROVENANCE_GAP",
                        "deterministic_export_label": "eval_only",
                        "source_artifacts": ["artifact.json"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    actions = build_governed_next_actions(patterns, tmp_path / "governed_next_actions.jsonl")

    assert [action.action_type for action in actions] == ["truth_audit", "provenance_join"]
    assert all(action.training_export_blocked for action in actions)
    assert all(action.allowed_commands for action in actions)
    assert all(action.kill_criteria for action in actions)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_agentxrd_next_actions.py -q
```

Expected: fail with missing module/function.

- [ ] **Step 3: Implement bounded action mapping**

Create `src/detrix/agentxrd/next_actions.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class GovernedNextAction(BaseModel):
    schema_version: str = "agentxrd_governed_next_action_v0.1"
    action_id: str
    sample_id: str
    blocker_class: str
    action_type: str
    source_artifacts: list[str] = Field(default_factory=list)
    allowed_commands: list[str]
    kill_criteria: list[str]
    expected_evidence_delta: str
    training_export_blocked: bool = True


ACTION_MAP = {
    "TRUTH_CONFLICT": (
        "truth_audit",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/audit_nb_truth_provenance.py"],
    ),
    "PROVENANCE_GAP": (
        "provenance_join",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/reaction_product_candidate_discovery_v0.py"],
    ),
    "AMBIGUOUS_MULTI_HYPOTHESIS": (
        "hypothesis_disambiguation",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/reaction_product_candidate_discovery_v0.py"],
    ),
    "REFINEMENT_STRATEGY": (
        "refinement_strategy_probe",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/probe_bimo_mp_candidate_refine.py"],
    ),
    "INSUFFICIENT_ARTIFACT_EVIDENCE": (
        "artifact_evidence_request",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/generate_v5_evidence_report.py"],
    ),
    "SUPPORT_ONLY_BLOCKED": (
        "calibration_only_review",
        ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/check_binary_support_manifest_public_cifs.py"],
    ),
}


def build_governed_next_actions(
    failure_patterns: Path,
    output_path: Path,
) -> list[GovernedNextAction]:
    rows = [
        json.loads(line)
        for line in failure_patterns.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    actions: list[GovernedNextAction] = []
    for row in rows:
        blocker = str(row.get("blocker_class") or row.get("high_level_bucket"))
        action_type, commands = ACTION_MAP.get(
            blocker,
            (
                "calibration_only_review",
                ["python /home/gabriel/Desktop/AgentXRD_v2/scripts/build_pxrd_failure_router_v0.py"],
            ),
        )
        actions.append(
            GovernedNextAction(
                action_id=f"{row['sample_id']}:{action_type}",
                sample_id=str(row["sample_id"]),
                blocker_class=blocker,
                action_type=action_type,
                source_artifacts=list(row.get("source_artifacts", [])),
                allowed_commands=commands,
                kill_criteria=[
                    "stop if support_only, accept_eligible, or truth status would be mutated",
                    "stop if required evidence artifact is absent",
                    "stop if proposed action would promote training/export eligibility directly",
                ],
                expected_evidence_delta=f"resolve or narrow {blocker} without changing deterministic gate authority",
            )
        )
    _write_jsonl(output_path, [action.model_dump() for action in actions])
    return actions


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_agentxrd_next_actions.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/detrix/agentxrd/next_actions.py tests/test_agentxrd_next_actions.py
git commit -m "feat: add AgentXRD governed next actions"
```

## Task 3: AgentXRD Provenance DAG

**Files:**
- Create: `src/detrix/agentxrd/provenance.py`
- Modify: `src/detrix/runtime/provenance.py`
- Test: `tests/test_agentxrd_provenance.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_agentxrd_provenance.py`:

```python
import json
from pathlib import Path

from detrix.agentxrd.provenance import build_agentxrd_provenance_dag


FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"


def test_provenance_dag_links_trace_packet_candidate_and_export_route(tmp_path):
    output = tmp_path / "provenance_dag.jsonl"

    graph = build_agentxrd_provenance_dag(
        detrix_artifact=BINARY20 / "detrix_run_artifact.json",
        trace_packet_map=BINARY20 / "trace_to_pxrd_packet_map.jsonl",
        row_packets=BINARY20 / "row_packets.jsonl",
        output_path=output,
    )

    assert graph.nodes
    assert graph.edges
    node_types = {node.node_type for node in graph.nodes}
    assert {
        "sample",
        "trace",
        "pxrd_packet",
        "candidate_cif",
        "source_cif",
        "refinement_evidence",
        "terminal_route",
        "training_route",
    } <= node_types

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert any(row["record_type"] == "node" for row in rows)
    assert any(row["record_type"] == "edge" for row in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_agentxrd_provenance.py -q
```

Expected: fail with missing module/function or missing node types.

- [ ] **Step 3: Extend provenance node type comments only if needed**

Modify `src/detrix/runtime/provenance.py` so comments allow AgentXRD-specific node types:

```python
class ProvenanceNode(BaseModel):
    """A node in the provenance DAG."""

    node_id: str
    node_type: str  # Examples: sample, trace, pxrd_packet, candidate, terminal_route
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Implement AgentXRD DAG builder**

Create `src/detrix/agentxrd/provenance.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from detrix.runtime.provenance import ProvenanceEdge, ProvenanceGraph, ProvenanceNode


def build_agentxrd_provenance_dag(
    *,
    detrix_artifact: Path,
    trace_packet_map: Path,
    row_packets: Path,
    output_path: Path,
) -> ProvenanceGraph:
    artifact = json.loads(detrix_artifact.read_text(encoding="utf-8"))
    maps = _load_jsonl(trace_packet_map)
    packets = {row["sample_id"]: row for row in _load_jsonl(row_packets)}
    terminals = artifact["terminal_routes"]
    scores = {row["sample_id"]: row for row in artifact["langfuse_score_evidence"]}
    recon = {
        row["sample_id"]: row
        for row in artifact["deterministic_gate_reconciliation"]["rows"]
    }

    nodes: dict[str, ProvenanceNode] = {}
    edges: list[ProvenanceEdge] = []

    for mapping in maps:
        sample_id = str(mapping["sample_id"])
        trace_id = str(mapping.get("trace_id") or f"trace:{sample_id}")
        packet = packets.get(sample_id, {})
        packet_id = f"packet:{sample_id}"
        route_id = f"terminal:{sample_id}"
        training_id = f"training:{sample_id}"

        nodes[f"sample:{sample_id}"] = ProvenanceNode(
            node_id=f"sample:{sample_id}",
            node_type="sample",
            metadata={"sample_id": sample_id},
        )
        nodes[trace_id] = ProvenanceNode(
            node_id=trace_id,
            node_type="trace",
            metadata={"observation_id": mapping.get("observation_id")},
        )
        nodes[packet_id] = ProvenanceNode(
            node_id=packet_id,
            node_type="pxrd_packet",
            metadata=packet,
        )
        refinement_id = f"refinement:{sample_id}"
        nodes[refinement_id] = ProvenanceNode(
            node_id=refinement_id,
            node_type="refinement_evidence",
            metadata=packet.get("pawley_rietveld_metrics", {}),
        )
        nodes[route_id] = ProvenanceNode(
            node_id=route_id,
            node_type="terminal_route",
            metadata=terminals.get(sample_id, {}),
        )
        nodes[training_id] = ProvenanceNode(
            node_id=training_id,
            node_type="training_route",
            metadata={
                "judge_score": scores.get(sample_id, {}),
                "reconciliation": recon.get(sample_id, {}),
            },
        )
        edges.extend(
            [
                ProvenanceEdge(source=f"sample:{sample_id}", target=trace_id, relation="observed_as"),
                ProvenanceEdge(source=trace_id, target=packet_id, relation="maps_to_packet"),
                ProvenanceEdge(source=packet_id, target=refinement_id, relation="has_refinement_evidence"),
                ProvenanceEdge(source=packet_id, target=route_id, relation="produces_terminal_route"),
                ProvenanceEdge(source=route_id, target=training_id, relation="governs_training_route"),
            ]
        )
        for index, candidate in enumerate(packet.get("candidate_cif_provenance", [])):
            candidate_id = f"candidate:{sample_id}:{index}"
            source_id = f"source_cif:{sample_id}:{index}"
            nodes[candidate_id] = ProvenanceNode(
                node_id=candidate_id,
                node_type="candidate_cif",
                metadata=candidate,
            )
            nodes[source_id] = ProvenanceNode(
                node_id=source_id,
                node_type="source_cif",
                metadata={
                    "cif_path": candidate.get("cif_path"),
                    "source": candidate.get("source"),
                    "support_only": candidate.get("support_only"),
                    "accept_eligible": candidate.get("accept_eligible"),
                    "generated_structure": candidate.get("generated_structure"),
                    "generated_provenance": candidate.get("generated_provenance"),
                },
            )
            edges.extend(
                [
                    ProvenanceEdge(source=packet_id, target=candidate_id, relation="has_candidate"),
                    ProvenanceEdge(source=candidate_id, target=source_id, relation="derived_from_source"),
                    ProvenanceEdge(source=source_id, target=route_id, relation="constrains_terminal_route"),
                ]
            )

    graph = ProvenanceGraph(nodes=list(nodes.values()), edges=edges)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for node in graph.nodes:
            file.write(json.dumps({"record_type": "node", **node.model_dump()}, sort_keys=True) + "\n")
        for edge in graph.edges:
            file.write(json.dumps({"record_type": "edge", **edge.model_dump()}, sort_keys=True) + "\n")
    return graph


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_agentxrd_provenance.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/detrix/runtime/provenance.py src/detrix/agentxrd/provenance.py tests/test_agentxrd_provenance.py
git commit -m "feat: export AgentXRD provenance DAG"
```

## Task 4: Fail-Closed Promotion Packet

**Files:**
- Create: `src/detrix/agentxrd/promotion_packet.py`
- Modify: `src/detrix/improvement/promoter.py` only if the CLI needs shared verdict types.
- Test: `tests/test_agentxrd_promotion_packet.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_agentxrd_promotion_packet.py`:

```python
import pytest

from detrix.agentxrd.promotion_packet import (
    AgentXRDPromotionMetrics,
    build_promotion_packet,
)


def test_promotion_packet_blocks_when_safety_metrics_are_clean_but_no_sft_positive():
    packet = build_promotion_packet(
        metrics=AgentXRDPromotionMetrics(
            row_count=20,
            wrong_accept_count=0,
            support_only_accept_violation_count=0,
            accept_ineligible_accept_violation_count=0,
            truth_blocked_positive_count=0,
            provisional_positive_count=0,
            sft_positive_count=0,
        )
    )

    assert packet.promote is False
    assert "no_sft_positive_rows" in packet.block_reasons


def test_promotion_packet_fails_closed_on_missing_metric():
    with pytest.raises(ValueError, match="missing required safety metric"):
        AgentXRDPromotionMetrics.model_validate(
            {
                "row_count": 20,
                "wrong_accept_count": 0,
                "support_only_accept_violation_count": 0,
                "accept_ineligible_accept_violation_count": 0,
                "truth_blocked_positive_count": 0,
                "sft_positive_count": 0,
            }
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_agentxrd_promotion_packet.py -q
```

Expected: fail with missing module.

- [ ] **Step 3: Implement promotion packet**

Create `src/detrix/agentxrd/promotion_packet.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class AgentXRDPromotionMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_count: int
    wrong_accept_count: int
    support_only_accept_violation_count: int
    accept_ineligible_accept_violation_count: int
    truth_blocked_positive_count: int
    provisional_positive_count: int
    sft_positive_count: int

    @model_validator(mode="before")
    @classmethod
    def require_all_metrics(cls, data):
        required = set(cls.model_fields)
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"missing required safety metric: {', '.join(missing)}")
        return data


class AgentXRDPromotionPacket(BaseModel):
    schema_version: str = "agentxrd_promotion_packet_v0.1"
    metrics: AgentXRDPromotionMetrics
    promote: bool
    block_reasons: list[str]
    deterministic_gates_authoritative: bool = True


def build_promotion_packet(metrics: AgentXRDPromotionMetrics) -> AgentXRDPromotionPacket:
    block_reasons: list[str] = []
    if metrics.wrong_accept_count != 0:
        block_reasons.append("wrong_accept_count_nonzero")
    if metrics.support_only_accept_violation_count != 0:
        block_reasons.append("support_only_accept_violation")
    if metrics.accept_ineligible_accept_violation_count != 0:
        block_reasons.append("accept_ineligible_accept_violation")
    if metrics.truth_blocked_positive_count != 0:
        block_reasons.append("truth_blocked_positive")
    if metrics.provisional_positive_count != 0:
        block_reasons.append("provisional_positive")
    if metrics.sft_positive_count <= 0:
        block_reasons.append("no_sft_positive_rows")
    return AgentXRDPromotionPacket(
        metrics=metrics,
        promote=not block_reasons,
        block_reasons=block_reasons,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_agentxrd_promotion_packet.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/detrix/agentxrd/promotion_packet.py tests/test_agentxrd_promotion_packet.py
git commit -m "feat: add AgentXRD promotion packet"
```

## Task 5: Threshold and Judge Drift Replay

**Files:**
- Create: `src/detrix/agentxrd/drift_replay.py`
- Test: `tests/test_agentxrd_drift_replay.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_agentxrd_drift_replay.py`:

```python
from pathlib import Path

from detrix.agentxrd.drift_replay import run_drift_replay


FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"
ROUTER = FIXTURE_ROOT / "pxrd_failure_router_v0"


def test_drift_replay_blocks_unsafe_sft_positive_delta(tmp_path):
    report = run_drift_replay(
        binary20_artifact=BINARY20 / "detrix_run_artifact.json",
        router_summary=ROUTER / "summary.json",
        output_path=tmp_path / "drift_replay_report.json",
        proposed_metrics={"sft_positive_count": 1, "wrong_accept_count": 1},
    )

    assert report.release_blocked is True
    assert "wrong_accept_regression" in report.block_reasons
    assert report.before["sft_positive_count"] == 0
    assert report.after["sft_positive_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_agentxrd_drift_replay.py -q
```

Expected: fail with missing module.

- [ ] **Step 3: Implement drift replay report**

Create `src/detrix/agentxrd/drift_replay.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class DriftReplayReport(BaseModel):
    schema_version: str = "agentxrd_drift_replay_v0.1"
    before: dict[str, int]
    after: dict[str, int]
    deltas: dict[str, int]
    release_blocked: bool
    block_reasons: list[str]


def run_drift_replay(
    *,
    binary20_artifact: Path,
    router_summary: Path,
    output_path: Path,
    proposed_metrics: dict[str, int],
) -> DriftReplayReport:
    artifact = json.loads(binary20_artifact.read_text(encoding="utf-8"))
    router = json.loads(router_summary.read_text(encoding="utf-8"))
    before = {
        "row_count": int(artifact["deterministic_gate_reconciliation"]["row_count"]),
        "sft_positive_count": 0,
        "judge_gate_conflict_count": int(
            artifact["deterministic_gate_reconciliation"]["judge_gate_conflict_count"]
        ),
        "judge_over_promote_count": int(
            artifact["deterministic_gate_reconciliation"]["judge_over_promote_count"]
        ),
        "wrong_accept_count": int(router.get("wrong_accept_count", 0)),
        "support_only_accept_violation_count": int(
            router.get("support_only_accept_violation_count", 0)
        ),
        "accept_ineligible_accept_violation_count": int(
            router.get("accept_ineligible_accept_violation_count", 0)
        ),
    }
    after = {**before, **proposed_metrics}
    deltas = {key: after.get(key, 0) - before.get(key, 0) for key in sorted(after)}
    block_reasons = []
    if after.get("wrong_accept_count", 0) > before.get("wrong_accept_count", 0):
        block_reasons.append("wrong_accept_regression")
    if after.get("support_only_accept_violation_count", 0) > 0:
        block_reasons.append("support_only_accept_violation")
    if after.get("accept_ineligible_accept_violation_count", 0) > 0:
        block_reasons.append("accept_ineligible_accept_violation")
    report = DriftReplayReport(
        before=before,
        after=after,
        deltas=deltas,
        release_blocked=bool(block_reasons),
        block_reasons=block_reasons,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_agentxrd_drift_replay.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/detrix/agentxrd/drift_replay.py tests/test_agentxrd_drift_replay.py
git commit -m "feat: add AgentXRD drift replay"
```

## Task 6: CLI and Demo Script Wiring

**Files:**
- Modify: `src/detrix/cli/main.py`
- Modify: `scripts/demo_binary20_governed_judge_cohort.py`
- Test: `tests/test_binary20_governed_judge_cohort.py`
- Test: `tests/test_agentxrd_failure_harness_cli.py`

- [ ] **Step 1: Write failing CLI smoke test**

Add `tests/test_agentxrd_failure_harness_cli.py`:

```python
import json
import sqlite3
from pathlib import Path
from click.testing import CliRunner

from detrix.cli.main import cli


FIXTURE_ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics")
BINARY20 = FIXTURE_ROOT / "binary20_governed_judge_cohort_v0"
ROUTER = FIXTURE_ROOT / "pxrd_failure_router_v0"


def test_agentxrd_harness_cli_emits_required_artifacts(tmp_path):
    db_path = tmp_path / "mc.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE langfuse_traces (
                id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL,
                name TEXT,
                project TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_cost REAL,
                latency_ms INTEGER,
                status TEXT,
                started_at TEXT,
                metadata TEXT,
                ingested_at TEXT
            )"""
        )
        conn.execute(
            """INSERT INTO langfuse_traces
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "trace-1",
                "langfuse-general",
                "AgentXRD_v2 session",
                "AgentXRD_v2",
                "qwen-test",
                10,
                5,
                0.0,
                123,
                None,
                "2026-04-28T00:00:00Z",
                json.dumps(
                    {
                        "cwd": "/home/gabriel/Desktop/AgentXRD_v2",
                        "source": "codex",
                        "model": "gpt-5.4",
                    }
                ),
                "2026-04-28T00:00:01Z",
            ),
        )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "agentxrd",
            "build-harness-evidence",
            "--binary20-artifact",
            str(BINARY20 / "detrix_run_artifact.json"),
            "--row-packets",
            str(BINARY20 / "row_packets.jsonl"),
            "--trace-packet-map",
            str(BINARY20 / "trace_to_pxrd_packet_map.jsonl"),
            "--router-decisions",
            str(ROUTER / "router_decisions.jsonl"),
            "--router-summary",
            str(ROUTER / "summary.json"),
            "--mission-control-db",
            str(db_path),
            "--langfuse-project",
            "AgentXRD_v2",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    for name in [
        "failure_patterns.jsonl",
        "failure_pattern_summary.json",
        "raw_langfuse_traces.jsonl",
        "normalized_observations.jsonl",
        "trace_to_agentxrd_packet_map.jsonl",
        "governed_next_actions.jsonl",
        "provenance_dag.jsonl",
        "promotion_packet.json",
        "drift_replay_report.json",
    ]:
        assert (tmp_path / name).exists()
    packet = json.loads((tmp_path / "promotion_packet.json").read_text())
    assert packet["promote"] is False
    summary = json.loads((tmp_path / "failure_pattern_summary.json").read_text())
    assert summary["langfuse_observation_count"] == 1
    assert summary["unjoinable_langfuse_trace_count"] == 1
    assert summary["unjoinable_langfuse_trace_patterns"]["AgentXRD_v2 session"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_agentxrd_failure_harness_cli.py -q
```

Expected: fail with missing `agentxrd` command.

- [ ] **Step 3: Add CLI group**

Modify `src/detrix/cli/main.py` following the existing Click style in the file. Add a subcommand equivalent to:

```python
@cli.group("agentxrd")
def agentxrd() -> None:
    """AgentXRD-specific governance harness commands."""


@agentxrd.command("build-harness-evidence")
@click.option("--binary20-artifact", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--row-packets", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--trace-packet-map", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--router-decisions", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--router-summary", type=click.Path(exists=True, path_type=Path), required=True)
@click.option(
    "--mission-control-db",
    type=click.Path(exists=True, path_type=Path),
    default=Path("/home/gabriel/.mission-control/data.db"),
    show_default=True,
)
@click.option("--langfuse-project", default="AgentXRD_v2", show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), required=True)
def agentxrd_build_harness_evidence(
    binary20_artifact: Path,
    row_packets: Path,
    trace_packet_map: Path,
    router_decisions: Path,
    router_summary: Path,
    mission_control_db: Path,
    langfuse_project: str,
    output_dir: Path,
) -> None:
    import_agentxrd_langfuse_traces(
        source=MissionControlLangfuseSource(
            db_path=mission_control_db,
            live_enabled=False,
        ),
        project=langfuse_project,
        output_dir=output_dir,
    )
    summary = build_failure_pattern_corpus(
        binary20_artifact=binary20_artifact,
        row_packets=row_packets,
        trace_packet_map=trace_packet_map,
        router_decisions=router_decisions,
        router_summary=router_summary,
        normalized_observations=output_dir / "normalized_observations.jsonl",
        output_dir=output_dir,
    )
    (output_dir / "trace_to_agentxrd_packet_map.jsonl").write_text(
        trace_packet_map.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    build_governed_next_actions(
        output_dir / "failure_patterns.jsonl",
        output_dir / "governed_next_actions.jsonl",
    )
    build_agentxrd_provenance_dag(
        detrix_artifact=binary20_artifact,
        trace_packet_map=trace_packet_map,
        row_packets=row_packets,
        output_path=output_dir / "provenance_dag.jsonl",
    )
    router = json.loads(router_summary.read_text(encoding="utf-8"))
    pattern_rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    packet = build_promotion_packet(
        AgentXRDPromotionMetrics(
            row_count=summary.row_count,
            wrong_accept_count=int(router.get("wrong_accept_count", 0)),
            support_only_accept_violation_count=int(
                router.get("support_only_accept_violation_count", 0)
            ),
            accept_ineligible_accept_violation_count=int(
                router.get("accept_ineligible_accept_violation_count", 0)
            ),
            truth_blocked_positive_count=sum(
                1
                for row in pattern_rows
                if row.get("deterministic_export_label") == "sft_positive"
                and row.get("truth_flags", {}).get("truth_blocked") is True
            ),
            provisional_positive_count=sum(
                1
                for row in pattern_rows
                if row.get("deterministic_export_label") == "sft_positive"
                and row.get("truth_flags", {}).get("provisional") is True
            ),
            sft_positive_count=summary.sft_positive_count,
        )
    )
    (output_dir / "promotion_packet.json").write_text(
        packet.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    run_drift_replay(
        binary20_artifact=binary20_artifact,
        router_summary=router_summary,
        output_path=output_dir / "drift_replay_report.json",
        proposed_metrics={"sft_positive_count": summary.sft_positive_count},
    )
    click.echo(f"Wrote AgentXRD harness evidence to {output_dir}")
```

- [ ] **Step 4: Preserve existing demo script outputs**

Modify `scripts/demo_binary20_governed_judge_cohort.py` to call the new modules after its existing replay finishes, writing the new harness artifacts into the same output directory. Do not remove existing outputs or change their names.

- [ ] **Step 5: Run CLI and regression tests**

Run:

```bash
uv run pytest tests/test_agentxrd_failure_harness_cli.py tests/test_binary20_governed_judge_cohort.py tests/test_agentxrd_langfuse_judge_bridge.py tests/test_axv2_adapter.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/detrix/cli/main.py scripts/demo_binary20_governed_judge_cohort.py tests/test_agentxrd_failure_harness_cli.py tests/test_binary20_governed_judge_cohort.py
git commit -m "feat: wire AgentXRD failure harness CLI"
```

## Task 7: Full Verification and Beads Closure

**Files:**
- No new code files.
- Update beads only.

- [ ] **Step 1: Run targeted harness command**

Run:

```bash
uv run detrix agentxrd build-harness-evidence \
  --binary20-artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json \
  --row-packets /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/row_packets.jsonl \
  --trace-packet-map /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/trace_to_pxrd_packet_map.jsonl \
  --router-decisions /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/router_decisions.jsonl \
  --router-summary /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/summary.json \
  --mission-control-db /home/gabriel/.mission-control/data.db \
  --langfuse-project AgentXRD_v2 \
  --output-dir /tmp/detrix-agentxrd-failure-governance-harness
```

Expected:

- command exits 0
- `/tmp/detrix-agentxrd-failure-governance-harness/failure_patterns.jsonl` has at least 20 deterministic rows plus any unjoinable Langfuse cache-summary trace patterns
- `/tmp/detrix-agentxrd-failure-governance-harness/failure_pattern_summary.json` has `langfuse_observation_count > 0` when the local Mission Control cache contains `AgentXRD_v2` traces, records `unjoinable_langfuse_trace_count` when cache rows lack AgentXRD row IDs, and otherwise has a non-null `trace_cache_miss_reason`
- `/tmp/detrix-agentxrd-failure-governance-harness/promotion_packet.json` has `"promote": false`
- `/tmp/detrix-agentxrd-failure-governance-harness/drift_replay_report.json` has `"release_blocked": false` for the unchanged baseline

- [ ] **Step 2: Run quality gates**

Run:

```bash
uv run ruff check .
uv run mypy src/detrix
uv run pytest
```

Expected: all pass.

- [ ] **Step 3: Close completed beads**

Run one close command per completed implementation bead:

```bash
bd close <BEAD_ID> --reason "Implemented and verified" --json
```

- [ ] **Step 4: Push beads and git**

Run:

```bash
git status --short
git pull --rebase
bd dolt push
git push
git status --short --branch
```

Expected: branch is up to date with origin and no uncommitted implementation changes remain except unrelated pre-existing files.

## Implementation Notes

- Do not run BGMN, DARA, Ray, or full binary20 during this implementation. Use the fixed artifacts listed above.
- Do not add new dependencies.
- Use live Langfuse only behind an explicit flag and only after cache/fixture tests pass.
- If Mission Control project filtering returns zero traces, fall back to `langfuse_trace_fixture.jsonl` and record the live/cache miss in the import report.
- Keep the existing not-proven boundary in reports: no Qwen reliability, live evaluator reliability, autonomous self-improvement, production readiness, support-only promotion, or calibrated ACCEPT claim.
