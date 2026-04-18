# Detrix V1: Narrow Governance Slice for AgentXRD_v2

**Date:** 2026-04-18
**Status:** SPEC — approved design, pending implementation plan
**Scope:** Narrow control-plane contract that hardens AXV2's frozen benchmark and proves the RLVR improvement loop. NOT a platform build.

---

## Problem

AgentXRD_v2 has 7 governance gates wired into its pipeline, producing structured GateRecord
and TerminalRoute objects. But:

1. **Traces lack admission classification.** Provenance signals exist (instrument_profile_confidence,
   Pawley-fallback, benchmark provenance) but are not promoted to explicit admission classes.
   Training on fallback/provisional traces would self-poison the improvement loop.

2. **No training bridge.** Governance-scored traces are persisted to governance_report.json but
   never flow into SFT/DPO/GRPO training data. The improvement loop doesn't exist yet.

3. **Version tuples are coarse.** Gate config changes drove AXV2 benchmark coverage from 31 to 0.
   GovernedTrajectory records evaluator versions but not the full policy tuple (config hashes,
   bundle IDs, phase-map/index, environment metadata).

4. **No RLVR training on the local model.** Qwen 3.6 sits on Blackwell unused. The whole point
   of open-source local models is that you can fine-tune them with domain-verified rewards.

## Constraints

- AXV2's recovery policy (ADR-0004) bans generic platform work during recovery.
- The frozen benchmark is the trust anchor. Nothing ships that could degrade it.
- "Detrix governance" means a narrow control-plane contract, not a new platform surface.
- ParabolaHunter is a later domain pack, not a prerequisite.
- pi-mono agent loop fork is V2, after V1 proves itself on AXV2.

## Non-Goals (V2+)

- Pi-mono TypeScript fork / hybrid TS+Python architecture
- Generic domain pack loading system
- Framework adapters (LangGraph, CrewAI, raw Python)
- Meta-Harness proposer (LLM optimizes gate config)
- ParabolaHunter integration
- New pipeline runtime / agent loop
- Mission-control dashboard panels

---

## Architecture

V1 is 5 components built into AXV2's existing pipeline and detrix-core's existing Python modules.

```
AXV2 PIPELINE (existing, unchanged)
    │
    │ produces
    ▼
GateRecords + TerminalRoutes (existing)
    │
    │ NEW: promote provenance signals
    ▼
┌─────────────────────────────────────────────────────┐
│  1. TRACE ADMISSION CONTRACT                         │
│     clean | provisional | fallback                   │
│     Derived from existing AXV2 signals               │
│     Training bridge rejects non-clean by contract    │
├─────────────────────────────────────────────────────┤
│  2. GOVERNED TRAJECTORY + FULL VERSION TUPLES        │
│     GovernedTrajectory with policy_hash:             │
│       gate config hashes + bundle/dataset hash +     │
│       phase-map/index IDs + model alias +            │
│       environment metadata                           │
│     Append-only evidence log (single-writer SQLite)  │
├─────────────────────────────────────────────────────┤
│  3. SKILL EVOLVER (fast lane, gradient-free)         │
│     Rejection traces → LLM analyzes WHY →            │
│     markdown skills → prompt injection               │
│     Effect: 7-32% improvement, zero GPU              │
├─────────────────────────────────────────────────────┤
│  4. TRAINING BRIDGE (deep lane prerequisite)         │
│     GovernedTrajectory (clean only) → HF Dataset     │
│     SFT: gate-passed traces                          │
│     DPO: (gate-passed, gate-rejected) pairs          │
│     GRPO: completion + governance composite reward    │
├─────────────────────────────────────────────────────┤
│  5. RLVR TRAINING LOOP                               │
│     TRL GRPOTrainer + governance reward function     │
│     Qwen 3.6 via vLLM on Blackwell                  │
│     Shadow eval through same gates                   │
│     Promote only if challenger beats incumbent       │
│     Support-query versioning: flush on version bump  │
└─────────────────────────────────────────────────────┘
```

