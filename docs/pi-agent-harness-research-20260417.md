# Pi Agent Harness + Meta-Harness Research — Building Detrix-Core Around It

**Date:** 2026-04-17
**Status:** Research complete. Synthesis of pi-mono, MetaClaw, Meta-Harness, Agent-RLVR.
**Scope:** How pi-mono's harness architecture informs detrix-core's build-out.

---

## Executive Summary

Pi-mono (badlogic/pi-mono) is a 36.8k-star TypeScript coding agent harness with a
clean extension-first architecture. It produces traces. It does NOT evaluate, score,
or improve them. **This is exactly the gap Detrix fills.**

The thesis: pi-mono is the exemplar of a well-designed harness that lacks governance
and self-improvement. Detrix wraps harnesses like pi-mono (and LangGraph, CrewAI, raw
Python) via adapters to add the missing layers. The papers (MetaClaw, Meta-Harness,
Agent-RLVR) provide the improvement mechanics.

**What changes for detrix-core:**

1. The adapter layer needs to target pi-mono's extension hooks as a first-class adapter
2. pi-mono's JSONL session format becomes a trace ingestion source
3. The MetaClaw dual-mechanism (skills + GRPO) is the improvement loop
4. Meta-Harness's proposer pattern is the V2 autoresearch loop (optimize governance config itself)
5. Agent-RLVR's guidance injection maps to "governance-as-dense-reward" — Detrix already has this

---

## 1. Pi-Mono Architecture (What We're Wrapping)

### 1.1 Layered Monorepo

```
pi-ai           — multi-provider LLM streaming (20+ providers)
  └── pi-agent-core — generic stateful agent loop + event system
        └── pi-coding-agent — session, tools, extensions, CLI
```

### 1.2 Core Abstractions → Detrix Mapping

| Pi Concept | Pi Implementation | Detrix Analog | Gap |
|---|---|---|---|
| `Tool` | TypeBox schema + execute() | Step function in pipeline | None — both are callable units |
| `Extension` | Plugin factory: tools + hooks + events | **Domain Pack** | Pi extensions are runtime plugins; Detrix domain packs add evaluation |
| `beforeToolCall` hook | Returns `{block: true}` to prevent execution | **Pre-gate** (GovernanceGate) | Pi hooks are advisory; Detrix gates are structural enforcement |
| `afterToolCall` hook | Can override result content/isError | **Post-gate** (GovernanceGate) | Same — pi hooks advise, Detrix gates block |
| `AgentSession` | Session-scoped orchestration | WorkflowEngine run | Pi is interactive; Detrix is batch pipeline |
| JSONL session log | Append-only tree at `~/.pi/agent/sessions/` | **Audit log** (SQLite) + GovernedTrajectory | Pi stores raw; Detrix scores + classifies |
| Skills (markdown) | Prompt injection via XML | **MetaClaw skill evolver output** | Pi consumes skills; Detrix GENERATES them from failures |
| No evaluation | Deliberate scope boundary | **The entire governance + scoring layer** | THIS IS THE GAP |
| No training | Traces uploaded to HF externally | **Improvement loop** (SFT→DPO→GRPO) | THIS IS THE GAP |

### 1.3 Pi's Extension API (The Wrapping Surface)

```typescript
export default function (pi: ExtensionAPI) {
    // Register governance gate as a tool-call interceptor
    pi.on("tool_call", async (event, ctx) => {
        // PRE-GATE: evaluate inputs before tool executes
        const verdict = await detrixGate.evaluate(event.input);
        if (verdict.decision === "reject") {
            return { block: true, reason: verdict.reason_codes.join(", ") };
        }
    });

    pi.on("tool_result", async (event, ctx) => {
        // POST-GATE: evaluate output after tool executes
        const verdict = await detrixGate.evaluate(event.result);
        if (verdict.decision === "reject") {
            event.content = `GOVERNANCE GATE REJECTED: ${verdict.reason_codes}`;
            event.isError = true;
        }
    });

    // Collect traces for improvement loop
    pi.on("turn_end", async (event, ctx) => {
        await detrixTraceCollector.record(event.messages, event.toolCalls);
    });
}
```

