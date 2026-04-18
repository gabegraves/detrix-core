# Detrix I/O Contracts: Inputs, Outputs, and Reward Definitions

**Date:** 2026-04-18
**Status:** SPEC — approved design
**Parent:** 2026-04-18-narrow-governance-slice-design.md
**Scope:** Clear definitions of what goes in, what comes out, how we know it's right, and how we know it's improving. Applies to both V1 (AXV2 narrow slice) and V2 (generic agent harness).

---

## Why This Document Exists

The recurring failure pattern across AgentXRD_v2 and ParabolaHunter is building features
without clear input/output contracts. Gates exist but don't block. Traces exist but aren't
scored. Scoring exists but doesn't feed training. This document pins down the contracts at
every boundary so the improvement loop is structurally sound.

---

## The Four Boundaries

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   BOUNDARY 1: AGENT INPUT                                        │
│   "Here's what goes in"                                          │
│   User describes: input data, expected output, how to verify     │
│                                                                  │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────┐                            │
│   │  AGENT (Qwen 3.6 via vLLM)     │                            │
│   │  Tools + domain knowledge       │                            │
│   └─────────────────────────────────┘                            │
│        │                                                         │
│        ▼                                                         │
│   BOUNDARY 2: GATE OUTPUT                                        │
│   Multi-verdict + per-metric scores + evidence                   │
│   Each gate: verdict enum + metrics dict + passed bool           │
│                                                                  │
│        │                                                         │
│        ▼                                                         │
│   BOUNDARY 3: RLVR REWARD                                        │
│   Composite scalar = structural score + domain eval score        │
│   Per-metric scores feed GRPO group normalization                │
│   Single composite feeds autoresearch keep/discard               │
│                                                                  │
│        │                                                         │
│        ▼                                                         │
│   BOUNDARY 4: IMPROVEMENT EVIDENCE                               │
│   Benchmark pass rate delta (scientists/engineers)               │
│   Cost reduction at quality parity (buyers/investors)            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Boundary 1: Agent Input Contract

### The user describes in human words:

1. **"Here's what goes in"** — the input data and task
   - XRD example: "A powder X-ray diffraction pattern from a lab instrument"
   - Trading example: "Real-time options flow data and Greek exposure for SPY"

2. **"Here's what should come out"** — the expected output format and content
   - XRD example: "A list of crystal phases with weight fractions and confidence scores"
   - Trading example: "A trade recommendation with entry, stop-loss, target, and position size"

3. **"Here's how you know it's right"** — the verifiable reward description
   - XRD example: "Rietveld refinement R_wp below 15%, lattice parameters within 3% of CIF"
   - Trading example: "Backtest Sharpe above 1.5, max drawdown under 10%, win rate above 55%"

### Translation methods (A/B test all three):

**Method A: LLM generates, user validates**
- Harness uses frontier model (Claude) to generate gate code from the description
- User reviews generated evaluation functions and approves/corrects
- Most automated, least user effort after initial description

**Method B: Structured interview**
- Harness asks targeted questions: "What does a bad output look like?"
  "What numeric threshold means failure?" "What data format?"
- Builds contract from answers
- Most guided, lowest hallucination risk

**Method C: Example-driven**
- User provides 3-5 good outputs and 3-5 bad outputs
- Harness infers evaluation criteria from examples
- Most intuitive for domain experts who "know it when they see it"

**Evaluation of which method works best:** Run all three on the same domain task.
Measure: does the generated gate correctly identify good vs bad outputs on held-out
examples? The method with highest gate accuracy wins. This is RLVR applied to the
harness's own onboarding flow.

### Structured input contract (what the harness receives):

```python
@dataclass
class TaskContract:
    """What the user provides to set up a governed agent run."""

    # Human descriptions (natural language)
    input_description: str        # "A powder XRD pattern..."
    output_description: str       # "Crystal phases with weight fractions..."
    reward_description: str       # "R_wp below 15%, lattice within 3%..."

    # Structured fields (derived from descriptions or provided directly)
    input_schema: dict | None     # JSON schema for input data (optional)
    output_schema: dict | None    # JSON schema for expected output (optional)
    evaluation_fn: Callable | None  # Python function: (output) -> float (optional)

    # Domain metadata
    domain: str                   # "xrd", "trading", "pharma"
    domain_pack: str | None       # registered domain pack name (optional)

    # Examples (for Method C)
    good_examples: list[dict]     # 3-5 examples of correct outputs
    bad_examples: list[dict]      # 3-5 examples of incorrect outputs
```

