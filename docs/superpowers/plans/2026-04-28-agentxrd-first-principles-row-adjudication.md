# AgentXRD First-Principles Row Adjudication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-principles AgentXRD adjudication lane that inspects raw row evidence before deciding whether each existing binary20 blocker class is scientifically correct, scientifically wrong, or under-evidenced.

**Architecture:** Detrix will add an AgentXRD evidence resolver, row evidence packet schema, deterministic adjudicator, CLI/demo artifact wiring, and report layer. Existing router decisions remain an input, not the authority for this lane; adjudication must be based on raw XY/metadata, truth/provenance, candidate CIF/source provenance, support-only/accept-eligibility joins, Pawley/Rietveld outputs, chemistry constraints, and the router decision under review. Missing first-principles evidence yields `REQUEST_MORE_DATA`, never promotion.

**Tech Stack:** Python 3.12, Pydantic, Click, pytest, existing `src/detrix/agentxrd/*` harness modules, AgentXRD JSON/JSONL/XY/BGMN artifacts, `bd` beads, Codex native subagents.

---

## Non-Negotiable Scope

This is the missing layer after `docs/superpowers/plans/2026-04-28-agentxrd-failure-governance-harness.md`. The previous harness normalized existing AgentXRD classifications. This plan must **re-derive or challenge those classifications from evidence**.

Do not claim a row was first-principles adjudicated unless all required evidence classes for that blocker type were inspected and recorded. If evidence is absent, emit `REQUEST_MORE_DATA` with exact missing files/fields.

No task may relax these boundaries:

- `support_only=true` cannot become training-positive.
- `accept_eligible=false` cannot become training-positive.
- truth-blocked or provisional rows cannot become training-positive.
- advisory judge/Langfuse output cannot override deterministic scientific evidence.
- challenged router decisions do not imply `ACCEPT`; they imply a safer next audit or `REQUEST_MORE_DATA`.
- this work should improve demo proof for governance and evidence trails, not broaden into generic platform abstraction during the YC sprint.

## Evidence Baseline

Verified current Detrix harness outputs:

- `src/detrix/agentxrd/failure_patterns.py`
- `src/detrix/agentxrd/langfuse_importer.py`
- `src/detrix/agentxrd/next_actions.py`
- `src/detrix/agentxrd/provenance.py`
- `src/detrix/agentxrd/promotion_packet.py`
- `src/detrix/agentxrd/drift_replay.py`
- `src/detrix/cli/main.py`
- `scripts/demo_binary20_governed_judge_cohort.py`

Verified AgentXRD source artifacts:

- `/home/gabriel/Desktop/AgentXRD_v2/docs/benchmarks/2026-04-28-binary20-governed-judge-cohort-v0-plan.md`
- `/home/gabriel/Desktop/AgentXRD_v2/scripts/build_binary20_governed_judge_cohort_v0.py`
- `/home/gabriel/Desktop/AgentXRD_v2/scripts/build_binary20_scientist_judge_packets_v0.py`
- `/home/gabriel/Desktop/AgentXRD_v2/scripts/audit_binary20_accept_promotion_v0.py`
- `/home/gabriel/Desktop/AgentXRD_v2/data/binary_support_manifest.json`
- `/home/gabriel/Desktop/AgentXRD_v2/data/manifest_materialized_splits.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/benchmark_e2e/binary20_pawley_degradation_safety_20260427_cap4.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/benchmark_e2e/binary20_pawley_degradation_safety_20260427_cap4.enriched.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/benchmark_e2e/binary20_pawley_degradation_safety_20260427_cap4.assertions.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/benchmark_e2e/binary20_pawley_degradation_safety_20260427_cap4_trace/`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/benchmark_e2e/binary20_pawley_degradation_safety_20260427_cap4_workdirs/`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/row_packets.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/trace_to_pxrd_packet_map.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/deterministic_gate_reconciliation.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/judge_gate_disagreement_matrix.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_accept_promotion_audit_v0/row_classifications.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_accept_eligibility_provenance_join_v0/row_join_table.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_accept_eligibility_provenance_join_v0/candidate_identity_join.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/reaction_product_candidate_discovery_v0/candidate_registry.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/router_decisions.jsonl`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/summary.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/nb_truth_provenance_audit_20260427/*.truth_provenance.json`
- `/home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/crzn_accept_eligibility_runtime_probe_v0/`

Current governed-cohort directory does **not** contain `row_classifications.json`, `blocks.jsonl`, `review_recommendations.json`, or `promotion_candidates.json`; use the accept-promotion audit and row packet artifacts instead.

## File Structure

- Create: `src/detrix/agentxrd/evidence_resolver.py`
  - Locate and validate evidence files by `sample_id`.
  - Resolve raw XY, benchmark rows, enriched chemistry rows, workdirs, traces, row packets, support manifest entries, provenance joins, candidate registry rows, and router decisions.
- Create: `src/detrix/agentxrd/row_evidence.py`
  - Pydantic schemas for `RowEvidencePacket`, `EvidenceStatus`, `EvidenceReference`, and per-domain evidence sections.
- Create: `src/detrix/agentxrd/adjudication.py`
  - Deterministic adjudication rules producing `RowAdjudication`.
  - Compare evidence-derived blocker classification to router `blocker_class`.
- Create: `src/detrix/agentxrd/adjudication_report.py`
  - JSON and Markdown report helpers.
- Modify: `src/detrix/agentxrd/failure_patterns.py`
  - Optionally attach adjudication status/source evidence to failure rows.
  - Do not replace existing fields or break previous harness artifacts.
- Modify: `src/detrix/cli/main.py`
  - Add `detrix agentxrd adjudicate-rows`.
  - Add optional adjudication wiring to `build-harness-evidence` only after standalone command passes.
- Modify: `scripts/demo_binary20_governed_judge_cohort.py`
  - Emit adjudication artifacts when verified seed evidence exists, without changing legacy outputs.
- Test: `tests/test_agentxrd_evidence_resolver.py`
- Test: `tests/test_agentxrd_row_evidence.py`
- Test: `tests/test_agentxrd_adjudication.py`
- Test: `tests/test_agentxrd_adjudication_cli.py`
- Test: `tests/test_agentxrd_adjudication_report.py`
- Test: extend `tests/test_agentxrd_failure_harness_cli.py`
- Test: extend `tests/test_binary20_governed_judge_cohort.py`

## Artifact Contracts

Standalone command must emit:

- `row_evidence_packets.jsonl`
- `row_adjudications.jsonl`
- `adjudication_summary.json`
- `adjudication_report.md`
- `adjudication_missing_evidence.jsonl`

Optional integration with existing harness must preserve all prior outputs and additionally emit the five files above.

## First-Principles Evidence Matrix

Adjudication is not valid until every row records the following section states as one of `parsed`, `present_unparsed`, `contradictory`, or `missing`. `CONFIRMED` and `CHALLENGED` require `parsed` for all blocker-specific required sections. `REQUEST_MORE_DATA` is mandatory when any blocker-specific required section is `missing` or only `present_unparsed`.

| Candidate blocker | Raw XY/metadata | Truth/provenance | Candidate CIF/source | Eligibility joins | Pawley/Rietveld/refinement | Chemistry constraints | Router decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SUPPORT_ONLY_BLOCKED` | parsed XY path plus scan metadata when present | parsed truth labels/verdict | parsed candidate CIF/source references if candidates exist | parsed `support_only`, `accept_eligible`, support manifest, row/candidate joins | present or parsed, not decisive | parsed sample/formula allowed elements | present only for comparison |
| `TRUTH_CONFLICT` | parsed XY path plus row metadata | parsed truth labels, provisional flags, `current_verdict`, exact-match state, Nb truth audit when applicable | parsed candidate/source references enough to show what was proposed | parsed eligibility joins to prove no promotion leak | present or parsed, not decisive | parsed ground-truth phases and selected phases | present only for comparison |
| `PROVENANCE_GAP` | parsed XY path plus row metadata | parsed truth labels/verdict | parsed CIF paths, source type, registry rows, identity join, missing/invalid candidate sources | parsed row/candidate joins and accept eligibility propagation | present or parsed, not decisive | parsed candidate formulas/elements | present only for comparison |
| `INSUFFICIENT_ARTIFACT_EVIDENCE` | parsed XY path and finite intensity sanity | parsed truth labels/verdict | parsed candidate CIF/source references | parsed eligibility joins | parsed workdir outputs and best available Pawley/Rietveld evidence | parsed `reason_codes`, `ranked_hypotheses[].chemistry_checks`, `phase_constraint_diagnostics`, `selected_phase_ids`, `ground_truth_phases`, precursor/sample-id allowed elements | present only for comparison |
| `AMBIGUOUS_MULTI_HYPOTHESIS` | parsed XY path and finite intensity sanity | parsed truth labels/verdict | parsed candidate sources for competing hypotheses | parsed eligibility joins | parsed ranked/refined hypothesis count and Rwp spread when available | parsed competing-hypothesis chemistry checks | present only for comparison |
| `REFINEMENT_STRATEGY` | parsed XY path and finite intensity sanity | parsed truth labels/verdict | parsed CIF/source references for refined candidates | parsed eligibility joins | parsed `.lst`, `.dia`, `.par`, summary JSON, best Rwp, failed strategy/fallback indicators | parsed chemistry checks to rule out chemistry-first blocker | present only for comparison |

Implementation must parse enough content to support each state. Path existence alone is insufficient for `parsed`. Raw XY parsing must check row count, finite numeric x/y values, and usable two-column or known schema structure. Candidate CIF parsing must extract or verify formula/source/provenance identifiers. Refinement parsing must inspect available BGMN/Pawley/Rietveld files or structured summaries rather than only recording workdir existence. Chemistry parsing must use current fields: `reason_codes`, `ranked_hypotheses[].chemistry_checks`, `phase_constraint_diagnostics`, `selected_phase_ids`, `ground_truth_phases`, and precursor/sample-id-derived allowed elements.

## Subagent Protocol

Use subagents before implementation and at review gates:

1. **AgentXRD evidence mapper** (`explore`, read-only)
   - CWD: `/home/gabriel/Desktop/AgentXRD_v2`
   - Verify all evidence surfaces listed above still exist.
   - Return exact file paths and field names for raw XY, truth/provenance, candidates, joins, refinement, chemistry, and router inputs.
   - Patch this plan's evidence matrix and field contract before Task 1 starts if the local artifact schema differs.

2. **Detrix implementation mapper** (`explore`, read-only)
   - CWD: `/home/gabriel/Desktop/detrix-core`
   - Verify existing harness module boundaries and tests.
   - Return risks before Task 1 starts.

3. **Task reviewers** (`code-reviewer` or `verifier`, read-only)
   - After Tasks 2, 3, 4, and 6, review the diff and artifacts.
   - Reject if the implementation merely reuses router labels as ground truth.

Never delegate write access to the same files from two agents at once. Each implementation subagent owns one task and reports changed paths.

## Beads

Created tracker IDs:

- `detrix-core-vrx`: Plan first-principles AgentXRD row adjudication harness
- `detrix-core-54v`: Epic: AgentXRD first-principles row adjudication
- `detrix-core-phq`: Map AgentXRD first-principles evidence surfaces
- `detrix-core-uf8`: Implement AgentXRD row evidence packet schema
- `detrix-core-poc`: Adjudicate AgentXRD blocker classes from first principles
- `detrix-core-zy3`: Wire AgentXRD adjudication into harness artifacts
- `detrix-core-s10`: Add AgentXRD first-principles adjudication reports
- `detrix-core-6bn`: Validate AgentXRD adjudication harness end to end

Claim each bead before its task:

```bash
bd update <ID> --claim --json
```

Close only after tests, commit, and artifact verification:

```bash
bd close <ID> --reason "Completed and verified" --json
```

Every task commit must use the repo Lore protocol. If using the short `git commit -m` examples below, replace them with a multi-line message that includes at least `Constraint:`, `Confidence:`, `Scope-risk:`, `Tested:`, and `Not-tested:` trailers. Record any rejected shortcut that would have reused router labels or promotion buckets as truth.

## Task 1: Evidence Resolver Inventory

**Files:**
- Create: `src/detrix/agentxrd/evidence_resolver.py`
- Test: `tests/test_agentxrd_evidence_resolver.py`
- Bead: `detrix-core-phq`

- [ ] **Step 1: Claim bead**

```bash
bd update detrix-core-phq --claim --json
```

- [ ] **Step 2: Write failing resolver tests**

Add `tests/test_agentxrd_evidence_resolver.py`:

```python
from pathlib import Path

from detrix.agentxrd.evidence_resolver import AgentXRDEvidenceResolver

ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2")


def test_resolver_finds_required_binary20_surfaces():
    resolver = AgentXRDEvidenceResolver.default(root=ROOT)
    inventory = resolver.build_inventory()

    assert inventory.row_count == 20
    assert inventory.binary20_artifact.exists()
    assert inventory.row_packets.exists()
    assert inventory.router_decisions.exists()
    assert inventory.benchmark_raw.exists()
    assert inventory.benchmark_enriched.exists()
    assert inventory.workdirs_root.exists()
    assert inventory.trace_root.exists()


def test_resolver_builds_row_index_with_raw_xy_and_router_decision():
    resolver = AgentXRDEvidenceResolver.default(root=ROOT)
    row = resolver.resolve_row("dara_2Fe3O4-3Y2O3_1000C_60min")

    assert row.sample_id == "dara_2Fe3O4-3Y2O3_1000C_60min"
    assert row.raw_xy_path is not None
    assert row.raw_xy_path.name.endswith(".xy")
    assert row.row_packet is not None
    assert row.router_decision is not None
    assert row.benchmark_row is not None
    assert row.enriched_row is not None
```

- [ ] **Step 3: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_agentxrd_evidence_resolver.py -q
```

Expected: import failure for `detrix.agentxrd.evidence_resolver`.

- [ ] **Step 4: Implement minimal resolver**

Create `src/detrix/agentxrd/evidence_resolver.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class EvidenceInventory(BaseModel):
    root: Path
    row_count: int
    binary20_artifact: Path
    row_packets: Path
    router_decisions: Path
    router_summary: Path
    benchmark_raw: Path
    benchmark_enriched: Path
    benchmark_assertions: Path
    workdirs_root: Path
    trace_root: Path
    support_manifest: Path
    materialized_manifest: Path
    promotion_row_classifications: Path
    provenance_row_join_table: Path
    provenance_candidate_join: Path
    candidate_registry: Path


class ResolvedRowEvidence(BaseModel):
    sample_id: str
    raw_xy_path: Path | None
    work_dir: Path | None
    trace_path: Path | None
    row_packet: dict[str, Any] | None
    router_decision: dict[str, Any] | None
    benchmark_row: dict[str, Any] | None
    enriched_row: dict[str, Any] | None
    support_manifest_entry: dict[str, Any] | None
    promotion_classification: dict[str, Any] | None
    provenance_join: dict[str, Any] | None
    candidate_identity_rows: list[dict[str, Any]]
    candidate_registry_rows: list[dict[str, Any]]
    missing_evidence: list[str]


class AgentXRDEvidenceResolver:
    def __init__(self, *, root: Path) -> None:
        self.root = root
        self.inventory = self._inventory(root)

    @classmethod
    def default(cls, *, root: Path) -> "AgentXRDEvidenceResolver":
        return cls(root=root)

    def build_inventory(self) -> EvidenceInventory:
        return self.inventory

    def resolve_row(self, sample_id: str) -> ResolvedRowEvidence:
        packets = {str(row["sample_id"]): row for row in _jsonl(self.inventory.row_packets)}
        routers = {str(row["sample_id"]): row for row in _jsonl(self.inventory.router_decisions)}
        raw_rows = {str(row["sample_id"]): row for row in _jsonl(self.inventory.benchmark_raw)}
        enriched = {str(row["sample_id"]): row for row in _jsonl(self.inventory.benchmark_enriched)}
        support = {str(row.get("sample_id")): row for row in _load_support_rows(self.inventory.support_manifest)}
        classes = {str(row["sample_id"]): row for row in _load_classification_rows(self.inventory.promotion_row_classifications)}
        joins = {str(row["sample_id"]): row for row in _jsonl(self.inventory.provenance_row_join_table)}
        candidate_joins = [row for row in _jsonl(self.inventory.provenance_candidate_join) if str(row.get("sample_id")) == sample_id]
        registry = [row for row in _jsonl(self.inventory.candidate_registry) if str(row.get("sample_id")) == sample_id]

        packet = packets.get(sample_id)
        work_dir = _resolve_work_dir(self.root, packet)
        raw_xy = _find_xy(sample_id, work_dir, self.root / "outputs" / "diagnostics" / "xy_cache")
        trace_path = _resolve_trace_path(self.root, packet)
        missing = []
        for name, value in {
            "row_packet": packet,
            "router_decision": routers.get(sample_id),
            "benchmark_row": raw_rows.get(sample_id),
            "enriched_row": enriched.get(sample_id),
            "raw_xy_path": raw_xy,
            "work_dir": work_dir if work_dir and work_dir.exists() else None,
            "trace_path": trace_path if trace_path and trace_path.exists() else None,
        }.items():
            if value is None:
                missing.append(name)

        return ResolvedRowEvidence(
            sample_id=sample_id,
            raw_xy_path=raw_xy,
            work_dir=work_dir if work_dir and work_dir.exists() else None,
            trace_path=trace_path if trace_path and trace_path.exists() else None,
            row_packet=packet,
            router_decision=routers.get(sample_id),
            benchmark_row=raw_rows.get(sample_id),
            enriched_row=enriched.get(sample_id),
            support_manifest_entry=support.get(sample_id),
            promotion_classification=classes.get(sample_id),
            provenance_join=joins.get(sample_id),
            candidate_identity_rows=candidate_joins,
            candidate_registry_rows=registry,
            missing_evidence=missing,
        )
```

Also implement `_inventory`, `_jsonl`, `_load_support_rows`, `_load_classification_rows`, `_resolve_work_dir`, `_resolve_trace_path`, and `_find_xy` in the same file. Keep helpers pure and path-based.

- [ ] **Step 5: Run resolver tests**

```bash
uv run pytest tests/test_agentxrd_evidence_resolver.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/detrix/agentxrd/evidence_resolver.py tests/test_agentxrd_evidence_resolver.py
git commit -m "feat: map AgentXRD first-principles evidence surfaces (detrix-core-phq)"
```

Use Lore trailers in the commit body.

## Task 2: Row Evidence Packet Schema

**Files:**
- Create: `src/detrix/agentxrd/row_evidence.py`
- Modify: `src/detrix/agentxrd/evidence_resolver.py`
- Test: `tests/test_agentxrd_row_evidence.py`
- Bead: `detrix-core-uf8`

- [ ] **Step 1: Claim bead**

```bash
bd update detrix-core-uf8 --claim --json
```

- [ ] **Step 2: Write failing schema tests**

Add `tests/test_agentxrd_row_evidence.py`:

```python
from pathlib import Path

from detrix.agentxrd.evidence_resolver import AgentXRDEvidenceResolver
from detrix.agentxrd.row_evidence import build_row_evidence_packet

ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2")


def test_row_evidence_packet_records_all_required_evidence_classes():
    resolved = AgentXRDEvidenceResolver.default(root=ROOT).resolve_row(
        "dara_2Fe3O4-3Y2O3_1000C_60min"
    )

    packet = build_row_evidence_packet(resolved)

    assert packet.sample_id == resolved.sample_id
    assert packet.raw_pattern.status == "present"
    assert packet.truth.status in {"present", "partial", "missing"}
    assert packet.candidate_provenance.status in {"present", "partial", "missing"}
    assert packet.eligibility_join.status in {"present", "partial", "missing"}
    assert packet.refinement.status in {"present", "partial", "missing"}
    assert packet.chemistry.status in {"present", "partial", "missing"}
    assert packet.router.status == "present"
    assert packet.training_export_blocked is True


def test_missing_raw_xy_does_not_disappear_from_packet(tmp_path):
    resolved = AgentXRDEvidenceResolver.default(root=ROOT).resolve_row(
        "dara_2FeC2O4_H2O_2-Y2O3_200C_60min"
    )
    resolved.raw_xy_path = None

    packet = build_row_evidence_packet(resolved)

    assert packet.raw_pattern.status == "missing"
    assert "raw_xy_path" in packet.missing_required_evidence
```

Before implementing, verify both sample IDs exist in the Detrix `row_packets.jsonl` fixture. If the second row is absent in the local artifact snapshot, select any existing row and keep the explicit `raw_xy_path = None` mutation.

- [ ] **Step 3: Run test and verify failure**

```bash
uv run pytest tests/test_agentxrd_row_evidence.py -q
```

Expected: import failure for `detrix.agentxrd.row_evidence`.

- [ ] **Step 4: Implement schemas and packet builder**

Create `src/detrix/agentxrd/row_evidence.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from detrix.agentxrd.evidence_resolver import ResolvedRowEvidence

EvidenceState = Literal["present", "partial", "missing"]


class EvidenceReference(BaseModel):
    path: str
    kind: str
    exists: bool


class EvidenceStatus(BaseModel):
    status: EvidenceState
    inspection_state: Literal["parsed", "present_unparsed", "contradictory", "missing"]
    references: list[EvidenceReference] = Field(default_factory=list)
    fields: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class RowEvidencePacket(BaseModel):
    schema_version: str = "agentxrd_row_evidence_v0.1"
    sample_id: str
    raw_pattern: EvidenceStatus
    truth: EvidenceStatus
    candidate_provenance: EvidenceStatus
    eligibility_join: EvidenceStatus
    refinement: EvidenceStatus
    chemistry: EvidenceStatus
    router: EvidenceStatus
    missing_required_evidence: list[str] = Field(default_factory=list)
    training_export_blocked: bool = True


def build_row_evidence_packet(row: ResolvedRowEvidence) -> RowEvidencePacket:
    missing: list[str] = []
    raw = _path_status("raw_xy_path", row.raw_xy_path, missing)
    truth = _dict_status("truth", row.row_packet, ["truth_flags"], missing)
    candidate = _candidate_status(row, missing)
    eligibility = _eligibility_status(row, missing)
    refinement = _refinement_status(row, missing)
    chemistry = _dict_status(
        "chemistry",
        row.enriched_row,
        [
            "reason_codes",
            "ranked_hypotheses",
            "phase_constraint_diagnostics",
            "selected_phase_ids",
            "ground_truth_phases",
        ],
        missing,
    )
    router = _dict_status("router", row.router_decision, ["blocker_class"], missing)

    return RowEvidencePacket(
        sample_id=row.sample_id,
        raw_pattern=raw,
        truth=truth,
        candidate_provenance=candidate,
        eligibility_join=eligibility,
        refinement=refinement,
        chemistry=chemistry,
        router=router,
        missing_required_evidence=missing,
    )
```

Implement helpers so they preserve references and relevant fields:

- `raw_pattern`: XY path, workdir, trace path, parsed x/y row count, finite-value checks, x-range, y-range, and parse errors.
- `truth`: `truth_flags`, `current_verdict`, `exact_match`, promotion audit classification.
- `candidate_provenance`: packet candidate CIFs, candidate identity joins, registry rows, parsed CIF formula/source/provenance identifiers, and missing candidate files.
- `eligibility_join`: `support_only`, `accept_eligible`, support manifest, provenance join.
- `refinement`: `best_rwp`, `n_refined`, `pawley_fallback`, parsed `.lst`/`.dia`/`.par` or structured summary evidence, and failed-strategy/fallback indicators.
- `chemistry`: enriched row `reason_codes`, `ranked_hypotheses[].chemistry_checks`, `phase_constraint_diagnostics`, `selected_phase_ids`, `ground_truth_phases`, and precursor/sample-id-derived allowed elements.
- `router`: router blocker class and blocking fields.

Tests must include negative controls that remove or corrupt content, not just paths:

- mutate the router blocker label and assert evidence-derived adjudication does not follow the mutation;
- set a candidate CIF path to a nonexistent file and assert candidate provenance becomes `missing` or `present_unparsed`;
- remove raw XY content or inject non-finite intensity values and assert `REQUEST_MORE_DATA`;
- remove refinement `.lst`/`.dia`/`.par` evidence for a refinement-strategy row and assert `REQUEST_MORE_DATA`;
- inject `support_only=true` or `accept_eligible=false` and assert `training_export_blocked` remains true.

- [ ] **Step 5: Run schema tests**

```bash
uv run pytest tests/test_agentxrd_row_evidence.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/detrix/agentxrd/evidence_resolver.py src/detrix/agentxrd/row_evidence.py tests/test_agentxrd_row_evidence.py
git commit -m "feat: build AgentXRD row evidence packets (detrix-core-uf8)"
```

## Task 3: First-Principles Adjudicator

**Files:**
- Create: `src/detrix/agentxrd/adjudication.py`
- Test: `tests/test_agentxrd_adjudication.py`
- Bead: `detrix-core-poc`

- [ ] **Step 1: Claim bead**

```bash
bd update detrix-core-poc --claim --json
```

- [ ] **Step 2: Write failing adjudication tests**

Add `tests/test_agentxrd_adjudication.py`:

```python
from pathlib import Path

from detrix.agentxrd.adjudication import adjudicate_row
from detrix.agentxrd.evidence_resolver import AgentXRDEvidenceResolver
from detrix.agentxrd.row_evidence import build_row_evidence_packet

ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2")


def _packet(sample_id: str):
    resolved = AgentXRDEvidenceResolver.default(root=ROOT).resolve_row(sample_id)
    return build_row_evidence_packet(resolved)


def test_support_only_blocker_is_confirmed_from_evidence_not_router_label():
    packet = _packet("dara_Bi2O3-2MoO3_400C_60min")
    packet.router.fields["blocker_class"] = "REFINEMENT_STRATEGY"

    adjudication = adjudicate_row(packet)

    assert adjudication.status == "CHALLENGED"
    assert adjudication.evidence_derived_blocker == "SUPPORT_ONLY_BLOCKED"
    assert "support_only" in adjudication.primary_evidence
    assert adjudication.training_export_blocked is True


def test_missing_required_evidence_requests_more_data():
    packet = _packet("dara_CoO-ZnO_1100C_60min")
    packet.raw_pattern.status = "missing"
    packet.missing_required_evidence.append("raw_xy_path")

    adjudication = adjudicate_row(packet)

    assert adjudication.status == "REQUEST_MORE_DATA"
    assert "raw_xy_path" in adjudication.missing_evidence
    assert adjudication.training_export_blocked is True


def test_ambiguous_multi_hypothesis_can_be_confirmed_from_refinement_and_verdict():
    packet = _packet("dara_CoO-ZnO_1100C_60min")

    adjudication = adjudicate_row(packet)

    assert adjudication.evidence_derived_blocker in {
        "AMBIGUOUS_MULTI_HYPOTHESIS",
        "REQUEST_MORE_DATA",
    }
    assert adjudication.training_export_blocked is True


def test_refinement_blocker_requires_parsed_refinement_artifacts():
    packet = _packet("dara_CoO-ZnO_1100C_60min")
    packet.router.fields["blocker_class"] = "REFINEMENT_STRATEGY"
    packet.refinement.inspection_state = "present_unparsed"

    adjudication = adjudicate_row(packet)

    assert adjudication.status == "REQUEST_MORE_DATA"
    assert "refinement" in adjudication.missing_evidence
```

- [ ] **Step 3: Run test and verify failure**

```bash
uv run pytest tests/test_agentxrd_adjudication.py -q
```

Expected: import failure for `detrix.agentxrd.adjudication`.

- [ ] **Step 4: Implement adjudication models and rules**

Create `src/detrix/agentxrd/adjudication.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from detrix.agentxrd.row_evidence import RowEvidencePacket

AdjudicationStatus = Literal["CONFIRMED", "CHALLENGED", "REQUEST_MORE_DATA"]


class RowAdjudication(BaseModel):
    schema_version: str = "agentxrd_row_adjudication_v0.1"
    sample_id: str
    router_blocker_class: str | None
    evidence_derived_blocker: str | None
    status: AdjudicationStatus
    primary_evidence: list[str] = Field(default_factory=list)
    parsed_evidence_references: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    scientific_rationale: str
    training_export_blocked: bool = True


def adjudicate_row(packet: RowEvidencePacket) -> RowAdjudication:
    router_blocker = packet.router.fields.get("blocker_class")
    required_gap = missing_required_sections_for_router(packet)
    if packet.missing_required_evidence or required_gap:
        return RowAdjudication(
            sample_id=packet.sample_id,
            router_blocker_class=router_blocker,
            evidence_derived_blocker=None,
            status="REQUEST_MORE_DATA",
            missing_evidence=[*packet.missing_required_evidence, *required_gap],
            scientific_rationale=(
                "First-principles adjudication is blocked because required raw "
                "or provenance evidence is absent."
            ),
        )

    derived, evidence = derive_blocker_from_evidence(packet)
    status: AdjudicationStatus = "CONFIRMED" if derived == router_blocker else "CHALLENGED"
    return RowAdjudication(
        sample_id=packet.sample_id,
        router_blocker_class=router_blocker,
        evidence_derived_blocker=derived,
        status=status,
        primary_evidence=evidence,
        parsed_evidence_references=_parsed_non_router_references(packet, evidence),
        scientific_rationale=_rationale(derived, router_blocker, evidence),
    )
```

Implement `derive_blocker_from_evidence()` in precedence order:

1. support-only evidence proves `SUPPORT_ONLY_BLOCKED`.
2. truth/provisional blockers prove `TRUTH_CONFLICT`.
3. candidate provenance gap or accept eligibility propagation mismatch proves `PROVENANCE_GAP`.
4. exact-match false or chemistry missing expected elements proves `INSUFFICIENT_ARTIFACT_EVIDENCE` unless ambiguity/refinement evidence is stronger.
5. multiple hypotheses, `SET`, or hypothesis-count evidence proves `AMBIGUOUS_MULTI_HYPOTHESIS`.
6. refined row with high/near-threshold Rwp, failed Rietveld/Pawley, or strategy-specific blocker proves `REFINEMENT_STRATEGY`.
7. otherwise `REQUEST_MORE_DATA`.

Keep this function deterministic and auditable. Do not call LLMs.

Implement `missing_required_sections_for_router()` from the First-Principles Evidence Matrix. It must require `inspection_state == "parsed"` for every blocker-specific required section before allowing `CONFIRMED` or `CHALLENGED`. The router label selects the minimum required section set only; it cannot determine the evidence-derived blocker. If the router label is missing or unknown, require all sections except router and return `REQUEST_MORE_DATA` until parsed.

- [ ] **Step 5: Run adjudication tests**

```bash
uv run pytest tests/test_agentxrd_adjudication.py -q
```

Expected: pass.

- [ ] **Step 6: Dispatch code-reviewer subagent**

Prompt:

```text
Read-only review in /home/gabriel/Desktop/detrix-core. Review the diff for Task 3 of docs/superpowers/plans/2026-04-28-agentxrd-first-principles-row-adjudication.md. Verify adjudication derives blocker class from RowEvidencePacket fields, not from router labels alone. Flag promotion-safety regressions, missing evidence fail-open behavior, and test gaps.
```

Fix blocking findings before committing.

- [ ] **Step 7: Commit**

```bash
git add src/detrix/agentxrd/adjudication.py tests/test_agentxrd_adjudication.py
git commit -m "feat: adjudicate AgentXRD blockers from evidence (detrix-core-poc)"
```

## Task 4: CLI And Harness Artifact Wiring

**Files:**
- Modify: `src/detrix/cli/main.py`
- Modify: `scripts/demo_binary20_governed_judge_cohort.py`
- Modify: `src/detrix/agentxrd/failure_patterns.py`
- Test: `tests/test_agentxrd_adjudication_cli.py`
- Test: extend `tests/test_agentxrd_failure_harness_cli.py`
- Test: extend `tests/test_binary20_governed_judge_cohort.py`
- Bead: `detrix-core-zy3`

- [ ] **Step 1: Claim bead**

```bash
bd update detrix-core-zy3 --claim --json
```

- [ ] **Step 2: Write failing CLI test**

Add `tests/test_agentxrd_adjudication_cli.py`:

```python
import json
from pathlib import Path

from click.testing import CliRunner

from detrix.cli.main import cli

ROOT = Path("/home/gabriel/Desktop/AgentXRD_v2")


def test_agentxrd_adjudicate_rows_cli_emits_packets_and_adjudications(tmp_path):
    result = CliRunner().invoke(
        cli,
        [
            "agentxrd",
            "adjudicate-rows",
            "--agentxrd-root",
            str(ROOT),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    for name in [
        "row_evidence_packets.jsonl",
        "row_adjudications.jsonl",
        "adjudication_summary.json",
        "adjudication_missing_evidence.jsonl",
    ]:
        assert (tmp_path / name).exists(), name

    summary = json.loads((tmp_path / "adjudication_summary.json").read_text())
    assert summary["row_count"] == 20
    assert summary["training_export_blocked_count"] == 20
    assert summary["first_principles_claim"] in {"complete", "partial"}
    assert summary["parsed_section_counts"]["raw_pattern"] == 20
```

- [ ] **Step 3: Run test and verify failure**

```bash
uv run pytest tests/test_agentxrd_adjudication_cli.py -q
```

Expected: Click reports no such command `adjudicate-rows`.

- [ ] **Step 4: Implement CLI helper**

Add to `src/detrix/cli/main.py` under the existing `agentxrd` group:

```python
@agentxrd.command("adjudicate-rows")
@click.option("--agentxrd-root", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--output-dir", type=click.Path(path_type=Path), required=True)
def agentxrd_adjudicate_rows(agentxrd_root: Path, output_dir: Path) -> None:
    from detrix.agentxrd.adjudication import adjudicate_row
    from detrix.agentxrd.adjudication_report import write_adjudication_artifacts
    from detrix.agentxrd.evidence_resolver import AgentXRDEvidenceResolver
    from detrix.agentxrd.row_evidence import build_row_evidence_packet

    resolver = AgentXRDEvidenceResolver.default(root=agentxrd_root)
    inventory = resolver.build_inventory()
    packets = []
    adjudications = []
    for sample_id in resolver.sample_ids():
        packet = build_row_evidence_packet(resolver.resolve_row(sample_id))
        packets.append(packet)
        adjudications.append(adjudicate_row(packet))
    write_adjudication_artifacts(
        output_dir=output_dir,
        inventory=inventory,
        packets=packets,
        adjudications=adjudications,
    )
    click.echo(f"Rows adjudicated: {len(adjudications)}")
```

Add `sample_ids()` to `AgentXRDEvidenceResolver`.

Also add an optional `--agentxrd-root PATH` option to the existing `build-harness-evidence` command. When omitted, behavior must remain compatible with the existing harness tests. When present, the command should call the same adjudication writer used by `agentxrd adjudicate-rows` and append the five adjudication artifacts to the requested output directory.

- [ ] **Step 5: Run CLI test**

```bash
uv run pytest tests/test_agentxrd_adjudication_cli.py -q
```

Expected: pass.

- [ ] **Step 6: Extend existing harness CLI test**

In `tests/test_agentxrd_failure_harness_cli.py`, assert the optional integrated command emits the five adjudication artifacts when `--agentxrd-root` or equivalent option is provided. Do not require Mission Control DB for adjudication.

- [ ] **Step 7: Split synthetic and real demo tests**

Keep the existing synthetic-temp fixture tests focused on legacy governed-cohort outputs only. Do not make synthetic row packets pretend to support first-principles adjudication.

Add a real-artifact test, skipped only when `/home/gabriel/Desktop/AgentXRD_v2` is absent, that runs the demo or CLI with `--agentxrd-root /home/gabriel/Desktop/AgentXRD_v2` and verifies these outputs are produced from real local artifacts:

- `row_evidence_packets.jsonl`
- `row_adjudications.jsonl`
- `adjudication_summary.json`
- `adjudication_report.md`
- `adjudication_missing_evidence.jsonl`

The real-artifact test must assert every `CONFIRMED` or `CHALLENGED` row cites at least one parsed evidence reference outside `router`, and all rows keep `training_export_blocked=true`.

- [ ] **Step 8: Run focused tests**

```bash
uv run pytest tests/test_agentxrd_adjudication_cli.py tests/test_agentxrd_failure_harness_cli.py tests/test_binary20_governed_judge_cohort.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add src/detrix/cli/main.py scripts/demo_binary20_governed_judge_cohort.py src/detrix/agentxrd/failure_patterns.py tests/test_agentxrd_adjudication_cli.py tests/test_agentxrd_failure_harness_cli.py tests/test_binary20_governed_judge_cohort.py
git commit -m "feat: wire AgentXRD row adjudication artifacts (detrix-core-zy3)"
```

## Task 5: Adjudication Reports

**Files:**
- Create: `src/detrix/agentxrd/adjudication_report.py`
- Test: `tests/test_agentxrd_adjudication_report.py`
- Bead: `detrix-core-s10`

- [ ] **Step 1: Claim bead**

```bash
bd update detrix-core-s10 --claim --json
```

- [ ] **Step 2: Write failing report test**

Add `tests/test_agentxrd_adjudication_report.py`:

```python
from pathlib import Path

from detrix.agentxrd.adjudication import RowAdjudication
from detrix.agentxrd.adjudication_report import build_adjudication_summary


def test_summary_counts_confirmed_challenged_and_request_more_data():
    rows = [
        RowAdjudication(
            sample_id="a",
            router_blocker_class="SUPPORT_ONLY_BLOCKED",
            evidence_derived_blocker="SUPPORT_ONLY_BLOCKED",
            status="CONFIRMED",
            primary_evidence=["support_only"],
            scientific_rationale="confirmed",
        ),
        RowAdjudication(
            sample_id="b",
            router_blocker_class="PROVENANCE_GAP",
            evidence_derived_blocker="TRUTH_CONFLICT",
            status="CHALLENGED",
            primary_evidence=["truth_flags"],
            scientific_rationale="challenged",
        ),
        RowAdjudication(
            sample_id="c",
            router_blocker_class="REFINEMENT_STRATEGY",
            evidence_derived_blocker=None,
            status="REQUEST_MORE_DATA",
            missing_evidence=["raw_xy_path"],
            scientific_rationale="missing evidence",
        ),
    ]

    summary = build_adjudication_summary(rows)

    assert summary["row_count"] == 3
    assert summary["status_counts"]["CONFIRMED"] == 1
    assert summary["status_counts"]["CHALLENGED"] == 1
    assert summary["status_counts"]["REQUEST_MORE_DATA"] == 1
    assert summary["training_export_blocked_count"] == 3
    assert summary["first_principles_claim"] == "partial"
```

- [ ] **Step 3: Run test and verify failure**

```bash
uv run pytest tests/test_agentxrd_adjudication_report.py -q
```

Expected: import failure.

- [ ] **Step 4: Implement report helpers**

Create `src/detrix/agentxrd/adjudication_report.py`:

```python
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from detrix.agentxrd.adjudication import RowAdjudication
from detrix.agentxrd.evidence_resolver import EvidenceInventory
from detrix.agentxrd.row_evidence import RowEvidencePacket


def build_adjudication_summary(rows: list[RowAdjudication]) -> dict[str, object]:
    status_counts = Counter(row.status for row in rows)
    derived_counts = Counter(row.evidence_derived_blocker or "REQUEST_MORE_DATA" for row in rows)
    parsed_section_counts = _parsed_section_counts(rows)
    all_confirmed_or_challenged_cite_parsed_evidence = all(
        row.status == "REQUEST_MORE_DATA" or _has_non_router_parsed_evidence(row)
        for row in rows
    )
    return {
        "schema_version": "agentxrd_adjudication_summary_v0.1",
        "row_count": len(rows),
        "status_counts": dict(status_counts),
        "evidence_derived_blocker_counts": dict(derived_counts),
        "training_export_blocked_count": sum(1 for row in rows if row.training_export_blocked),
        "parsed_section_counts": parsed_section_counts,
        "all_decisive_rows_cite_parsed_non_router_evidence": all_confirmed_or_challenged_cite_parsed_evidence,
        "first_principles_claim": "complete"
        if status_counts.get("REQUEST_MORE_DATA", 0) == 0
        and all_confirmed_or_challenged_cite_parsed_evidence
        and _all_required_sections_parsed(rows)
        else "partial",
    }
```

Implement `write_adjudication_artifacts()`:

- write JSONL packets sorted by `sample_id`;
- write JSONL adjudications sorted by `sample_id`;
- write missing evidence JSONL for `REQUEST_MORE_DATA` rows;
- write `adjudication_summary.json`;
- write `adjudication_report.md` with concise table rows.

The summary must not set `first_principles_claim="complete"` merely because no row emitted `REQUEST_MORE_DATA`. It may claim complete only when every decisive row cites parsed non-router evidence and every blocker-specific required section from the First-Principles Evidence Matrix was parsed.

- [ ] **Step 5: Run report tests**

```bash
uv run pytest tests/test_agentxrd_adjudication_report.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/detrix/agentxrd/adjudication_report.py tests/test_agentxrd_adjudication_report.py
git commit -m "feat: report AgentXRD row adjudications (detrix-core-s10)"
```

## Task 6: End-to-End Verification And Landing

**Files:**
- Modify tests only if verification exposes a real contract gap.
- Bead: `detrix-core-6bn`

- [ ] **Step 1: Claim bead**

```bash
bd update detrix-core-6bn --claim --json
```

- [ ] **Step 2: Run all focused AgentXRD tests**

```bash
uv run pytest \
  tests/test_agentxrd_evidence_resolver.py \
  tests/test_agentxrd_row_evidence.py \
  tests/test_agentxrd_adjudication.py \
  tests/test_agentxrd_adjudication_cli.py \
  tests/test_agentxrd_adjudication_report.py \
  tests/test_agentxrd_failure_harness_cli.py \
  tests/test_binary20_governed_judge_cohort.py \
  -q
```

Expected: pass.

- [ ] **Step 3: Run real adjudication command**

```bash
rm -rf /tmp/detrix-agentxrd-first-principles-adjudication
uv run detrix agentxrd adjudicate-rows \
  --agentxrd-root /home/gabriel/Desktop/AgentXRD_v2 \
  --output-dir /tmp/detrix-agentxrd-first-principles-adjudication
```

Expected:

- prints `Rows adjudicated: 20`;
- emits all five adjudication artifacts;
- `adjudication_summary.json` has `row_count=20`;
- `training_export_blocked_count=20`;
- `first_principles_claim` is `complete` only if no rows are missing required evidence, all decisive rows cite parsed non-router evidence, and all blocker-specific required sections were parsed.

- [ ] **Step 4: Inspect real output**

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('/tmp/detrix-agentxrd-first-principles-adjudication')
print(json.dumps(json.loads((p / 'adjudication_summary.json').read_text()), indent=2, sort_keys=True))
print('packets', sum(1 for _ in (p / 'row_evidence_packets.jsonl').open()))
print('adjudications', sum(1 for _ in (p / 'row_adjudications.jsonl').open()))
print('missing', sum(1 for _ in (p / 'adjudication_missing_evidence.jsonl').open()))
PY
```

Expected: counts are internally consistent. Any `CHALLENGED` rows must include rationale; any missing rows must include exact missing evidence.

- [ ] **Step 5: Run quality gates**

```bash
uv run ruff check .
uv run mypy src/detrix
uv run pytest
```

Expected: pass.

- [ ] **Step 6: Dispatch verifier subagent**

Prompt:

```text
Read-only verification in /home/gabriel/Desktop/detrix-core. Review the completed implementation for docs/superpowers/plans/2026-04-28-agentxrd-first-principles-row-adjudication.md. Verify that row adjudications inspect first-principles evidence packets and do not simply restate router blocker classes. Check real /tmp/detrix-agentxrd-first-principles-adjudication artifacts if present. Return PASS/FAIL with blocking issues only.
```

- [ ] **Step 7: Close beads**

Close all completed child beads, then the epic:

```bash
bd close detrix-core-phq --reason "Completed and verified evidence resolver" --json
bd close detrix-core-uf8 --reason "Completed and verified row evidence packets" --json
bd close detrix-core-poc --reason "Completed and verified first-principles adjudicator" --json
bd close detrix-core-zy3 --reason "Completed and verified adjudication artifact wiring" --json
bd close detrix-core-s10 --reason "Completed and verified adjudication reports" --json
bd close detrix-core-6bn --reason "Completed and verified end-to-end adjudication harness" --json
bd close detrix-core-54v --reason "Implemented and verified first-principles AgentXRD row adjudication" --json
```

- [ ] **Step 8: Push beads and git**

```bash
git pull --rebase --autostash
bd dolt push
git push
git status --short --branch
```

Expected: branch is up to date with origin; only unrelated pre-existing local dirt remains.

## Done Criteria

The implementation is complete only when:

- `row_evidence_packets.jsonl` has exactly 20 rows for binary20.
- Each row packet records raw pattern, truth, candidate provenance, eligibility join, refinement, chemistry, and router evidence statuses.
- `row_adjudications.jsonl` has exactly 20 rows.
- Every adjudication is one of `CONFIRMED`, `CHALLENGED`, or `REQUEST_MORE_DATA`.
- `CONFIRMED` and `CHALLENGED` rows include concrete scientific evidence fields.
- `REQUEST_MORE_DATA` rows include exact missing files/fields.
- No adjudication enables SFT/export eligibility.
- Existing harness artifacts still emit unchanged.
- `uv run ruff check .`, `uv run mypy src/detrix`, and `uv run pytest` pass.
- Beads and git are pushed.