**Key insight:** Pi's `beforeToolCall` → `{block: true}` IS the Stripe Blueprints pattern
expressed as hooks. But hooks are opt-in and advisory. Detrix makes it structural:
the orchestrator runs gates unconditionally. The pi adapter translates between the two
paradigms.

### 1.4 Pi's Session Format (Trace Ingestion)

Pi stores sessions as JSONL trees:

```
session_id/
  ├── 0.jsonl      (root branch)
  ├── 0-1.jsonl    (branch from message 1)
  └── 0-1-5.jsonl  (branch from message 5 of branch 0-1)
```

Each line is a typed entry: `user_message`, `assistant_message` (with tool_calls),
`tool_result`, `thinking`, `compaction_summary`, `model_info`, `timestamp`.

**Detrix ingestion pipeline:**

```
Pi JSONL session → parse entries → extract (prompt, completion, tool_calls, results)
                → attach governance scores via DomainEvaluator
                → classify rejection_type (input_quality / output_quality / None)
                → emit GovernedTrajectory
                → store in SQLite + export to HF Dataset
```

This is the "training data bridge" from rl-environment-research.md — pi-mono gives us
a concrete, well-structured trace format to ingest from.

---

## 2. The Four Papers — What Each Contributes

### 2.1 MetaClaw (2603.17187) — The Improvement Loop

**Core:** ℳ = (θ, 𝒮) where θ = policy weights, 𝒮 = skill library.

**Dual mechanism:**

```
FAST (gradient-free, immediate):
  Failure trajectories → LLM skill evolver → markdown skills → prompt injection
  Effect: 7-32% improvement, zero downtime, no GPU needed

SLOW (gradient-based, deferred):
  Scored traces → GRPO with PRM → LoRA weight updates → hot-swap
  Effect: compounds on top of skills, ~2x skills-only improvement
  Runs during idle windows via OMLS scheduler
```

**What Detrix takes:**

| MetaClaw Component | Detrix Integration | Priority |
|---|---|---|
| Skill evolver | Extract skills from governance-rejected traces | HIGH — ships before training |
| OMLS scheduler | 3-signal idle detection for overnight GRPO | HIGH — enables unattended training |
| Support-query versioning | Flush trace buffer on gate/evaluator version bump | HIGH — correctness requirement |
| PRM endpoint | Governance composite score serves as PRM | MEDIUM — after basic GRPO works |
| Cloud LoRA | Not applicable — Detrix trains locally on Blackwell | SKIP |

**Critical correctness rule:** When skill library version advances g → g+1, ALL trace
buffer entries with version ≤ g are flushed immediately. Same rule applies when Detrix
governance gates change version. Without this, reward contamination silently degrades
the training loop.

### 2.2 Meta-Harness (2603.28052) — Optimizing the Harness Itself

**Core:** Instead of training model weights, search over the HARNESS CODE using an
agentic proposer (Claude Opus reading full execution traces + prior candidates).

**Architecture:**

```
OUTER LOOP (Meta-Harness):
  1. Proposer reads: all prior harness candidates + their source + eval scores + traces
     (median 82 files, up to 10M tokens per iteration)
  2. Proposes new harness code variant
  3. Evaluates on search-set tasks
  4. PUCT rule balances exploration/exploitation
  5. Repeats → converges on better harness

INNER LOOP (the harness being optimized):
  The actual agent execution — context management, retrieval, scaffolding
```

**Results:** +7.7 points text classification, +4.7 points IMO math, rank #1 TerminalBench-2.

**Detrix analog — this is the autoresearch V2 loop:**

```
OUTER LOOP (Detrix Meta-Harness):
  1. Proposer reads: governance configs, gate thresholds, reward weights,
     past GRPO training results, held-out eval scores
  2. Proposes: new reward weight composition, threshold adjustments,
     GRPO hyperparameters (lr, LoRA rank, batch size)
  3. Runs overnight GRPO with proposed config
  4. Evaluates challenger on held-out domain runs
  5. Track-and-Stop bandit decides promote/reject

INNER LOOP (what's being optimized):
  The GRPO training config + governance gate thresholds
```

**When to build this:** After the basic GRPO loop is validated (Month 2+). This is
Layer 5 of the five-layer stack.