### Three-mode harness (adopted from CascadeFlow):

| Mode | Behavior | Use case |
|---|---|---|
| `off` | Agent runs with no governance. Traces collected but not scored. | Baseline measurement |
| `observe` | Gates run but don't block. Scores recorded. Thresholds calibrate. | Threshold discovery |
| `enforce` | Gates block. Bad outputs stopped. Traces scored and admitted. | Production |

Users start in `observe`, calibrate from real data, switch to `enforce`. Matches
Detrix's observer-first principle.

---

## Boundary 2: Gate Output Contract

### Per-gate output (what every gate returns):

```python
@dataclass
class GateOutput:
    """Standard output from any governance gate, any domain."""

    # Verdict (human-readable decision)
    verdict: GateVerdict           # ACCEPT | REJECT | CAUTION | UNKNOWN | REQUEST_MORE_DATA

    # Binary (structural)
    passed: bool                   # True if verdict in {ACCEPT, CAUTION}

    # Scores (RLVR signal)
    score: float                   # 0-1, overall gate score
    metrics: dict[str, float]      # Named per-metric scores
                                   # XRD: {"snr": 0.8, "peak_count": 0.95, "r_wp": 0.72}
                                   # Trading: {"sharpe": 0.85, "drawdown": 0.92, "win_rate": 0.73}

    # Evidence (audit trail)
    reason_codes: list[str]        # ["low_snr", "step_size_warning"]
    evidence: dict[str, Any]       # Full structured proof
    recommended_actions: list[str] # ["provide_better_scan", "add_chemistry_prior"]

    # Provenance
    gate_id: str                   # "xrd.metrology"
    gate_version: str              # "1.2.0"
    config_hash: str               # SHA256 of gate threshold config
    evaluation_time_ms: float      # How long the gate took
```

### Why multi-verdict + per-metric (not binary):

| Need | How per-metric scores serve it |
|---|---|
| GRPO group normalization | Per-metric scores provide dense per-step signal. "Almost passed" (0.89) gets different advantage than "completely wrong" (0.12). Binary pass/fail can't distinguish. |
| Autoresearch keep/discard | Composite scalar (weighted sum of per-metric scores) = the single number for keep/discard. Like Karpathy's val_bpb. |
| Skill evolver | Reason codes + evidence explain WHY the gate failed. The skill evolver needs this to generate corrective behavioral rules. |
| Regression detection | Per-metric deltas show WHERE a regression happened (SNR got worse vs R_wp got worse), not just that the composite dropped. |
| Langfuse traces | Per-metric scores attach as Langfuse evaluations. Human inspects which specific metric degraded. |

### Domain pack evaluator contract (what domain packs implement):

```python
class DomainEvaluator(ABC):
    """The RLVR verifiable reward. Domain-specific. The moat."""

    @property
    @abstractmethod
    def domain(self) -> str: ...

    @property
    @abstractmethod
    def evaluator_id(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def evaluate(self, data: Any, **kwargs: Any) -> GateOutput:
        """Run domain-specific evaluation.

        INPUT:  agent output at a step (any format the domain understands)
        OUTPUT: GateOutput with score, metrics, verdict, evidence

        The harness doesn't need to know what R_wp means.
        It just needs a float, a dict of named floats, and a boolean.
        """
        ...
```

---

## Boundary 3: RLVR Reward Contract

### Two components:

**Structural score (domain-agnostic, computed by harness):**
```python
def structural_score(gate_outputs: list[GateOutput]) -> float:
    """Fraction of gates passed. Any domain. Automatic."""
    if not gate_outputs:
        return 0.0
    return sum(1 for g in gate_outputs if g.passed) / len(gate_outputs)
```

**Domain eval score (domain-specific, from DomainEvaluator):**
```python
def domain_eval_score(gate_outputs: list[GateOutput]) -> float:
    """Weighted average of per-metric scores from domain gates."""
    all_scores = []
    for gate in gate_outputs:
        all_scores.append(gate.score)
    return sum(all_scores) / max(len(all_scores), 1)
```

### Composite reward (the RLVR verifiable reward):

```python
def governance_reward(
    structural: float,       # gate pass rate (0-1)
    domain_eval: float,      # domain evaluator composite (0-1)
    weights: tuple[float, float] = (0.3, 0.7),
) -> float:
    """Single scalar for GRPO and autoresearch.

    Default: 70% domain eval, 30% structural.
    Domain eval is weighted higher because it's the authoritative signal.
    Structural score prevents gaming (pass the eval but skip gates).
    """
    return weights[0] * structural + weights[1] * domain_eval
```