---

## Component 1: Trace Admission Contract

### What exists in AXV2 today

| Signal | Location | Values |
|---|---|---|
| `instrument_profile_confidence` | metrology_guard.py:72 | matched \| fallback \| missing |
| Pawley-fallback flag | quantify.py handler | boolean on RefinementResult |
| Default-fallback instrument forced UNKNOWN | quantify.py:1351 | verdict override |
| Benchmark provenance | pilot_benchmark.py:560 | persisted per run |
| Family-backed proxy labels | MASTER.md references | provisional flag |

### What V1 adds

A `TraceAdmission` enum and classification function that reads existing AXV2 signals:

```python
class TraceAdmission(str, Enum):
    CLEAN = "clean"             # All provenance verified. Safe for training.
    PROVISIONAL = "provisional" # Some signals unverified (family-backed labels,
                                # unmatched instrument). Safe for skill evolver,
                                # NOT safe for RLVR weight updates.
    FALLBACK = "fallback"       # Fallback pricing, default instrument, Pawley-only.
                                # QUARANTINED. Not used for any training.

def classify_trace_admission(
    governance_report: dict,
    metrology_result: dict,
    refinement_result: dict,
) -> TraceAdmission:
    """Derive admission class from existing AXV2 provenance signals."""

    # Hard quarantine: any fallback signal
    if metrology_result.get("instrument_profile_confidence") == "missing":
        return TraceAdmission.FALLBACK
    if refinement_result.get("used_pawley_fallback", False):
        return TraceAdmission.FALLBACK
    if metrology_result.get("instrument_profile_confidence") == "fallback":
        return TraceAdmission.FALLBACK

    # Provisional: matched but not fully verified
    if metrology_result.get("status") == "caution":
        return TraceAdmission.PROVISIONAL

    # Check for provisional labels (family-backed proxies)
    for gate_record in governance_report.get("gate_history", []):
        if "family_backed" in gate_record.get("reason_codes", []):
            return TraceAdmission.PROVISIONAL

    return TraceAdmission.CLEAN
```

### Contract enforcement

| Consumer | CLEAN | PROVISIONAL | FALLBACK |
|---|---|---|---|
| Skill evolver (fast lane) | Yes | Yes | No |
| SFT training | Yes | No | No |
| DPO training | Yes (chosen side) | No | No |
| GRPO training | Yes | No | No |
| Audit/evidence log | Yes | Yes | Yes |
| Langfuse traces | Yes | Yes | Yes |

**Fail-closed:** If classification cannot be determined (missing fields, parse error), default to FALLBACK. Never default to CLEAN.

---

## Component 2: GovernedTrajectory + Full Version Tuples

### Schema

```python
@dataclass
class PolicyTuple:
    """Full versioning of everything that affects trace meaning."""
    gate_config_hashes: dict[str, str]    # gate_id → SHA256 of threshold config
    evaluator_versions: dict[str, str]    # gate_id → semantic version
    dataset_bundle_hash: str              # SHA256 of input data bundle
    phase_map_version: str                # crystal structure DB version
    model_alias: str                      # e.g., "qwen3.6-xrd-v3"
    model_version: str                    # resolved from alias
    environment: str                      # e.g., "blackwell-local" | "benchmark-ci"
    pipeline_commit: str                  # git SHA of AXV2 at run time

    @property
    def policy_hash(self) -> str:
        """Single hash representing the full policy state."""
        # SHA256 of all fields concatenated
        ...

@dataclass
class GovernedTrajectory:
    schema_version: int = 2

    # Identity
    trajectory_id: str                    # UUID
    run_id: str                           # links to AXV2 pipeline run
    domain: str = "xrd"

    # Admission
    admission: TraceAdmission             # clean | provisional | fallback

    # Steps + verdicts
    steps: list[dict]                     # ordered (tool_call, tool_result) pairs
    verdicts: list[dict]                  # VerdictContract.to_dict() from all gates
    terminal_verdict: str                 # ACCEPT | SET | UNKNOWN | REQUEST_MORE_DATA

    # Scores
    governance_score: float               # composite (0-1)
    domain_eval_score: float              # domain-specific (0-1)
    gate_pass_rate: float                 # fraction of gates passed

    # Rejection classification
    rejection_type: str | None = None     # "input_quality" | "output_quality" | None

    # Full provenance (Codex finding #3)
    policy: PolicyTuple                   # full version tuple

    # Timestamps
    started_at: datetime
    finished_at: datetime
```