### 2.3 Agent-RLVR (2506.11425) — Solving Sparse Rewards

**Problem:** Standard RLVR for agents fails because multi-step tasks have sparse terminal
rewards — agents almost never reach correct final states.

**Solution — guidance injection:**

```
1. Agent attempts task → fails (test assertions fail)
2. External LLM generates guidance: strategic plan + env feedback + file locations
3. Agent reattempts with guidance → succeeds
4. Training: hybrid SFT (20% correct) + DPO (guided-success vs original-failure)
```

**Why Detrix already solves this differently:**

Agent-RLVR needs guidance because the reward is only at task completion (tests pass/fail).
Detrix's governance gates produce DENSE per-step rewards throughout execution. Every gate
verdict is a reward signal, not just the final outcome. This is structurally superior:

```
Agent-RLVR:  sparse terminal reward → need guidance to bootstrap
Detrix:      dense per-step governance rewards → no guidance needed
```

The gate bonus formula already provides this:
```python
gate_bonus = sum(1 for v in gate_verdicts if v == "pass") / max(len(gate_verdicts), 1)
```

**What to take from Agent-RLVR:** The hybrid SFT+DPO training strategy. Instead of jumping
straight to GRPO, their phased approach validates: SFT on gate-passed traces first, then
DPO on (gate-passed, gate-rejected) pairs, THEN GRPO if plateau. This matches the existing
training strategy in rl-route-research.md.

### 2.4 Hermes/Atropos (Nous Research) — Microservice RL

**Architecture:** Three decoupled microservices: Environment → Trajectory API → Trainer.

**`BaseEnv` interface:**

```python
class BaseEnv:
    async def setup()           # init environment
    async def generate()        # produce (prompt, metadata) for vLLM
    async def evaluate()        # score responses → ScoredDataGroup
    async def cleanup()         # teardown
```

**Reward:** Each environment implements its own `score()` — fully domain-specific.
Algorithm-agnostic: PPO, DPO, GRPO all supported via trainer plugins.

**Detrix mapping:**

| Atropos Concept | Detrix Analog |
|---|---|
| `BaseEnv` | DomainEvaluator + GovernanceGate |
| `generate()` | Pipeline step execution |
| `evaluate()` | Gate.evaluate() → VerdictContract |
| `ScoredDataGroup` | GovernedTrajectory batch |
| Trajectory API | Training data bridge |
| Trainer | TRL GRPOTrainer |

**When to adopt Atropos pattern:** V2, when multiple domain packs need to simultaneously
contribute RL training signal. At current scale (single domain, 4 GPUs), TRL GRPOTrainer
with governance score as reward function is sufficient.

---

## 3. Architecture: Detrix-Core Built Around Pi-Style Harnesses

### 3.1 The Five-Layer Stack (Revised with Pi Adapter)

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: META-HARNESS LOOP (V2)                                │
│  LLM proposer optimizes governance config + GRPO hyperparams    │
│  Reads: execution traces + eval scores + prior configs          │
│  Pattern: Meta-Harness (Stanford 2603.28052)                    │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: IMPROVEMENT LOOP                                      │
│  Skills:  Failure trajectories → skill evolver → prompt inject  │
│  Training: SFT → DPO → GRPO via TRL on scored traces           │
│  Schedule: OMLS scheduler (overnight, idle-detect, pause/resume)│
│  Promote:  Track-and-Stop bandit (TensorZero)                   │
│  Pattern: MetaClaw dual-mechanism (2603.17187)                  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: SESSION SCORING                                       │
│  Tier 1: Deterministic per-step (mechanical grader)             │
│  Tier 2: LLM-as-judge per-session (advisory only)              │
│  Output: governance_score + gate_verdicts + domain_eval_score   │
│  → GovernedTrajectory (training-ready format)                   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: GOVERNANCE RAILS (Stripe Blueprints)                  │
│  Pre/post gates on every agentic phase                          │
│  Deterministic-first: physics → structure → LLM → human        │
│  VerdictContract persisted to audit log                         │
│  Gates block, not advise. Orchestrator runs them unconditionally │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: HARNESS ADAPTERS                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Pi Extension  │ │ LangGraph    │ │ Raw Python / CrewAI      │ │
│  │ beforeTool →  │ │ Conditional  │ │ Decorator / context mgr  │ │
│  │ gate.evaluate │ │ edge → gate  │ │ → gate.evaluate          │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
│  Trace ingestion: JSONL / LangSmith / custom → GovernedTrajectory│
└─────────────────────────────────────────────────────────────────┘

     ↕ wraps ↕

