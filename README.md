# detrix

**Turn failed agent sessions into replay-safe harness improvements.**

Detrix converts raw agent traces into atomic execution beads, verifies the claims and artifacts for each bead, mines recurring failure patterns, and promotes only harness changes that improve held-out replay without weakening domain gates.

> Current direction: see `docs/bead-native-harness-compiler-20260505.md`. The older pipeline runtime remains useful seed infrastructure, but the product direction is the bead-native builder/verifier harness compiler.

## Install

```bash
pip install detrix
```

## Quickstart

```bash
# Initialize detrix in your project
cd your-project

# Run a pipeline
detrix run pipeline.yaml -v

# See what happened
detrix history

# Compare two runs
detrix diff <run-a> <run-b>

# Inspect a specific run
detrix inspect <run-id>
```

## What it does

**Reproducible runs** — Every pipeline execution is cached by content hash and logged to an append-only audit trail. Same inputs = same outputs, guaranteed.

**Run artifacts** — Each run produces an immutable bundle: input hashes, output hashes, code revision, environment spec, step-by-step results. Portable, diffable, auditable.

**Run diffing** — `detrix diff` shows exactly what changed between two runs: which inputs changed, which steps produced different outputs, which models were swapped.

**Improvement loop** — Compare challenger models against incumbents on named metrics with explicit thresholds. Promote or reject, no guessing.

## Who is this for

Any team running AI agent pipelines that needs accountability, reproducibility, and continuous improvement:

- **R&D labs** — materials science, drug discovery, chemical engineering
- **ML engineering teams** — model evaluation, A/B testing, pipeline governance
- **Startups building vertical AI** — need audit trails before enterprise sales
- **Process engineering** — semiconductor fabs, manufacturing optimization
- **Financial modeling** — reproducible backtests, model validation

## Architecture

```
Improvement Loop    →  ModelPromoter, StepEvaluator, TraceCollector
Runtime/Governance  →  RunArtifact, AuditLog, diff, provenance
Pipeline Engine     →  WorkflowEngine, DAG executor, StepCache
Core Models         →  StepDef, WorkflowDef, RunRecord, StepResult
```

## Define a pipeline

```yaml
name: my-pipeline
version: "1.0"
steps:
  - id: load
    function: mypackage.steps.load_data
    outputs: [records]

  - id: process
    function: mypackage.steps.process
    depends_on: [load]
    inputs:
      records: "$load.records"
    retry:
      max_attempts: 3
      backoff_seconds: 1.0

  - id: evaluate
    function: mypackage.steps.evaluate
    depends_on: [process]
    inputs:
      results: "$process.output"
```

## Use programmatically

```python
from detrix.core import WorkflowEngine, StepCache, parse_workflow
from detrix.runtime.audit import AuditLog

engine = WorkflowEngine(
    cache=StepCache(".detrix/cache.db"),
    audit=AuditLog(".detrix/audit.db"),
    verbose=True,
)

record = engine.run_from_yaml("pipeline.yaml", inputs={"data_path": "/data"})
print(f"Run {record.run_id}: {record.status.value}")
```

## Design principles

- **Local-first** — SQLite for everything, no cloud accounts needed
- **YAML-as-code** — Declarative pipelines, version-controlled
- **Deterministic** — Content-addressable cache, reproducible by default
- **Pluggable** — ABC interfaces for evaluation, tracing, and model comparison

## License

MIT
