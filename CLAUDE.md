# Detrix Core

Make domain-specific agents reliable enough to deploy and cheap enough to scale.

## Design Doc

Full strategy, competitive analysis, positioning, and build plan:
`~/.gstack/projects/gabegraves-detrix-core/gabriel-main-design-20260331-022621.md`

Governance spec (ABCs, verdict contracts, MVP build order):
`docs/governance-spec.md`

Pi-mono + Meta-Harness + MetaClaw + Agent-RLVR research synthesis:
`docs/pi-agent-harness-research-20260417.md`

Autoresearch landscape + Bitter Lesson implications:
`docs/autoresearch-landscape-eval-20260423.md`, `docs/bitter-lesson-harness-implications-20260423.md`

## What Detrix Is

Reliability and improvement runtime for domain-specific agents. Evaluates outputs with domain physics post-hoc, rejects bad results, learns from scored traces, improves harness + model over time. RLVR (Reinforcement Learning with Verifiable Rewards) where domain physics evaluation IS the verifiable reward.

- Evaluates agent outputs post-hoc — does not wrap agent tools or constrain action space
- Adapts to existing frameworks (LangGraph, CrewAI, raw Python) via thin trajectory-capture shims
- NOT a methodology company, NOT a DAG executor, NOT a training UI
- Unsloth/ART handle training execution (complementary). Detrix provides the quality SIGNAL.
- AgentXRD_v2 is the proving ground (203 files, 6 gates already post-hoc). detrix-core is the extraction target.
- Target: self-improving, deterministically scored harness running local models (Qwen 3.6 via vLLM)

## Architecture

### Runtime: Observer -> Enforcer -> Improve

```
OBSERVE: attach to pipeline, score outputs post-hoc, calibrate thresholds
ENFORCE: calibrated gates block bad outputs (deterministic-first)
IMPROVE: scored traces -> SFT/DPO/GRPO overnight, challenger promotes through same gates
```

### Deterministic-First Hierarchy

```
1. Physics/math verifiable? -> Deterministic gate (Rietveld, convergence, backtest)
2. Structurally verifiable? -> Deterministic gate (schema, type, range)
3. Only semantic judgment?  -> LLM advisory (scores, never blocks)
4. Not verifiable?          -> Human-in-the-loop checkpoint
```

### Enforcement: Post-Hoc Evaluation (Bitter Lesson-Aligned)

Gates evaluate outputs after each agent phase — agent has full freedom, no awareness of gates.
Orchestrator runs evaluation checkpoints unconditionally after handler completion. If output
fails a gate, orchestrator rejects it (TerminalRoute) and the agent gets a rejection signal,
not a blocked action. Gates are invisible to the agent's action space.

This is the Bitter Lesson of Agent Harnesses applied: don't wrap the agent's tools or constrain
its actions. Evaluate results post-hoc. The agent optimizes for accuracy; gates validate
trustworthiness independently. AgentXRD_v2 already implements this pattern — handlers have
zero awareness of gates (see `pipeline.py:_post_score_governance()`, `_post_refinement_governance()`).

Not hooks (advisory). Not action-space constraints (wrapping). Post-hoc structural evaluation.

### Three-Tier Scoring

- Tier 1: Deterministic physics gates (authority, always blocks)
- Tier 2: LLM-as-judge (advisory only, never authoritative)
- Tier 3: Agent audit (behavioral verification — did agent do what it claimed?)
- Training signal: only traces where all tiers agree

### Five-Layer Stack

```
DOMAIN PACKS      — domain-specific gates, evaluators, training configs (proprietary)
IMPROVEMENT LOOP  — SFT/DPO/GRPO via ART+Unsloth on scored traces (overnight)
SESSION SCORING   — Tier 1 deterministic + Tier 2 LLM advisory
MEMORY LAYER      — not yet implemented
GOVERNANCE RAILS  — observer/enforcer runtime + post-hoc evaluation checkpoints (open-source)
```

### Build Sequence (revised 2026-04-17)

Improvement loop first. Adapters later. Foundation = existing pipeline.py + governance.py.

```
Phase 1 (Wk 1-2): GovernedTrajectory schema + MetaClaw skill evolver
Phase 2 (Wk 2-3): Training data bridge (traces → HF Dataset for SFT/DPO/GRPO)
Phase 3 (Wk 3-4): Overnight training loop (vLLM + TRL GRPOTrainer + OMLS scheduler)
Phase 4 (Wk 4-5): Model promotion (shadow eval + Track-and-Stop bandit)
Phase 5 (Mo 2+):  Framework adapters (thin trajectory-capture shims — LangGraph first)
Phase 6 (Mo 3+):  Meta-Harness proposer (LLM optimizes governance config — agent-editable configs start Phase 1)
```

### Architectural Decisions (2026-04-23)

- **Pi-mono is a reference architecture, not a foundation.** TypeScript + cloud-API orientation
  is wrong for ML training (Python + vLLM + TRL). Adopt its design principles (extension-first,
  definition-first tool registry, session-as-truth) but build in Python.
- **AgentXRD_v2 is the proving ground.** 6 governance gates built as post-hoc output evaluators,
  deterministic physics, Python, and the monetization vertical. Gates are already Bitter
  Lesson-aligned — handlers have zero awareness of gates.
