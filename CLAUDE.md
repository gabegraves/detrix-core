# Detrix Core

Make domain-specific agents reliable enough to deploy and cheap enough to scale.

## Design Doc

Full strategy, competitive analysis, positioning, and build plan:
`~/.gstack/projects/gabegraves-detrix-core/gabriel-main-design-20260331-022621.md`

Governance spec (ABCs, verdict contracts, MVP build order):
`docs/governance-spec.md`

Pi-mono + Meta-Harness + MetaClaw + Agent-RLVR research synthesis:
`docs/pi-agent-harness-research-20260417.md`

## What Detrix Is

Reliability and improvement runtime for domain-specific agents. Validates outputs with domain physics, blocks bad results, learns from failures, improves harness + model over time. RLVR (Reinforcement Learning with Verifiable Rewards) where domain physics evaluation IS the verifiable reward.

- Wraps existing frameworks (LangGraph, CrewAI, raw Python) via adapters — does not replace them
- NOT a methodology company, NOT a DAG executor, NOT a training UI
- Unsloth/ART handle training execution (complementary). Detrix provides the quality SIGNAL.
- AgentXRD_v2 is the product demo (203 files). detrix-core is the extraction target.
- Target: self-improving, deterministically gated harness running local models (Qwen 3.6 via vLLM)

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

### Enforcement: Stripe Blueprints Pattern

State machine where deterministic gates alternate with agentic phases. Agent CANNOT skip gates — orchestrator runs them unconditionally. Not hooks (advisory). Not pipeline validators (too late). Structural enforcement.

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
GOVERNANCE RAILS  — observer/enforcer runtime + Stripe Blueprints gates (open-source)
```

### Build Sequence (revised 2026-04-17)

Improvement loop first. Adapters later. Foundation = existing pipeline.py + governance.py.

```
Phase 1 (Wk 1-2): GovernedTrajectory schema + MetaClaw skill evolver
Phase 2 (Wk 2-3): Training data bridge (traces → HF Dataset for SFT/DPO/GRPO)
Phase 3 (Wk 3-4): Overnight training loop (vLLM + TRL GRPOTrainer + OMLS scheduler)
Phase 4 (Wk 4-5): Model promotion (shadow eval + Track-and-Stop bandit)
Phase 5 (Mo 2+):  Framework adapters (LangGraph first, then pi-mono/raw Python)
Phase 6 (Mo 3+):  Meta-Harness proposer (LLM optimizes governance config)
```

### Architectural Decisions (2026-04-17)

- **Pi-mono is a reference architecture, not a foundation.** TypeScript + cloud-API orientation
  is wrong for ML training (Python + vLLM + TRL). Adopt its design principles (extension-first,
  definition-first tool registry, session-as-truth) but build in Python.
- **AgentXRD_v2 is the proving ground.** 6 governance gates built, deterministic physics,
  Python, and the monetization vertical. Not ParabolaHunter (demo vehicle, not foundation).
- **Improvement loop before adapters.** The moat is the RLVR environment (reward functions +
  evidence), not the adapter layer. Build skill evolver + training bridge + OMLS first.
- **MetaClaw dual mechanism.** Gradient-free skills (7-32% improvement, zero GPU, immediate)
  + gradient-based GRPO (overnight, compounds on skills). Skills ship first.
- **Support-query versioning is non-negotiable.** Flush trace buffer on ANY gate/evaluator
  version change. Reward contamination is silent and deadly.

### Research References

- MetaClaw (2603.17187): skill evolver + OMLS scheduler + support-query versioning
- Meta-Harness (2603.28052, Stanford): LLM proposer optimizes harness code (Phase 6)
- Agent-RLVR (2506.11425): guidance injection for sparse rewards (Detrix gates are superior — dense per-step)
- Pi-mono (badlogic/pi-mono): extension-first architecture, design patterns to adopt
- Atropos/Hermes (NousResearch): microservice RL (V2 if multi-domain)

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
- **MVP-first**: spec the eval metric, build thin, iterate from data
- **Framework-agnostic**: wrap via adapters, don't replace
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
