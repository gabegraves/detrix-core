# AgentXRD_v2 Langfuse Reliability Pack Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to execute this plan task-by-task. Keep Langfuse advisory, AgentXRD deterministic artifacts authoritative, and no model-improvement claims without held-out replay proof.

**Status:** consensus execution plan produced on 2026-05-04 from `.omx/context/agentxrd-v2-langfuse-reliability-pack-20260504T083359Z.md` plus read-only subagent repository/DB inspection.

**Goal:** Turn AgentXRD_v2 deterministic artifacts plus Mission Control Langfuse process traces into a repeatable Detrix reliability pack that shows what happened, why rows were accepted/blocked/abstained, what next actions are policy-allowed, and whether any proposed transition is admissible for training, replay, or promotion.

**Product outcome for YC:** A demoable AgentXRD reliability pack where Detrix is not another trace viewer: Langfuse shows process traces; Detrix admits or rejects state transitions under deterministic scientific evidence, provenance, replay, and promotion gates.

---

## Non-Negotiable Boundaries

- AgentXRD_v2 deterministic artifacts remain the authority for ACCEPT, SET, REQUEST_MORE_DATA, training route, and promotion.
- Mission Control Langfuse traces are advisory/process evidence only. They may explain failures, missing joins, and operator/session context; they cannot become scientific labels or training positives by themselves.
- `support_only=true`, `accept_eligible=false`, truth-blocked rows, provisional rows, and `must_not_promote=true` rows cannot become SFT/DPO/GRPO positives.
- Missing required scientific evidence yields `REQUEST_MORE_DATA`, never promotion.
- Qwen/local-model outputs are proposer/shadow signals only until held-out replay proves improvement without precision regression.
- The pack must be product-shaped and repeatable, not bespoke consulting prose.

---

## Current Evidence Baseline

### Existing Detrix surfaces

- `detrix agentxrd build-harness-evidence` exists in `src/detrix/cli/main.py`.
- It already emits:
  - `failure_patterns.jsonl`
  - `failure_pattern_summary.json`
  - `raw_langfuse_traces.jsonl`
  - `normalized_observations.jsonl`
  - `trace_to_agentxrd_packet_map.jsonl`
  - `governed_next_actions.jsonl`
  - `provenance_dag.jsonl`
  - `promotion_packet.json`
  - `drift_replay_report.json`
- Existing tests cover the CLI artifact contract, Langfuse advisory import, promotion fail-closed behavior, next actions, provenance, drift replay, and judge/advisory boundaries.

### Mission Control Langfuse reality check

Read-only inspection of `/home/gabriel/.mission-control/data.db` found:

- `langfuse_traces` total rows: 5,161.
- Current `AgentXRD_v2` cached rows: 100.
- Current `AgentXRD_v2` rows with `metadata.sample_id` or `metadata.agentxrd_sample_id`: 0.

Therefore the current Langfuse cache is useful as process-failure evidence and demo context, but not yet sample-joinable scientific evidence. The pack must expose this honestly as `unjoinable` / `advisory_only`, not hide it.

### Existing gap

Detrix has the artifact generator, but not a polished reliability-pack surface that a user or Mission Control UI can consume atomically:

- No canonical `reliability_pack.json` joining summary, rows, admissions, next actions, replay, promotion, and provenance references.
- No `agentxrd show-pack`, `show-next-actions`, or `replay-report` CLI inspection commands.
- Row-level evidence authority is implicit in several artifacts rather than explicit in a single packet.
- Mission Control UI/demo has no stable contract for ingesting this pack directly.

---

## Architecture

### Layer split

1. **AgentXRD_v2 owns science/runtime**
   - PXRD evidence, candidate provenance, support-only flags, accept eligibility, truth/provisional status, router decisions, deterministic gates, and first-principles row evidence.

2. **Detrix owns governance/admission/promotion**
   - Reliability pack schema, advisory trace import, failure pattern corpus, allowed next actions, admission decisions, provenance DAG, promotion packet, replay report, and training/export eligibility.

3. **Mission Control owns readback/operations**
   - Trace browsing, run/session context, demo UI cards, and operator-visible reliability pack rendering. Mission Control does not override Detrix admission decisions.