### Per-step reward (for GRPO dense signal):

```python
def step_reward(gate_output: GateOutput) -> dict:
    """Per-step reward for GRPO group normalization."""
    return {
        "score": gate_output.score,
        "metrics": gate_output.metrics,   # named floats for rich signal
        "passed": gate_output.passed,
    }
```

### How rewards flow to training:

```
Per-step GateOutputs
    │
    ├── step_reward() per gate ──────────────► GRPO per-step advantages
    │                                          (dense signal within groups)
    │
    ├── governance_reward() composite ───────► Autoresearch keep/discard
    │                                          (single scalar, like val_bpb)
    │
    └── GovernedTrajectory.governance_score ──► Training bridge filter
                                                (admission: clean only)
```

### Training tools:

| Tool | Use case | Hardware |
|---|---|---|
| **Unsloth** | LoRA fine-tuning (fast, memory-efficient) | RTX 6000 Pro (Blackwell) |
| **OpenPipe ART** | Agent Reinforcement Trainer (GRPO on agent traces) | RTX 6000 Pro (Blackwell) |
| **TRL GRPOTrainer** | Fallback if Unsloth/ART don't support specific config | RTX 6000 Pro (Blackwell) |
| **vLLM** | Model serving (Qwen 3.6 inference during training generation) | RTX 6000 Pro (Blackwell) |

**Hardware:** All training on RTX 6000 Pro (Blackwell, 98GB). 3090s are not used for
training. vLLM server mode on one Blackwell, training on the other (when second arrives)
or time-shared on one.

---

## Boundary 4: Improvement Evidence Contract

### Primary metrics (for paper, pitch deck, customer demos):

**Metric B: Benchmark pass rate delta**
```
BEFORE: Qwen 3.6 on 50 XRD benchmark cases → 34 ACCEPT (68%)
AFTER:  Qwen 3.6 + 1 overnight GRPO run    → 43 ACCEPT (86%)
DELTA:  +9 cases, +18 percentage points

"Your agent went from 68% to 86% accuracy on the XRD benchmark."
```

Who cares: scientists, engineers, domain experts. This is the number in the paper.

**Metric C: Cost reduction at quality parity**
```
BASELINE: GPT-5 API at $0.03/run, 85% pass rate
AFTER:    Qwen 3.6 local at $0.0003/run, 83% pass rate (within 2%)
SAVINGS:  100x cost reduction, <3% quality loss

"Same quality, 1/100th the cost. Runs on your hardware."
```

Who cares: buyers, investors, CFOs. This is the number in the pitch deck.

### Secondary metrics (internal, for debugging and tuning):

| Metric | What it measures | Who uses it |
|---|---|---|
| Governance composite score delta | Internal reward improvement | Training engineer |
| Per-gate pass rate delta | Which specific gates improved | Domain pack developer |
| Regression count | Cases that passed before but fail after training | Regression gate (automated) |
| Cost per governance point | Training compute cost per unit of improvement | Business model |
| Time to convergence | How many overnight cycles to reach target quality | Operations planning |
| Skill evolver hit rate | % of extracted skills that actually improve performance | Skill evolver tuning |

### Improvement evidence format (what gets persisted):

```python
@dataclass
class ImprovementReport:
    """Evidence that the system got better. Persisted per training run."""

    # Identity
    report_id: str
    training_run_id: str
    model_before: str             # "qwen3.6-xrd-v2"
    model_after: str              # "qwen3.6-xrd-v3"

    # Primary metrics
    pass_rate_before: float       # 0.68
    pass_rate_after: float        # 0.86
    pass_rate_delta: float        # +0.18
    cost_per_run_before: float    # $0.03 (frontier API)
    cost_per_run_after: float     # $0.0003 (local)
    cost_reduction_factor: float  # 100x

    # Secondary metrics
    governance_score_before: float
    governance_score_after: float
    per_gate_deltas: dict[str, float]  # gate_id → pass rate delta
    regression_count: int              # cases that got worse
    regression_ids: list[str]          # which specific cases regressed
    training_cost_usd: float           # compute cost of this training run
    training_duration_hours: float
    traces_used: int                   # how many clean traces fed training
    traces_rejected: int               # how many were quarantined (admission)

    # Provenance
    policy_before: PolicyTuple
    policy_after: PolicyTuple
    benchmark_version: str        # which benchmark was used
    timestamp: datetime
```

