# Detrix: Package A → Governed Karpathy Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a trace classifier that reads Langfuse traces, proposes deterministic gates from failure patterns, classifies traces for training export — then extend into a governed self-improvement loop (the Karpathy Loop for domain-specific agents).

**Architecture:** Four phases. Phase 1 ("Detrix Export") ships a CLI product: `detrix connect → detrix propose-gates → detrix classify → detrix export`. Phase 2 ("Detrix Diagnose") adds automated skill generation from failure patterns with governed promotion. Phase 3 ("Detrix Loop") wires the full autoresearch ratchet: diagnose → skill → train → shadow-eval → promote → serve. Phase 4 packages for distribution.

**Tech Stack:** Python 3.12, Click CLI, Pydantic v2, SQLite (TrajectoryStore), Unsloth + TRL (training), pi agent harness (runtime), vLLM (serving). `uv` for packages.

**Key constraint:** Post-hoc evaluation only (Bitter Lesson). Gates never constrain agent action space. Support-query versioning: flush trace buffer on ANY gate/evaluator version change.

**Core insight:** Gates in AgentXRD and ParabolaHunter were all agent-written (Claude Code sessions analyzing failures). The product is the PROCESS of creating gates from failures — an agent reads traces, proposes deterministic checks, human approves. The "gate factory" is already happening informally.

---

## File Map

### Phase 1 — Detrix Export (new files)

| File | Responsibility |
|------|---------------|
| `src/detrix/connectors/langfuse.py` | Generic Langfuse trace reader (HTTP API + SQLite cache) |
| `src/detrix/connectors/jsonl.py` | JSONL trace file reader |
| `src/detrix/connectors/base.py` | TraceConnector ABC |
| `src/detrix/classify/proposer.py` | Agent that reads failure patterns → proposes GovernanceGate code |
| `src/detrix/classify/classifier.py` | Runs approved gates on traces → SFT-positive/DPO-negative/eval-only/exclude |
| `src/detrix/classify/review.py` | CLI review flow for proposed gates (approve/reject/edit) |
| `tests/test_connectors.py` | Connector tests |
| `tests/test_proposer.py` | Gate proposer tests |
| `tests/test_classifier.py` | Trace classifier tests |

### Phase 1 — Detrix Export (modified files)

| File | Change |
|------|--------|
| `src/detrix/cli/main.py` | Add `connect`, `propose-gates`, `classify` commands |
| `src/detrix/core/governance.py` | Add `TraceClassification` enum, `classify_trace()` function |

### Phase 2 — Detrix Diagnose (new files)

| File | Responsibility |
|------|---------------|
| `src/detrix/skillify/miner.py` | Generic failure pattern miner (not AgentXRD-specific) |
| `src/detrix/skillify/generator.py` | Skill generation from failure patterns |
| `src/detrix/skillify/validator.py` | Skill validation against holdout traces |
| `src/detrix/skillify/promoter.py` | Governed skill promotion with admission checks |

### Phase 3 — Detrix Loop (new files)

| File | Responsibility |
|------|---------------|
| `src/detrix/loop/ratchet.py` | Karpathy-style autoresearch ratchet for domain agents |
| `src/detrix/loop/serving.py` | vLLM/Ollama adapter loading + inference server |
| `src/detrix/loop/shadow_eval.py` | Shadow evaluation for model promotion |
| `src/detrix/loop/runtime.py` | Always-on agent runtime with continuous re-training trigger |

---

## Phase 1: Detrix Export (~3-4 weeks)

The first revenue-generating product. A CLI that connects to existing traces, proposes gates, classifies training data, and exports governed datasets.

### Task 1: Trace Connector ABC + JSONL Connector

**Files:**
- Create: `src/detrix/connectors/__init__.py`
- Create: `src/detrix/connectors/base.py`
- Create: `src/detrix/connectors/jsonl.py`
- Test: `tests/test_connectors.py`

- [ ] **Step 1: Write the failing test for TraceConnector ABC and JSONL reader**

