# Detrix Core

The runtime that makes any AI agent pipeline reproducible, governed, and self-improving — for science, engineering, and R&D teams in any domain.

## Build / Test / Run
- `uv run pytest` — run all tests
- `uv run ruff check .` — lint
- `uv run mypy src/detrix` — type check
- `uv run detrix run examples/seed_pipeline.yaml -v` — smoke test CLI
- `uv sync` — install deps (never pip)

## Architecture

4-layer stack:
```
┌─────────────────────────────────┐
│  Improvement Loop               │  ModelPromoter, StepEvaluator, TraceCollector
│  (challenger vs incumbent)      │
├─────────────────────────────────┤
│  Runtime / Governance           │  RunArtifact, AuditLog, diff, provenance
│  (who ran what, when, why)      │
├─────────────────────────────────┤
│  Pipeline Engine                │  WorkflowEngine, DAG executor, StepCache
│  (YAML → topological execution) │
├─────────────────────────────────┤
│  Core Models                    │  StepDef, WorkflowDef, RunRecord, StepResult
│  (typed contracts)              │
└─────────────────────────────────┘
```

## Design Principles
- **Local-first**: SQLite everywhere, no cloud accounts needed
- **YAML-as-code**: pipelines are declarative YAML with typed step contracts
- **Deterministic**: fixed seeds, content-addressable cache, reproducible runs
- **Pluggable**: StepEvaluator ABC, TraceCollector ABC — implement what you need

## Conventions
- Click for CLI (not argparse)
- Pydantic v2 for all data models
- pytest for tests (no mocks of internal modules — integration tests only)
- ruff for linting (line-length=100)
- Conventional commits (feat/fix/docs/refactor)
- `uv` for all package management (never pip)

## Key Paths
- `src/detrix/core/` — models, cache, pipeline engine
- `src/detrix/runtime/` — audit, artifacts, diff, provenance
- `src/detrix/improvement/` — promoter, eval harness, trace collector
- `src/detrix/cli/` — Click CLI commands
- `tests/` — all tests
- `examples/` — example pipelines and usage
- `.detrix/` — runtime data directory (cache.db, audit.db, artifacts/)