- **Improvement loop before adapters.** The moat is the RLVR environment (reward functions +
  evidence), not the adapter layer. Build skill evolver + training bridge + OMLS first.
- **MetaClaw dual mechanism.** Gradient-free skills (7-32% improvement, zero GPU, immediate)
  + gradient-based GRPO (overnight, compounds on skills). Skills ship first.
- **Support-query versioning is non-negotiable.** Flush trace buffer on ANY gate/evaluator
  version change. Reward contamination is silent and deadly.
- **Gates evaluate outputs, never constrain actions (Bitter Lesson).** The agent has maximal
  action-space freedom. Gates are invisible post-hoc evaluation checkpoints the orchestrator
  runs unconditionally. AgentXRD_v2 already does this — preserve the pattern during extraction.
- **Governance config is agent-editable from Phase 1.** Gate thresholds live in config the agent
  can read and propose edits to. Changes validated against held-out test set. Don't defer
  editability to Phase 6 Meta-Harness.
- **Adapters are trajectory-capture shims, not framework wrappers.** ~50 lines each. Hook into
  framework output/callback, capture (input, output, metadata) as GovernedTrajectory, return
  accept/reject. No tool wrapping, no action-space modification.
- **MLAgentBench is the Phase 2 RLVR training ground.** 13 ML tasks with deterministic
  get_score() + trajectory logging = ready-made verifiable reward environment for SFT/DPO/GRPO.
- **Competitive moat is the full stack.** 6+ projects (GEPA, AIDE, ML-Agent, recursive-improve)
  attack parts of the improvement loop. None combine deterministic physics gates + tiered
  scoring + post-hoc enforcement + training signal extraction. GEPA (ICLR 2026) outperforms
  GRPO on benchmarks — closest threat to MetaClaw gradient-free evolver.

### Research References

- MetaClaw (2603.17187): skill evolver + OMLS scheduler + support-query versioning
- Meta-Harness (2603.28052, Stanford): LLM proposer optimizes harness code (Phase 6)
- Agent-RLVR (2506.11425): guidance injection for sparse rewards (Detrix gates are superior — dense per-step)
- Pi-mono (badlogic/pi-mono): extension-first architecture, design patterns to adopt
- Atropos/Hermes (NousResearch): microservice RL (V2 if multi-domain)
- MLAgentBench (snap-stanford): 13-task RLVR benchmark, deterministic eval, trajectory logging
- GEPA (ICLR 2026): Pareto prompt evolution, outperforms GRPO — MetaClaw competitive threat
- AIDE/aideml (Weco): tree-search agent improvement loop — closest analog to overnight loop
- Browser-harness (browser-use): Bitter Lesson of Agent Harnesses — minimal harness, post-hoc eval
- AutoResearchClaw (aiming-lab): live MetaClaw deployment (5-layer integration, +18.3% robustness)

### Current Implementation

- `src/detrix/core/` — models, cache, pipeline engine
- `src/detrix/runtime/` — audit log, artifacts, diff, provenance, langfuse observer
- `src/detrix/scoring/` — mechanical grader, haiku grader
- `src/detrix/improvement/` — ModelPromoter, eval harness, trace collector
- `src/detrix/cli/` — Click CLI
- `.detrix/` — runtime data (cache.db, audit.db, artifacts/)

## Build / Test / Run

- `uv run pytest` — run all tests
- `uv run ruff check .` — lint
- `uv run mypy src/detrix` — type check
- `uv run detrix run examples/seed_pipeline.yaml -v` — smoke test CLI
- `uv sync` — install deps (never pip)

## Design Principles

- **Deterministic-first**: physics/math -> deterministic code, never LLM
- **Observer-first**: observe, calibrate from real data, THEN enforce
- **Post-hoc evaluation, not action-space wrapping**: gates score outputs after the fact — agent never sees gates in its action space (Bitter Lesson alignment)
- **Minimal harness**: every line of governance code must justify its existence. Thin trajectory-capture shims, not framework internalization.
- **Agent-editable governance**: gate thresholds live in config the agent can read and propose changes to. Don't wait for Meta-Harness to make governance editable — build it in from Phase 1.
- **MVP-first**: spec the eval metric, build thin, iterate from data
- **Framework-agnostic**: adapt via thin shims, don't wrap or replace
- **Local-first**: SQLite everywhere, no cloud accounts needed
- **Self-improving**: governance-scored traces feed fine-tuning
- **Pluggable**: GovernanceGate ABC, DomainEvaluator ABC, adapter pattern

## Conventions

- Click for CLI (not argparse)
- Pydantic v2 for all data models
- pytest for tests (no mocks of internal modules — integration tests only)
- ruff for linting (line-length=100)
- `uv` for all package management (never pip)

## Quality Gates

- `uv run ruff check .` and `uv run mypy src/detrix` before committing
- `uv run pytest` before pushing

## Git Rules

- Commit early and often, one logical change per commit
- Conventional commits (feat/fix/docs/refactor)
- Include beads issue ID when applicable: `feat: add trace collector (bd-abc)`

## Working Rules

- All work tracked with beads and git
- Run `exec-report` skill at end of beads-tracked execution sessions
