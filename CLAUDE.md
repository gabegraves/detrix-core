# Detrix Core

Autoresearch for domain-specific agent pipelines — wrap any framework, get governance, memory, and self-improvement. Your agents work in demos; Detrix makes them work in production.

## Mission

Detrix is the infrastructure layer that turns any domain-specific agent from a demo into a reliable, self-improving pipeline. It wraps existing frameworks (LangGraph, LangChain, CrewAI, raw Python) — it does not replace them. The product is the four-layer stack; domain packs (starting with AgentXRD for materials science) prove the stack works on real science.

## Positioning (READ THIS FIRST)

**Detrix is NOT a pipeline runner.** It is a governance and improvement runtime that wraps whatever pipeline runner you already use. Do not position against LangGraph — position as the layer above it.

- **We are NOT:** another DAG executor, another YAML pipeline tool, another LangGraph competitor
- **We ARE:** the trust + improvement layer every agentic science company needs but nobody has built
- **One-liner:** "Detrix is autoresearch for domain-specific agent pipelines — define your workflow, plug in models, and the system makes them reliable and self-improving overnight."
- **Competitive edge:** 26+ YC companies build vertical AI agents. None have governance + memory + improvement loop + domain packs as infrastructure. We do.

### Key differentiators (what LangGraph/LangSmith lack):
1. **Improvement flywheel** — traces → SFT/RL → challenger model → blue/green promote → repeat. Every run makes local models better.
2. **Persistent memory across runs** — BM25 + semantic + graph BFS recall, tiered compression, self-curating
3. **Domain packs** — pluggable expert workflows (AgentXRD: 9-phase, 71% → 89% accuracy via overnight RL on local models)
4. **Local-first governance** — audit, provenance, RBAC baked into the runtime, not a paid SaaS bolt-on
5. **Framework-agnostic** — wraps LangGraph, LangChain, CrewAI, or raw Python. Not a replacement.

## Build / Test / Run
- `uv run pytest` — run all tests
- `uv run ruff check .` — lint
- `uv run mypy src/detrix` — type check
- `uv run detrix run examples/seed_pipeline.yaml -v` — smoke test CLI
- `uv sync` — install deps (never pip)

## Architecture

Four-layer stack — Runtime/Governance is THE product. Everything above is bundled or sold as add-ons.
```
┌───────────────────────────────────────────────────────────┐
│  DOMAIN PACKS (first: AgentXRD, then customer domains)    │
│  Pluggable, sold separately or built by customers         │
├───────────────────────────────────────────────────────────┤
│  IMPROVEMENT LOOP                                         │
│  Traces → SFT/RL → challenger → blue/green promote       │
│  The flywheel: every run makes local models better        │
├───────────────────────────────────────────────────────────┤
│  MEMORY LAYER                                             │
│  Multi-source recall, tiered compression, self-curating   │
│  Agents remember across sessions and runs                 │
├───────────────────────────────────────────────────────────┤
│  RUNTIME / GOVERNANCE (Detrix Core — the product)         │
│  Run Artifacts, Provenance DAG, Replay, RBAC, Audit       │
│  The trust layer every agentic science company needs      │
└───────────────────────────────────────────────────────────┘
```

### Current Implementation (detrix-core repo)
- `src/detrix/core/` — models (StepDef, WorkflowDef, RunRecord, StepResult), cache, pipeline engine
- `src/detrix/runtime/` — audit log, artifacts, diff, provenance
- `src/detrix/improvement/` — ModelPromoter, eval harness, trace collector
- `src/detrix/cli/` — Click CLI commands
- `tests/` — all tests
- `examples/` — example pipelines and usage
- `.detrix/` — runtime data directory (cache.db, audit.db, artifacts/)

## Design Principles
- **Framework-agnostic**: wrap LangGraph, LangChain, CrewAI, or raw Python — don't replace them
- **Local-first**: SQLite everywhere, no cloud accounts needed
- **Deterministic**: fixed seeds, content-addressable cache, reproducible runs
- **Self-improving**: traces feed fine-tuning, challenger models promote automatically
- **Pluggable**: StepEvaluator ABC, TraceCollector ABC — implement what you need

## Conventions
- Click for CLI (not argparse)
- Pydantic v2 for all data models
- pytest for tests (no mocks of internal modules — integration tests only)
- ruff for linting (line-length=100)
- Conventional commits (feat/fix/docs/refactor)
- `uv` for all package management (never pip)