┌─────────────────────────────────────────────────────────────────┐
│  EXISTING HARNESS (pi-mono, LangGraph, CrewAI, raw Python)      │
│  Agent loop + tools + sessions + provider abstraction            │
│  Produces traces. Does NOT evaluate or improve them.             │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Pi Adapter — Concrete Design

The pi adapter is a Detrix extension that plugs into pi-mono's extension system:

```
src/detrix/adapters/
├── __init__.py
├── base.py           — HarnessAdapter ABC
├── pi_adapter/
│   ├── __init__.py
│   ├── extension.ts  — pi-mono extension (TypeScript, loaded via jiti)
│   ├── bridge.py     — Python ↔ TypeScript IPC (stdin/stdout JSON-RPC)
│   ├── trace_ingester.py — JSONL session → GovernedTrajectory
│   └── gate_injector.py  — maps GovernanceGate → pi beforeToolCall/afterToolCall
├── langgraph_adapter.py  — LangGraph conditional edge adapter
└── raw_adapter.py        — context manager / decorator for raw Python
```

**HarnessAdapter ABC:**

```python
class HarnessAdapter(ABC):
    """Bridges between an external agent harness and Detrix governance."""

    @abstractmethod
    def attach(self, gates: list[GateBinding]) -> None:
        """Wire governance gates into the harness's execution loop."""
        ...

    @abstractmethod
    def collect_traces(self, session_id: str) -> list[GovernedTrajectory]:
        """Extract governed trajectories from a harness session."""
        ...

    @abstractmethod
    def inject_skills(self, skills: list[Skill]) -> None:
        """Inject MetaClaw-evolved skills into the harness's prompt."""
        ...
```

**Pi-specific adapter:**

```python
class PiAdapter(HarnessAdapter):
    """Adapter for pi-mono (badlogic/pi-mono).

    Communication: JSON-RPC over stdin/stdout with pi's RPC mode.
    Pi provides rpc-mode.ts for subprocess integration — we use that.
    """

    def attach(self, gates: list[GateBinding]) -> None:
        # Install a pi extension at .pi/extensions/detrix-governance.ts
        # Extension registers beforeToolCall/afterToolCall hooks
        # Hooks call back to Python process via JSON-RPC for gate evaluation
        ...

    def collect_traces(self, session_id: str) -> list[GovernedTrajectory]:
        # Read JSONL from ~/.pi/agent/sessions/{session_id}/
        # Parse entries: user_message, assistant_message, tool_result
        # Reconstruct (prompt, completion) pairs per turn
        # Attach governance scores from verdict log
        # Classify rejection_type
        # Emit GovernedTrajectory objects
        ...

    def inject_skills(self, skills: list[Skill]) -> None:
        # Write markdown skill files to .pi/skills/detrix/
        # Pi auto-discovers and injects into system prompt
        ...
```

### 3.3 Trace Ingestion Pipeline

```
Pi JSONL Session                    Detrix Processing
─────────────────                   ─────────────────
user_message          ──┐
assistant_message       │──→  extract (prompt, completion)
  └── tool_calls        │        per conversational turn
tool_result           ──┘
                                      │
                                      ▼
                              Run DomainEvaluators
                              on each (input, output) pair
                                      │
                                      ▼
                              Attach VerdictContracts
                              (deterministic gate scores)
                                      │
                                      ▼
                              Compute composite scores:
                              - governance_score (Tier 1)
                              - domain_eval_score (Tier 2)
                              - gate_pass_rate
                                      │
                                      ▼
                              Classify rejection_type:
                              - None → positive (SFT/DPO chosen)
                              - "output_quality" → DPO rejected
                              - "input_quality" → exclude
                                      │
                                      ▼
                              GovernedTrajectory
                              (training-ready, versioned)
```

---

## 4. Build-Out Sequence

### Phase 1: Adapter Foundation (Week 1)