```python
# tests/test_connectors.py
import json
from pathlib import Path
from detrix.connectors.base import Trace, TraceConnector
from detrix.connectors.jsonl import JsonlConnector

def test_trace_has_required_fields():
    t = Trace(
        trace_id="t1", inputs={"prompt": "hello"},
        outputs={"completion": "world"}, tool_calls=[],
        metadata={"model": "qwen-3.6"}, timestamp="2026-05-01T00:00:00Z",
    )
    assert t.trace_id == "t1"

def test_jsonl_connector_reads_traces(tmp_path: Path):
    traces_file = tmp_path / "traces.jsonl"
    rows = [
        {"trace_id": "t1", "inputs": {"prompt": "analyze"},
         "outputs": {"completion": "NaCl"}, "tool_calls": [{"name": "rietveld", "result": {"rwp": 5.2}}],
         "metadata": {}, "timestamp": "2026-05-01T00:00:00Z"},
        {"trace_id": "t2", "inputs": {"prompt": "identify"},
         "outputs": {"completion": "Unable"}, "tool_calls": [],
         "metadata": {}, "timestamp": "2026-05-01T00:01:00Z"},
    ]
    with traces_file.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    connector = JsonlConnector(str(traces_file))
    traces = list(connector.read_traces())
    assert len(traces) == 2

def test_jsonl_connector_count(tmp_path: Path):
    traces_file = tmp_path / "traces.jsonl"
    with traces_file.open("w") as f:
        for i in range(5):
            f.write(json.dumps({"trace_id": f"t{i}", "inputs": {}, "outputs": {},
                                "tool_calls": [], "metadata": {}, "timestamp": "2026-05-01T00:00:00Z"}) + "\n")
    assert JsonlConnector(str(traces_file)).count() == 5
```

- [ ] **Step 2:** Run: `uv run pytest tests/test_connectors.py -v` — Expected: FAIL

- [ ] **Step 3: Write Trace model, TraceConnector ABC, and JsonlConnector**

```python
# src/detrix/connectors/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any
from pydantic import BaseModel, Field

class Trace(BaseModel):
    trace_id: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str

    @property
    def prompt(self) -> str:
        return self.inputs.get("prompt", "")

    @property
    def completion(self) -> str:
        return self.outputs.get("completion", "")

class TraceConnector(ABC):
    @abstractmethod
    def read_traces(self, limit: int | None = None) -> Iterator[Trace]: ...
    @abstractmethod
    def count(self) -> int: ...
```

```python
# src/detrix/connectors/jsonl.py
from __future__ import annotations
import json
from collections.abc import Iterator
from pathlib import Path
from detrix.connectors.base import Trace, TraceConnector

class JsonlConnector(TraceConnector):
    def __init__(self, path: str) -> None:
        self.path = Path(path)
    def read_traces(self, limit: int | None = None) -> Iterator[Trace]:
        with self.path.open() as f:
            for i, line in enumerate(f):
                if limit is not None and i >= limit:
                    break
                yield Trace(**json.loads(line))
    def count(self) -> int:
        with self.path.open() as f:
            return sum(1 for _ in f)
```

- [ ] **Step 4:** Run: `uv run pytest tests/test_connectors.py -v` — Expected: 3 PASS
- [ ] **Step 5:** Commit: `git add src/detrix/connectors/ tests/test_connectors.py && git commit -m "feat: add TraceConnector ABC and JSONL connector"`

---

### Task 2: Langfuse HTTP Connector

**Files:**
- Create: `src/detrix/connectors/langfuse.py`
- Modify: `tests/test_connectors.py`

- [ ] **Step 1:** Write tests for LangfuseConnector.from_env() and _parse_traces()
- [ ] **Step 2:** Run: `uv run pytest tests/test_connectors.py -v` — Expected: FAIL
- [ ] **Step 3:** Write LangfuseConnector using httpx for paginated API reads. Add httpx to pyproject.toml optional deps.
- [ ] **Step 4:** Run: `uv run pytest tests/test_connectors.py -v` — Expected: PASS
- [ ] **Step 5:** Commit: `feat: add Langfuse HTTP trace connector`

---

### Task 3: TraceClassification + classify_trace()

**Files:**
- Create: `src/detrix/classify/__init__.py`
- Create: `src/detrix/classify/classifier.py`
- Test: `tests/test_classifier.py`

The core classification logic. For each trace, run all approved gates. Classify based on verdicts:
- All ACCEPT → SFT_POSITIVE
- Any REJECT with rejection_type="input_quality" → EXCLUDE
- Any REJECT with rejection_type="output_quality" → DPO_NEGATIVE
- Mixed/CAUTION/UNKNOWN without rejection_type → EVAL_ONLY
- No gates → EVAL_ONLY

```python
class TraceClassification(str, Enum):
    SFT_POSITIVE = "sft_positive"
    DPO_NEGATIVE = "dpo_negative"
    EVAL_ONLY = "eval_only"
    EXCLUDE = "exclude"

class ClassifiedTrace(BaseModel):
    trace: Trace
    classification: TraceClassification
    verdicts: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = ""

def classify_trace(trace: Trace, gates: list[GovernanceGate]) -> ClassifiedTrace: ...
```