### Evidence log

Single-writer, append-only SQLite table at `.detrix/evidence.db`:

```sql
CREATE TABLE evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trajectory_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    admission TEXT NOT NULL CHECK(admission IN ('clean', 'provisional', 'fallback')),
    policy_hash TEXT NOT NULL,
    governance_score REAL,
    domain_eval_score REAL,
    gate_pass_rate REAL,
    terminal_verdict TEXT NOT NULL,
    rejection_type TEXT,
    verdicts_json TEXT NOT NULL,       -- JSON array of verdict dicts
    steps_json TEXT NOT NULL,          -- JSON array of step dicts
    policy_json TEXT NOT NULL,         -- JSON serialized PolicyTuple
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Immutability: no UPDATE or DELETE permitted by application code
    -- Enforced by: no UPDATE/DELETE methods on the writer class
);

CREATE INDEX idx_evidence_admission ON evidence(admission);
CREATE INDEX idx_evidence_policy_hash ON evidence(policy_hash);
CREATE INDEX idx_evidence_run_id ON evidence(run_id);
```

**Single-writer rule (Codex finding #4):** Only the Python evidence writer appends rows.
No other process reads or writes this table during training. Consumers read via a separate
read-only connection. No bidirectional bridge.

---

## Component 3: Skill Evolver (Fast Lane)

MetaClaw port. Analyzes gate rejections from GovernedTrajectories and synthesizes behavioral
skills as markdown files.

### Input
- GovernedTrajectories with `admission != FALLBACK` and `terminal_verdict != ACCEPT`
- Gate verdicts with evidence (WHY the gate rejected)

### Process
1. Compress each failure: last 600 chars of step context + first 500 chars of output
2. Include gate verdicts with physics evidence (e.g., "SNR was 2.1, threshold is 3.0")
3. LLM generates skill JSON. Use Claude (via Claude Code subagent) for skill
   extraction — this is a meta-reasoning task that benefits from frontier capability.
   Qwen 3.6 is the agent being improved, not the improver. Skill extraction runs
   infrequently (after batches of failures, not per-trace) so cost is negligible:
   - name, description, content (6-15 lines markdown), category
4. Deduplicate against existing skills
5. Version-stamp skills (generation index g)

### Output
- Markdown skill files at `.detrix/skills/`
- Injected into Qwen 3.6's system prompt on next run
- Immediate effect, zero GPU cost

### Support-query versioning
When skills update (generation g → g+1), flush ALL trace buffer entries with version <= g.
Stale traces scored against old behavioral expectations produce incorrect gradient signal.

---

## Component 4: Training Bridge

Converts provenance-clean GovernedTrajectories into HuggingFace Dataset format.

### Admission filter (Codex finding #1)

```python
def filter_for_training(trajectories: list[GovernedTrajectory]) -> list[GovernedTrajectory]:
    """Only provenance-clean traces enter the training pipeline."""
    return [t for t in trajectories if t.admission == TraceAdmission.CLEAN]
```

**No exceptions.** PROVISIONAL traces feed the skill evolver but never touch model weights.
FALLBACK traces are audit-only.

### Export formats

**SFT:** Traces where `terminal_verdict == "ACCEPT"` and `admission == "CLEAN"`:
```python
{"prompt": step_input, "completion": step_output}
```

**DPO:** Paired traces for the same input where one passed and one failed:
```python
{"prompt": shared_input, "chosen": accepted_output, "rejected": rejected_output}
```
Rejected trace must have `rejection_type == "output_quality"` (model was wrong, not bad input).

**GRPO:** All clean traces with composite reward:
```python
{
    "prompt": step_input,
    "completion": step_output,
    "governance_score": 0.73,
    "gate_verdicts": ["accept", "accept", "reject", "accept"],
    "domain_eval_score": 0.81,
}
```

### Quality filters
- Minimum trace length: discard steps with < 50 tokens
- Score distribution check: verify reward variance > 0 in batch
- Version partition: separate by policy_hash (never mix policy versions in one batch)
- Buffer management: rolling 30-day window, flush on ANY policy version change

---

## Component 5: RLVR Training Loop

### Reward function

```python
def governance_reward(
    completions,
    governance_score,      # Tier 1 mechanical (0-1)
    gate_verdicts,         # list of pass/fail per gate
    domain_eval_score,     # domain evaluator (0-1)
    **kwargs,
) -> list[float]:
    rewards = []
    for gs, gv, des in zip(governance_score, gate_verdicts, domain_eval_score):
        gate_bonus = sum(1 for v in gv if v == "pass") / max(len(gv), 1)
        reward = 0.3 * gs + 0.2 * gate_bonus + 0.5 * des
        rewards.append(reward)
    return rewards
```

This IS RLVR:
- Environment = AXV2 pipeline with governance gates
- Action = model's outputs at each step
- Reward = domain physics evaluation (deterministic, verifiable)
- The model's WEIGHTS get better, not just prompts

### Training config

```
Model:          Qwen 3.6 (7B-class)
Serving:        vLLM on Blackwell (GPU 1/2, 98GB)
Training:       TRL GRPOTrainer on 3x 3090 (FSDP)
LoRA:           r=32 (no reference model VRAM cost)
KL:             beta=0.0 (current best practice)
scale_rewards:  False (DrGRPO, no std normalization)
Liger loss:     True (40% memory reduction)
Importance sampling: True (vLLM server mode correction)
```

### OMLS scheduler (MetaClaw port)

Three signals gate training:
1. Overnight window (23:00-07:00 ET)
2. System idle (no active AXV2 pipeline runs)
3. GPU idle (vLLM not serving inference)

Supports pause/resume across fragmented idle windows.

### Model promotion

**Shadow evaluation (mandatory before promotion):**
1. Run challenger model on N held-out benchmark cases
2. Both challenger and incumbent go through identical gates
3. Compare: verdict pass rates, governance scores, domain eval scores
4. Require: challenger pass rate >= incumbent (no regression)

**Regression gate (Codex finding #3):**
Before ANY threshold or reward-weight change:
- Re-run held-out golden set (50-100 pre-labeled traces)
- Compare score distributions (KL divergence)
- If flip rate > 10% (traces that previously passed now fail), BLOCK the change

**Track-and-Stop bandit:**
- Best-arm identification (find winner fast), not regret minimization
- GLRT-based stopping with anytime-valid inference
- Auto-stop when confidence exceeds threshold

**Alias deployment:**
- `@active` — currently serving
- `@champion` — best performing (promoted after shadow eval)
- `@staging` — under shadow evaluation
- `@previous` — auto-set when @active changes (instant rollback)

---

## Observability

### Langfuse integration

- Every AXV2 pipeline run → Langfuse trace
- Every gate verdict → Langfuse span with score
- Physics evidence attached as evaluation metadata
- Governance composite score as Langfuse score
- Admission class tagged on trace

### CLI inspection

```bash
detrix trace <run_id>          # Full governed trace with verdicts
detrix traces --admission clean # List clean traces
detrix scores --since 7d       # Governance scores over time
detrix training --status        # Training bridge status + buffer size
```

---

## Integration with AXV2

### What changes in AXV2 (minimal, targeted)

1. **`_write_governance_report()` extended** — after writing governance_report.json, also
   call detrix trace admission classifier and write GovernedTrajectory to evidence.db.
   ~30 lines added to pipeline.py.

2. **Metrology handler enriched** — ensure `instrument_profile_confidence` is persisted
   in GateRecord evidence dict (may already be, verify). ~5 lines.

3. **Refinement handler enriched** — ensure `used_pawley_fallback` is persisted in
   GateRecord evidence dict. ~5 lines.

4. **No pipeline flow changes.** Gates stay where they are. Handler chain unchanged.
   AXV2's pipeline is the execution environment. Detrix is the evidence + training layer.

### What stays in detrix-core

- TraceAdmission enum + classifier
- GovernedTrajectory + PolicyTuple schemas
- Evidence writer (append-only SQLite)
- Skill evolver
- Training bridge
- GRPO training wrapper
- OMLS scheduler
- Model promotion (shadow eval + bandit)
- CLI commands

---

## Build Sequence

```
Day 1:  TraceAdmission enum + classifier + PolicyTuple + GovernedTrajectory schema
        Evidence writer (append-only SQLite)
        Wire into AXV2's _write_governance_report()
        PROOF: "AXV2 benchmark run produces GovernedTrajectories in evidence.db
               with correct admission classification"

Day 2:  Skill evolver (MetaClaw port)
        Wire to AXV2 rejection traces
        PROOF: "Skills extracted from gate rejections, injected into Qwen 3.6 prompt"

Day 3:  Training bridge (GovernedTrajectory → HF Dataset)
        Quality filters + version partitioning + admission enforcement
        PROOF: "N clean traces exported to HF Dataset format, zero fallback traces"

Day 4:  RLVR training loop (TRL GRPOTrainer + governance reward)
        vLLM serving Qwen 3.6 on Blackwell
        OMLS scheduler
        PROOF: "Overnight GRPO run completed on clean XRD traces"

Day 5:  Model promotion (shadow eval + regression gate + bandit)
        Alias deployment
        CLI commands (detrix trace, detrix scores, detrix training)
        PROOF: "Promoted Qwen 3.6 LoRA verified better by physics gates"
```

### Demo sentence (end of Day 5)

"We ran Qwen 3.6 on 50 XRD scans through AXV2's 7 governance gates. 34 passed as CLEAN,
9 were PROVISIONAL (caution-flagged), 7 were FALLBACK (quarantined). The skill evolver
extracted 4 behavioral rules from the 16 rejection traces. After one overnight GRPO run
on the 34 clean traces, the challenger model improved governance score from 0.52 to 0.68.
Shadow evaluation confirmed no regression on the held-out golden set. Promoted to @champion.
Every trace carries a full policy tuple for reproducibility. No fallback data touched the
model weights."

---

## V2 Roadmap (after V1 hardens the anchor)

| Phase | What | When |
|---|---|---|
| V2a | Pi-mono agent loop fork (TS/Python hybrid) | After V1 demo |
| V2b | Generic domain pack loading system | After V2a |
| V2c | ParabolaHunter as second domain pack | After V2b |
| V2d | Framework adapters (LangGraph, CrewAI) | After V2c |
| V2e | Meta-Harness proposer | After improvement loop has 30+ days of data |

---

## Sources

- AgentXRD_v2 ADR-0004: execution lane and governance policy
- AgentXRD_v2 spin-breaker PRD: recovery sequencing
- AgentXRD_v2 MASTER.md: V2 as "Detrix M2 domain pack"
- MetaClaw (2603.17187): skill evolver + OMLS + support-query versioning
- Agent-RLVR (2506.11425): SFT→DPO→GRPO phasing, dense reward superiority
- Pi-mono (badlogic/pi-mono): design patterns (V2 foundation)
- Meta-Harness (2603.28052): harness code optimization (V2e)
- TRL GRPOTrainer docs: training config
- Codex adversarial review (2026-04-18): 4 findings incorporated