**Goal:** Detrix can wrap a pi-mono session and produce GovernedTrajectories.

| Task | File | Effort | Depends |
|---|---|---|---|
| `HarnessAdapter` ABC | `src/detrix/adapters/base.py` | 2h | None |
| Pi JSONL parser | `src/detrix/adapters/pi_adapter/trace_ingester.py` | 4h | None |
| Pi extension template | `src/detrix/adapters/pi_adapter/extension.ts` | 3h | None |
| JSON-RPC bridge | `src/detrix/adapters/pi_adapter/bridge.py` | 4h | Extension |
| GovernedTrajectory schema | `src/detrix/core/trajectory.py` | 2h | governance.py |
| Integration test: ingest pi session → trajectories | `tests/test_pi_adapter.py` | 3h | All above |

**Demo:** "We ingested a pi-mono coding session (47 turns, 12 tool calls), attached
governance scores from 3 XRD gates, and exported 12 GovernedTrajectories. 9 passed
all gates (SFT candidates), 2 were output-quality rejections (DPO pairs), 1 was
input-quality (excluded)."

### Phase 2: Skill Evolver (Week 2)

**Goal:** Governance-rejected traces automatically produce behavioral skills.

| Task | File | Effort | Depends |
|---|---|---|---|
| Skill schema | `src/detrix/improvement/skills.py` | 1h | None |
| Skill evolver (LLM extracts skills from failures) | `src/detrix/improvement/skill_evolver.py` | 4h | Trajectories |
| Skill storage + retrieval | `src/detrix/improvement/skill_store.py` | 2h | Skills |
| Pi skill injection (write to .pi/skills/) | Pi adapter extension | 2h | Pi adapter |
| Version stamping on skills | Skill store | 1h | Skill store |
| Integration test: rejected trace → skill → re-run improves | `tests/test_skill_evolver.py` | 3h | All above |

**Pattern from MetaClaw:**

```python
class SkillEvolver:
    """Extract behavioral skills from failure trajectories.

    Port of MetaClaw's skill_evolver. Uses LLM to analyze WHY
    governance gates rejected traces and synthesize corrective skills.
    """

    def evolve(
        self,
        failures: list[GovernedTrajectory],
        current_skills: list[Skill],
    ) -> list[Skill]:
        # 1. Compress each failure: last 600 chars context + first 500 chars response
        # 2. Include gate verdicts with evidence (WHY it failed)
        # 3. LLM generates JSON array of new skills
        # 4. Deduplicate against current_skills
        # 5. Return new skills with version stamp
        ...
```

### Phase 3: Training Data Bridge (Week 3)

**Goal:** GovernedTrajectories export to HuggingFace Dataset format for SFT/DPO/GRPO.

| Task | File | Effort | Depends |
|---|---|---|---|
| SFT export (positive trajectories only) | `src/detrix/improvement/exporters.py` | 2h | Trajectory |
| DPO export (chosen/rejected pairs) | Same file | 2h | Trajectory |
| GRPO export (completion + composite reward) | Same file | 2h | Trajectory |
| Quality filters (min length, score variance, version partition) | Same file | 2h | Trajectory |
| Buffer management (rolling window, flush on version bump) | `src/detrix/improvement/trace_buffer.py` | 3h | Trajectory |
| Integration test: trajectories → HF Dataset → verify schema | `tests/test_exporters.py` | 2h | All above |

### Phase 4: OMLS Scheduler + Overnight Loop (Week 4)

**Goal:** Unattended overnight training with idle detection and pause/resume.

| Task | File | Effort | Depends |
|---|---|---|---|
| OMLS scheduler (3-signal idle detection) | `src/detrix/improvement/scheduler.py` | 4h | None |
| GRPO training wrapper (TRL GRPOTrainer config) | `src/detrix/improvement/grpo_trainer.py` | 4h | Exporters |
| Overnight loop (collect → train → eval → promote/reject) | `src/detrix/improvement/overnight.py` | 4h | Scheduler + trainer |
| Pause/resume checkpointing | Scheduler | 2h | Scheduler |
| Integration test: mock overnight run | `tests/test_overnight.py` | 3h | All above |

### Phase 5: Model Promotion + Bandit (Week 5)