- [ ] **Step 1:** Write 5 tests: all_accept→sft_positive, input_reject→exclude, output_reject→dpo_negative, caution→eval_only, no_gates→eval_only
- [ ] **Step 2:** Run tests — Expected: FAIL
- [ ] **Step 3:** Implement classify_trace
- [ ] **Step 4:** Run tests — Expected: 5 PASS
- [ ] **Step 5:** Commit: `feat: add trace classifier with SFT/DPO/eval-only/exclude labels`

---

### Task 4: Gate Proposer — Extract Failure Signals, Render Gate Code

**Files:**
- Create: `src/detrix/classify/proposer.py`
- Test: `tests/test_proposer.py`

Deterministic signal extraction (no LLM needed for v1):
- empty_completion: agent returned blank
- low_confidence: output confidence below threshold
- no_tool_calls: agent answered without using tools
- tool_call_error: a tool returned an error

Each signal renders into a GovernanceGate subclass via string template.

```python
class FailureSignal(BaseModel):
    signal_type: str
    description: str
    affected_count: int
    trace_ids: list[str]
    suggested_check: str
    suggested_rejection_type: str = "output_quality"

class ProposedGate(BaseModel):
    signal_type: str
    gate_id: str
    gate_code: str
    description: str
    rejection_type: str
    affected_trace_count: int
    status: str = "proposed"  # proposed | approved | rejected

def extract_failure_signals(traces: list[Trace]) -> list[FailureSignal]: ...
def render_gate_proposal(signal: FailureSignal) -> ProposedGate: ...
```

- [ ] **Step 1:** Write 4 tests: finds empty completions, finds low confidence, finds no tool calls, renders valid Python gate code
- [ ] **Step 2:** Run tests — Expected: FAIL
- [ ] **Step 3:** Implement extract_failure_signals and render_gate_proposal
- [ ] **Step 4:** Run tests — Expected: 4 PASS
- [ ] **Step 5:** Commit: `feat: add gate proposer — extracts failure signals, renders gate code`

---

### Task 5: Gate Review — Save/Load Proposals with Approval Status

**Files:**
- Create: `src/detrix/classify/review.py`
- Test: `tests/test_review.py`

```python
def save_proposals(proposals: list[ProposedGate], path: Path) -> None: ...
def load_approved_gates(path: Path) -> list[ProposedGate]: ...
```

- [ ] **Step 1:** Write test: save proposals, load only approved ones
- [ ] **Step 2:** Run — FAIL
- [ ] **Step 3:** Implement
- [ ] **Step 4:** Run — PASS
- [ ] **Step 5:** Commit: `feat: add gate proposal save/load with approval status`

---

### Task 6: CLI Commands — connect, propose-gates, classify

**Files:**
- Modify: `src/detrix/cli/main.py`
- Test: `tests/test_cli_classify.py`

Three new Click commands:
- `detrix connect --source jsonl --path traces.jsonl` — cache traces locally
- `detrix propose-gates` — analyze cached traces, write proposals.json
- `detrix classify --auto-approve` — run approved gates on traces, write classified.jsonl

Gate code from proposals is loaded dynamically via `importlib.util.module_from_spec()` (safe alternative to shell-level evaluation). Each proposed gate module is loaded in isolation, inspected for GovernanceGate subclasses, and instantiated.

- [ ] **Step 1:** Write 3 tests: connect_jsonl, propose_gates, classify_with_auto_approve
- [ ] **Step 2:** Run — FAIL
- [ ] **Step 3:** Implement CLI commands
- [ ] **Step 4:** Run — 3 PASS
- [ ] **Step 5:** Run full suite: `uv run pytest --tb=short` — all pass
- [ ] **Step 6:** Commit: `feat: add connect/propose-gates/classify CLI commands`

---

### Task 7: End-to-End Integration Test

**Files:**
- Test: `tests/test_e2e_classify.py`

Full pipeline: write 20 mixed traces (some good, some empty, some low-confidence) → connect → propose-gates → classify --auto-approve → verify classified.jsonl has correct label distribution.

- [ ] **Step 1:** Write e2e test
- [ ] **Step 2:** Run — PASS
- [ ] **Step 3:** Commit: `test: add e2e pipeline test for connect → propose → classify`

---

## Phase 2: Detrix Diagnose (~2-3 weeks after Phase 1)