### Evidence authority model

Every row in the reliability pack should carry:

```json
{
  "evidence_authority": {
    "deterministic_agentxrd": true,
    "langfuse_process_trace": false,
    "llm_or_qwen_judge": false
  },
  "langfuse_join_status": "joined | unjoinable_cache_summary | missing",
  "admission_decision": "ACCEPT | SET | REQUEST_MORE_DATA | EVAL_ONLY | HARD_STOP",
  "training_route": "sft_positive | dpo_candidate | eval_only | excluded",
  "promotion_allowed": false,
  "promotion_block_reasons": []
}
```

### Pack artifact contract

Add a canonical artifact:

- `reliability_pack.json`

Minimum shape:

```json
{
  "schema_version": "agentxrd_reliability_pack_v0.1",
  "generated_at": "ISO-8601",
  "domain": "AgentXRD_v2",
  "pack_inputs": {"binary20_artifact": "...", "mission_control_db": "..."},
  "evidence_authority": {
    "deterministic_agentxrd_authoritative": true,
    "langfuse_advisory_only": true,
    "model_proposals_advisory_only": true
  },
  "summary": {
    "agentxrd_row_count": 20,
    "failure_pattern_row_count": 120,
    "langfuse_observation_count": 100,
    "joinable_langfuse_trace_count": 0,
    "unjoinable_langfuse_trace_count": 100,
    "wrong_accept_count": 0,
    "sft_positive_count": 0,
    "promotion_allowed": false
  },
  "rows": [],
  "failure_pattern_summary_ref": "failure_pattern_summary.json",
  "next_actions_ref": "governed_next_actions.jsonl",
  "provenance_ref": "provenance_dag.jsonl",
  "promotion_packet_ref": "promotion_packet.json",
  "drift_replay_ref": "drift_replay_report.json"
}
```

---

## Implementation Tasks

### Task 1 — Add reliability pack schema and writer

**Bead:** create/claim a child of `detrix-core-vyv` when executing.

**Files:**

- Create `src/detrix/agentxrd/reliability_pack.py`
- Extend `src/detrix/cli/main.py`
- Extend `tests/test_agentxrd_failure_harness_cli.py`
- Add `tests/test_agentxrd_reliability_pack.py`

**Requirements:**

- Build `AgentXRDReliabilityPack` and `AgentXRDReliabilityPackRow` Pydantic schemas.
- After `build-harness-evidence`, write `reliability_pack.json` alongside existing artifacts.
- Summarize counts without ambiguity:
  - `agentxrd_row_count`: deterministic AgentXRD sample rows only.
  - `failure_pattern_row_count`: all failure-pattern rows, including unjoinable advisory Langfuse rows.
  - `langfuse_observation_count`, `joinable_langfuse_trace_count`, and `unjoinable_langfuse_trace_count`.
  - blocker counts, promotion status, replay status, and safety blockers.
- Preserve existing output filenames and behavior.
- Do not use Langfuse observations to change deterministic export labels.

**Acceptance:**

- CLI writes all previous files plus `reliability_pack.json`.
- Pack count fields map unambiguously to underlying artifacts: `agentxrd_row_count` from deterministic packet rows, `failure_pattern_row_count` from `failure_pattern_summary.row_count`, and Langfuse joinability from normalized observations/failure summary.
- Pack promotion and replay fields match `promotion_packet.json` and `drift_replay_report.json`.
- Pack declares deterministic AgentXRD authority and Langfuse advisory-only semantics.

### Task 2 — Make Langfuse joinability explicit

**Files:**

- Modify `src/detrix/agentxrd/langfuse_importer.py`
- Modify `src/detrix/agentxrd/failure_patterns.py`
- Extend `tests/test_agentxrd_langfuse_importer.py`
- Extend `tests/test_agentxrd_failure_patterns.py`

**Requirements:**