---

## XRD Domain Pack I/O (Concrete Example)

### Input:
```
Human description: "A powder X-ray diffraction pattern in XY format from a
Bruker D8 Advance with Cu-Ka radiation"

Structured:
  input_schema: {two_theta: list[float], intensity: list[float]}
  instrument: "Cu-Ka, Bruker D8"
  goal: "enumerate" | "confirm" | "quantify"
```

### Expected output:
```
Human description: "A list of crystal phases identified in the sample, each with
a confidence score, weight fraction, and refined lattice parameters"

Structured:
  output_schema: {
    phases: [{name: str, confidence: float, weight_fraction: float,
              lattice_params: {a, b, c, alpha, beta, gamma}}]
    verdict: "ACCEPT" | "SET" | "UNKNOWN" | "REQUEST_MORE_DATA"
  }
```

### Reward (verifiable, deterministic):
```
Human description: "The Rietveld refinement R_wp should be below 15%.
Lattice parameters within 3% of reference CIF values. At least one phase
must have confidence above 0.8."

Gate metrics:
  metrology_gate:     {snr: float, peak_count: int, scan_span: float}
  confidence_gate:    {min_confidence: float, ece: float, ensemble_std: float}
  refinement_gate:    {r_wp: float, fom: float, lattice_deviation: float}
  plausibility_gate:  {weight_fraction_sum: float, lattice_plausibility: float}
```

### Improvement evidence:
```
Pass rate: 34/50 → 43/50 (+18%)
Cost: $0.03/run (GPT-5) → $0.0003/run (Qwen 3.6 local) = 100x reduction
Per-gate: metrology +5%, confidence +12%, refinement +22%, plausibility +8%
Regressions: 1 case (sample_17, previously ACCEPT, now SET — ambiguous multi-phase)
```

---

## ParabolaHunter Domain Pack I/O (Future, V2)

### Input:
```
Human description: "Real-time options flow data, Greek exposure, and IV surface
for a given ticker"

Structured:
  input_schema: {ticker: str, flow: list[OptionTrade], greeks: GreekExposure}
```

### Expected output:
```
Human description: "A trade recommendation: direction, entry, stop, target,
position size, and confidence"

Structured:
  output_schema: {
    direction: "long" | "short" | "pass",
    entry: float, stop: float, target: float,
    size: float, confidence: float
  }
```

### Reward:
```
Human description: "Backtest Sharpe above 1.5. Max drawdown under 10%.
Win rate above 55%. No trades on fallback-priced contracts."

Gate metrics:
  signal_gate:     {sharpe: float, sortino: float, win_rate: float}
  risk_gate:       {max_drawdown: float, var_95: float, position_concentration: float}
  execution_gate:  {slippage: float, fill_rate: float}
  provenance_gate: {pricing_source: "live" | "fallback", data_staleness_seconds: int}

CRITICAL: provenance_gate rejects any trace with pricing_source == "fallback".
This is the trace admission issue Codex identified.
```

---

## Corrections to Main Spec

The following changes should be applied to `2026-04-18-narrow-governance-slice-design.md`:

1. **Training hardware:** Replace "3x 3090 (FSDP)" with "RTX 6000 Pro (Blackwell)"
2. **Training tools:** Replace "TRL GRPOTrainer" primary with "Unsloth and/or OpenPipe ART.
   TRL as fallback."
3. **Training focus:** RLVR + GRPO + Hermes-style auto skill creation. Not SFT-heavy.
4. **Pi-mono fork:** Move from V2 to parallel goal. Fork and modify for agent harness
   reliability. Not deferred — runs alongside V1 governance slice.
5. **CascadeFlow patterns:** Add three-mode harness (off/observe/enforce) and lazy imports
   to the design.
6. **Gate output format:** Adopt GateOutput contract from this document (score + metrics
   dict + verdict + evidence).

---

## Sources

- AgentXRD_v2 governance gates (7 gates, all wired)
- MetaClaw (2603.17187): skill evolver, OMLS, support-query versioning
- Agent-RLVR (2506.11425): dense reward superiority
- CascadeFlow (lemony-ai/cascadeflow): three-mode harness, lazy imports, composite validators
- Karpathy autoresearch: single scalar metric for keep/discard
- Pi-mono (badlogic/pi-mono): agent loop architecture (parallel goal fork)
- Codex adversarial review (2026-04-18): trace admission, version tuples, single-writer