Governed skill creation from failure patterns. This is where Hermes-style skill generation gets the admission layer.

### Task 8: Generic Failure Pattern Miner

Extract FailurePatternCorpus logic from agentxrd/failure_patterns.py into a generic miner. Input: classified.jsonl. Output: failure clusters with counts and representative traces.

- [ ] Steps: test → implement → test → commit

### Task 9: Skill Generator from Failure Clusters

Takes a FailureCluster and generates a SkillDefinition (schema in core/skill_registry.py). Includes trigger conditions, deterministic tool references, test intents.

- [ ] Steps: test → implement → test → commit

### Task 10: Skill Validation Against Holdout Traces

Split classified traces into train/holdout. Apply candidate skill. Measure: does it reduce failure rate without increasing wrong-accepts? The governed promotion gate Hermes lacks.

- [ ] Steps: test → implement → test → commit

### Task 11: Skillify CLI Command

`detrix skillify --holdout-ratio 0.2` — mine → generate → validate → promote.

- [ ] Steps: test → implement → test → commit

---

## Phase 3: Detrix Loop — The Governed Karpathy Loop (~4-6 weeks after Phase 2)

### Task 12: Ratchet Loop Orchestrator

Karpathy's autoresearch generalized: diagnose → propose skill → validate → apply → re-evaluate → keep/revert. Extends existing AutoresearchLoop from hyperparameter search to full agent improvement.

- [ ] Steps: test → implement → test → commit

### Task 13: Governed Training Trigger

When N governed traces accumulate, trigger SFT via existing SFTTrainer. Export only traces where all tiers agree. Version-stamp.

- [ ] Steps: test → implement → test → commit

### Task 14: Shadow Eval for Model Promotion

Run challenger adapter against holdout. Compare gate pass rates. Promote only if: pass_rate >= incumbent, no new failure modes, wrong_accept_delta <= 0.

- [ ] Steps: test → implement → test → commit

### Task 15: Local Model Serving

vLLM or Ollama wrapper. Load base model + LoRA adapter. OpenAI-compatible API. Hot-swap adapters on promotion.

- [ ] Steps: test → implement → test → commit

### Task 16: Always-On Runtime

Persistent agent: load adapter → connect to pi harness → run gates post-hoc → accumulate traces → trigger re-training → promote → repeat.

- [ ] Steps: test → implement → test → commit

### Task 17: `detrix loop` CLI

`detrix loop --base-model Qwen/Qwen3.6-27B --max-iterations 50`

- [ ] Steps: test → implement → test → commit

---

## Phase 4: Distribution + Scale

### Task 18: Docker Packaging
Multi-stage build: base → inference → full. docker-compose for pi + bridge + gates + serving.

### Task 19: PyPI Release
Publish to PyPI. Version tagging via git tags.

### Task 20: Gate Genome Registry (Future)
Share gate structures publicly, keep calibration private. The npm model for governance.

---

## Beads Issue Structure

```
Epic: Detrix Export → Karpathy Loop
├── P0: Trace Connector ABC + JSONL (Task 1)
├── P0: Langfuse HTTP Connector (Task 2)
├── P0: TraceClassification + classify_trace (Task 3)
├── P0: Gate Proposer (Task 4)
├── P1: Gate Review CLI (Task 5)
├── P0: CLI Commands connect/propose/classify (Task 6)
├── P1: E2E Integration Test (Task 7)
├── P1: Generic Failure Pattern Miner (Task 8)
├── P1: Skill Generator (Task 9)
├── P1: Skill Validation + Holdout (Task 10)
├── P1: Skillify CLI (Task 11)
├── P2: Ratchet Loop Orchestrator (Task 12)
├── P2: Governed Training Trigger (Task 13)
├── P2: Shadow Eval for Model Promotion (Task 14)
├── P2: Local Model Serving (Task 15)
├── P2: Always-On Runtime (Task 16)
├── P2: Loop CLI (Task 17)
├── P3: Docker Packaging (Task 18)
├── P3: PyPI Release (Task 19)
└── P4: Gate Genome Registry (Task 20)
```

Phase 1 (Tasks 1-7): ~3-4 weeks → ships "Detrix Export" product
Phase 2 (Tasks 8-11): ~2-3 weeks → ships "Detrix Diagnose" with governed skillify
Phase 3 (Tasks 12-17): ~4-6 weeks → ships "Detrix Loop" — the governed Karpathy Loop
Phase 4 (Tasks 18-20): ~2-3 weeks → ships distribution + scale