- Add explicit counts for `joinable_trace_count`, `unjoinable_trace_count`, and missing join-key reasons to the importer report or failure summary.
- Preserve all Langfuse rows as advisory evidence.
- Include `langfuse_join_status` and `advisory_only=true` in pack rows where applicable.
- For current Mission Control cache reality, show that `AgentXRD_v2` traces are process evidence until joined to row artifacts.

**Acceptance:**

- Synthetic joined and unjoinable traces are both tested.
- Unjoinable traces remain `eval_only` and cannot affect `sft_positive_count`.
- Current no-join-key condition is represented as an explicit demo-safe status, not hidden.

### Task 3 — Add CLI inspection commands

**Files:**

- Modify `src/detrix/cli/main.py`
- Add/extend `tests/test_agentxrd_failure_harness_cli.py`

**Commands:**

- `detrix agentxrd show-pack <output-dir>`
- `detrix agentxrd show-next-actions <output-dir> [--limit N]`
- `detrix agentxrd replay-report <output-dir> [--format text|json|md]`

**Requirements:**

- `show-pack` prints row count, Langfuse joinability, promotion allowed/blocked, top blocker classes, and safety invariants.
- `show-next-actions` prints sample id, blocker class, action type, allowed commands, kill criteria, and expected evidence delta.
- `replay-report` prints before/after metrics, deltas, release block status, and block reasons.
- Commands fail closed with clear messages when required artifacts are missing.

**Acceptance:**

- CLI tests cover success and missing-artifact failure.
- Text output is concise enough for terminal/YC demo use.
- JSON output is parseable and stable.
- Markdown output includes the same release-block/promotion facts and referenced-artifact links needed for docs/Mission Control readback.

### Task 4 — Expose admission decisions and safety reasons per row

**Files:**

- Modify `src/detrix/agentxrd/reliability_pack.py`
- Optionally modify `src/detrix/agentxrd/failure_patterns.py`
- Add tests in `tests/test_agentxrd_reliability_pack.py`

**Requirements:**

- For each row, derive an explicit admission decision and ordered reason chain from deterministic fields.
- Use this precedence when multiple blockers apply:

| Precedence | Condition | Admission decision | Required leading reason |
| --- | --- | --- | --- |
| 1 | wrong-accept risk or deterministic safety violation | `HARD_STOP` | `wrong_accept_risk` or exact safety violation |
| 2 | `support_only=true`, `accept_eligible=false`, truth-blocked, provisional, or `must_not_promote=true` | `EVAL_ONLY` | the matching promotion boundary |
| 3 | missing required scientific evidence or unjoinable scientific packet | `REQUEST_MORE_DATA` | `missing_required_evidence` |
| 4 | deterministic export label is not training-positive | `EVAL_ONLY` | `not_training_positive` |
| 5 | deterministic row is accepted and training-positive with replay-safe promotion packet | `ACCEPT` or `SET` | `deterministic_gate_passed` |

- Preserve all applicable secondary reasons after the leading reason for auditability.
- Challenged or unjoinable Langfuse traces must not imply ACCEPT; they route to eval-only/process evidence or REQUEST_MORE_DATA.

**Acceptance:**

- Rows with `support_only=true` are blocked from training positive.
- Rows with `accept_eligible=false` are blocked from training positive.
- Truth-blocked/provisional rows are blocked from training positive.
- Missing row evidence can route to `REQUEST_MORE_DATA` without promotion.

### Task 5 — Define Mission Control UI/demo contract

**Files:**

- Create `docs/agentxrd-v2-langfuse-reliability-pack-ui-contract-20260504.md`
- Optionally create a JSON fixture under `tests/fixtures/` if useful.

**Requirements:**

- Document how Mission Control should read `reliability_pack.json` plus referenced artifacts.
- Define UI cards:
  - Pack summary
  - Langfuse joinability
  - Failure patterns
  - Next allowed actions
  - Admission/promotion
  - Replay/promotion safety
  - Provenance drilldown
- Explicitly state that Mission Control readback cannot override deterministic Detrix decisions.

**Acceptance:**

- Contract includes file paths, schema names, required fields, empty-state behavior, and demo-safe copy.
- Copy uses the approved Detrix positioning:
  - “Your agents work in demos. Detrix makes them work in production.”
  - “Langfuse shows what happened. Detrix decides what is safe to learn from.”