**Goal:** Track-and-Stop bandit for statistically validated model promotion.

| Task | File | Effort | Depends |
|---|---|---|---|
| Shadow evaluation protocol | `src/detrix/improvement/shadow_eval.py` | 4h | Trainer |
| Track-and-Stop bandit (GLRT) | `src/detrix/improvement/bandit.py` | 4h | Shadow eval |
| Model version registry | `src/detrix/core/registry.py` | 3h | governance.py |
| Alias-based deployment (@active, @champion, @staging) | Registry | 2h | Registry |
| Rollback protocol | Promoter + registry | 2h | Both |
| Integration test: train → shadow eval → promote/rollback | `tests/test_promotion.py` | 3h | All above |

### Phase 6: Meta-Harness Loop (Month 2+)

**Goal:** LLM proposer optimizes governance config and GRPO hyperparameters.

This is the Karpathy autoresearch pattern applied to Detrix's overnight loop:

```
1. PROPOSE: LLM reads governance configs + past training results + eval scores
            Proposes: reward weights, gate thresholds, LoRA rank, learning rate
2. TRAIN:   Run overnight GRPO with proposed config (8h window)
3. EVALUATE: Governance composite score on held-out domain runs
4. DECIDE:   If score improved → keep config, update experiment log
             If regressed → discard, revert config, log attempt
5. REPEAT
```

---

## 5. Key Architectural Decisions

### 5.1 Why Adapter Pattern (Not Plugin Pattern)

Pi uses plugins (extensions). Detrix could be a pi extension. But:

- **Adapter wraps externally.** The harness doesn't need to know Detrix exists.
- **Plugin requires harness cooperation.** The harness must load and trust the plugin.
- **Adapter works across harnesses.** Same Detrix core wraps pi, LangGraph, CrewAI.
- **Plugin is harness-specific.** A pi extension doesn't help LangGraph users.

Detrix's value prop is framework-agnostic governance. Adapter pattern preserves this.

The pi extension IS an adapter implementation detail — it's how the PiAdapter
communicates with pi's runtime. But the Detrix user sees `HarnessAdapter`, not
a pi extension.

### 5.2 Why IPC Bridge (Not In-Process)

Pi is TypeScript. Detrix is Python. Options:

| Approach | Pros | Cons |
|---|---|---|
| **JSON-RPC over stdio** | Clean boundary, pi's RPC mode supports it natively | Latency per gate call (~5ms) |
| HTTP server | Standard, debuggable | Extra port, process management |
| In-process (PyO3/Napi) | Zero-copy, fastest | Build complexity, tight coupling |
| File-based (JSONL append) | Simplest, async | No real-time gate blocking |

**Choice: JSON-RPC over stdio.** Pi already has `rpc-mode.ts` for subprocess
integration. Gate evaluation latency (~5ms) is negligible vs LLM inference (~500ms).
Clean process boundary means pi crashes don't take down Detrix and vice versa.

### 5.3 Why Skills Before Training

MetaClaw shows skills-only delivers 7-32% improvement with zero GPU cost and
immediate effect. The skill evolver:

1. Analyzes governance-rejected traces (WHY the gate said no)
2. Synthesizes behavioral rules as markdown files
3. Injects into the agent's system prompt via pi's skill system
4. Takes effect on the next conversation — no retraining needed

This is the fastest path to demonstrable improvement. Train only after skills plateau.

### 5.4 Deterministic-First Applies to Pi Too

Pi has no command filtering or sandboxing. Detrix's governance gates add this:

```
Pi tool call: bash("rm -rf /")
  → Detrix pre-gate: StructuralSafetyGate.evaluate({"command": "rm -rf /"})
  → Decision.REJECT, reason_codes=["destructive_command"]
  → Pi hook returns {block: true}
  → Command never executes
```

This is structural enforcement via the adapter — pi doesn't need to implement safety,
Detrix provides it externally. Different from pi's "add safety via extensions" approach
because Detrix gates are unconditional (the orchestrator runs them, not the agent).

---

## 6. Cross-Reference: Principles from All Sources

### From MetaClaw:

| Principle | Application |
|---|---|
| Dual timescale (fast skills + slow RL) | Skills ship in Phase 2, GRPO in Phase 4 |
| OMLS opportunistic scheduling | Phase 4 — idle detect + overnight window |
| Support-query versioning | Flush trace buffer on ANY governance version change |
| PRM for dense process rewards | Governance composite score = the PRM |
| Mutual reinforcement | Better model → better failures → better skills → better model |

### From Meta-Harness:

| Principle | Application |
|---|---|
| Full execution traces as proposer input | Phase 6 — proposer reads governance traces |
| PUCT exploration/exploitation | Bandit in Phase 5 approximates this |
| Harness code as optimization target | Phase 6 — optimize gate thresholds + reward weights |
| Median 82 files per iteration | Proposer gets full access to trace DB + config |

### From Agent-RLVR:

| Principle | Application |
|---|---|
| Dense reward > sparse reward | Governance gates already provide this |
| Hybrid SFT+DPO before RL | Training strategy: SFT → DPO → GRPO |
| Guidance from failures | Skill evolver generates "guidance" as skills |
| Test assertions as verifiable reward | Domain evaluators = verifiable reward |

### From Pi-Mono:

| Principle | Application |
|---|---|
| Extension-first for domain specificity | Domain packs ARE Detrix extensions |
| Definition-first tool registry | Typed GovernanceGate + DomainEvaluator registries |
| Session as append-only source of truth | Audit log + GovernedTrajectory = immutable record |
| Provider-agnostic from day one | Framework-agnostic from day one |
| No eval in core (deliberate scope) | Detrix IS the eval layer pi doesn't have |
| Skills as prompt-injectable markdown | MetaClaw skill evolver → pi skill system |

---

## 7. What NOT to Build

| Don't Build | Why | Alternative |
|---|---|---|
| Full pi-mono clone in Python | Pi is a harness, Detrix is governance. Don't compete. | Wrap via adapter |
| Custom RL framework | TRL GRPOTrainer is production-grade | Use TRL directly |
| GPU-cluster RL infra (Atropos) | Single domain, 4 GPUs. Premature. | V2 if multi-domain |
| Custom agent loop | Pi/LangGraph/CrewAI already do this | Adapter pattern |
| Learned reward model | Governance score IS the reward. No RM training needed for MVP. | Direct reward fn |
| Meta-Harness proposer | Requires validated GRPO loop first | Phase 6 (Month 2+) |
| Pi-mono TypeScript port | Detrix is Python, pi is TypeScript. IPC bridge handles it. | JSON-RPC |

---

## 8. Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Pi API instability (v0.67, fast-moving) | MEDIUM | Pin to specific pi-mono version, test against release tags |
| JSON-RPC latency blocks agent UX | LOW | Gate eval is <5ms, LLM inference is ~500ms. Negligible. |
| Skill evolver produces bad skills | MEDIUM | Gate the skills — run evolved skills through governance eval before injection |
| Reward contamination from version drift | HIGH | Support-query versioning is non-negotiable. Flush on ANY version change. |
| GRPO doesn't converge on governance reward | MEDIUM | SFT-first strategy validates the loop before GRPO investment |
| Meta-Harness proposer infinite-loops | LOW | Phase 6 is bounded by overnight window + experiment budget |

---

## Sources

- [pi-mono GitHub](https://github.com/badlogic/pi-mono) — v0.67.67, 36.8k stars, TypeScript
- [MetaClaw arXiv 2603.17187](https://arxiv.org/abs/2603.17187) — AIMING Lab, MIT
- [Meta-Harness arXiv 2603.28052](https://arxiv.org/abs/2603.28052) — Stanford IRIS Lab
- [Agent-RLVR arXiv 2506.11425](https://arxiv.org/abs/2506.11425) — Guidance-based RLVR
- [Atropos GitHub](https://github.com/NousResearch/atropos) — Nous Research, MIT
- [Hermes Agent](https://hermes-agent.nousresearch.com) — Nous Research
- [TRL GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) — v1.0 RC1
- [TensorZero Track-and-Stop](https://www.tensorzero.com/blog/bandits-in-your-llm-gateway/)
- Existing: `docs/rl-environment-research-march2026.md`, `docs/rl-route-research.md`,
  `docs/sota-agent-research-20260328.md`, `docs/governance-spec.md`