### Task 6 — Validate end-to-end pack against synthetic fixtures and optional real seed artifacts

**Files:**

- Extend tests and/or add `tests/test_agentxrd_reliability_pack_e2e.py`
- Add committed synthetic fixture data under `tests/fixtures/agentxrd_reliability_pack/` for portable unit/CLI tests.
- Optionally add a documented smoke command to `docs/agentxrd-v2-langfuse-reliability-pack-ui-contract-20260504.md`

**Portable test rule:**

Unit and CLI tests must use committed synthetic fixtures only. Absolute paths under `/home/gabriel/Desktop/AgentXRD_v2` and `/home/gabriel/.mission-control/data.db` are allowed only in an optional smoke test or documented manual command that skips cleanly when paths are missing.

**Optional local smoke command:**

```bash
uv run detrix agentxrd build-harness-evidence \
  --binary20-artifact /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/detrix_run_artifact.json \
  --row-packets /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/row_packets.jsonl \
  --trace-packet-map /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/binary20_governed_judge_cohort_v0/trace_to_pxrd_packet_map.jsonl \
  --router-decisions /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/router_decisions.jsonl \
  --router-summary /home/gabriel/Desktop/AgentXRD_v2/outputs/diagnostics/pxrd_failure_router_v0/summary.json \
  --mission-control-db /home/gabriel/.mission-control/data.db \
  --langfuse-project AgentXRD_v2 \
  --output-dir /tmp/detrix-agentxrd-reliability-pack
```

Then:

```bash
uv run detrix agentxrd show-pack /tmp/detrix-agentxrd-reliability-pack
uv run detrix agentxrd show-next-actions /tmp/detrix-agentxrd-reliability-pack --limit 5
uv run detrix agentxrd replay-report /tmp/detrix-agentxrd-reliability-pack --format text
```

**Acceptance:**

- Existing artifact contract still passes on committed fixtures.
- Pack is generated with deterministic authority declarations.
- Promotion remains blocked when there are zero SFT-positive rows.
- Synthetic joined/unjoinable traces are represented with separate joinability counts.
- Optional local smoke retains current Langfuse traces as advisory/process evidence and reports them as unjoinable unless sample ids are present.

---

## Review Gates

After each implementation task:

1. **Spec compliance review**
   - Does the diff satisfy the task exactly?
   - Did it preserve advisory vs deterministic authority?
   - Did it avoid extra platform abstraction?

2. **Code quality review**
   - Are schemas minimal and stable?
   - Are CLI errors fail-closed and readable?
   - Are tests focused and not brittle against live external state?

3. **Final verification**
   - `uv run ruff check .`
   - `uv run mypy src/detrix`
   - `uv run pytest`
   - Real smoke command against AgentXRD_v2 seed artifacts if those paths exist.

---

## Demo Script Narrative

1. Start with AgentXRD_v2 seed artifacts: 20 rows, 3 SET / 17 UNKNOWN, no wrong accepts.
2. Import Mission Control Langfuse cache: process traces retained, but no sample join keys today.
3. Detrix emits failure patterns and explicit unjoinable trace evidence instead of pretending traces are labels.
4. Detrix proposes allowed next actions with kill criteria.
5. Detrix writes a promotion packet and replay report; promotion remains blocked because no SFT-positive rows are safe yet.
6. Mission Control can render the pack: Langfuse shows what happened; Detrix decides what is safe to learn from.

---

## Out of Scope

- Live Langfuse API ingestion beyond cache import unless separately planned.
- Qwen/local-model inference, training, or claimed improvement.
- Refactoring AgentXRD_v2 gates into action constraints.
- Mission Control UI implementation in this Detrix-core plan.
- Broad domain-pack factory abstraction.

---

## Remaining Unknowns

- Whether future Mission Control traces will include `sample_id` / `agentxrd_sample_id` join keys by default.
- Whether Mission Control UI should ingest `reliability_pack.json` directly or through Detrix audit collector tables first.
- Which subset of rows should be used for the shortest live YC demo once `reliability_pack.json` exists.
