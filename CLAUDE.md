# Detrix Core

Make domain-specific agents reliable enough to deploy and cheap enough to scale.

## Design Doc (READ FIRST)

**Full strategy, competitive analysis, architecture, and build plan:**
`~/.gstack/projects/gabegraves-detrix-core/gabriel-main-design-20260331-022621.md`

This design doc is the source of truth for positioning, monetization, competitive landscape, and build order. Updated 2026-03-31 via YC office hours session with Codex cross-model review and market research.

## Mission

Make domain-specific agents reliable enough to deploy and cheap enough to scale.

## Identity (resolved 2026-03-31, Claude + Codex consensus)

Detrix is a **reliability and improvement runtime for domain-specific agents**. It validates outputs with domain physics, blocks bad results, learns from failures, and improves both the harness and the model over time. Three framings for three audiences:

| Audience | Framing | Example |
|----------|---------|---------|
| Research / papers | RLVR environment with dual-axis improvement | "Domain-physics verifiable rewards for agent training" |
| Technical buyers / ML engineers | Self-improving agent harness with domain physics gates | "Give me your agent on GPT-5, I give you back a 7B at 1/100th cost with quality guarantees" |
| Acquirers / investors / elevator | Reliability and improvement runtime | "We turn unreliable domain agents into governed systems you can trust, and make them cheaper every week" |

**In plain English:** Detrix sits around a specialist AI agent, checks whether each answer is actually correct using hard domain tests, blocks bad outputs, records what failed, and uses that evidence to make the workflow and the underlying model better over time. It turns a clever but unreliable agent into a governed system that can be trusted in a real domain, and it keeps reducing cost by teaching smaller models to do the validated work.

**How reliability works (the closed loop):**
1. Agent output → deterministic domain evaluator scores it (not LLM, not human)
2. Bad output → BLOCKED (not "kind of okay")
3. Short loop → harness changes prevent same failure class from recurring (hours)
4. Long loop → validated traces train cheaper model via SFT/DPO (overnight)
5. Promotion gated → new harness or model ships ONLY if it beats incumbent on held-out domain evals

**What Detrix is NOT:** a methodology company. If you call it a methodology company, you are telling acquirers they can copy the idea and skip buying you. It is a product company with a proprietary method. The method is the moat. The product is the thing being bought.

**Internally, the engine is RLVR** (Reinforcement Learning with Verifiable Rewards). Domain physics evaluation IS the verifiable reward. Two optimization targets in the same environment: harness code (Axis 1, hours) and model weights (Axis 2, overnight). DeepSeek-R1 proved RLVR > RLHF for math/code. Detrix extends RLVR to domains where the verifier runs physics, not test cases.

Detrix wraps existing frameworks (LangGraph, LangChain, CrewAI, raw Python) — it does not replace them. Unsloth/ART handle training execution (complementary, already in stack). Domain packs (starting with AgentXRD for materials science) prove the stack works.

## Positioning (READ THIS SECOND)

**Detrix is an RLVR environment for domain-specific agents.** RLVR = Reinforcement Learning with Verifiable Rewards. DeepSeek-R1 proved RLVR works for math/code (test cases as verifier). Detrix extends RLVR to R&D and engineering domains where verification requires domain physics, not test cases. The dual-axis improvement loop (harness optimization + model distillation) uses verifiable domain rewards as the shared training signal.

- **We are NOT:** another DAG executor, another YAML pipeline tool, another LangGraph competitor, another OpenPipe, another tracing/observability tool, another training UI (that's Unsloth, which we use)
- **We ARE:** an RLVR environment that provides domain-physics verifiable rewards for agent training + a dual-axis improvement loop (harness optimization + model distillation) that uses those rewards to make agents reliable and cheap
- **RLVR framing:** Environment = agent pipeline. Action = agent output at each step. Reward = domain physics evaluation (R_wp, convergence, Sharpe). Verifiable = computed by deterministic code, not judged by LLM. Two optimization targets: harness code (fast, hours) and model weights (deep, overnight).
- **One-liner:** "RLVR environments for domain-specific agents. We provide the verifiable reward that makes your agent trainable — domain physics, not LLM opinions."
- **AutoML pitch:** "Give me your agent on GPT-5. I give you back a 7B model at 1/100th cost, with an optimized harness and verifiable quality guarantees. The improvement loop runs on your hardware."
- **Competitive line:** "OpenPipe trains on traces. Detrix trains on traces that survived domain validation. Cascade learns what usually passes (RLAIF). Detrix knows what is actually correct (RLVR)."
- **Elevator pitch:** "We tell you if your agent's output is correct, validated by domain-specific evaluation, not LLM vibes. Then we make it better automatically — both the harness (hours) and the model (overnight). Each domain gets its own verifiable reward: materials science uses Rietveld refinement, engineering uses simulation convergence, trading uses backtest consistency. The rewards become training signal. Your agent gets cheaper and more reliable every cycle."
- **Tech buyer pitch:** "RLVR environment + deterministic governance gates + domain physics rewards + dual-axis improvement (harness + model). Sits between tracing (Langfuse) and training (Unsloth/ART). The training loop is commodity. The ENVIRONMENT + REWARD FUNCTION is the moat."
- **Core pattern:** Domain-physics RLVR (verifiable rewards from deterministic evaluation) + Meta-Harness (harness optimization via coding agent with filesystem-as-feedback) + Karpathy autoresearch (parallel experimentation + overnight improvement). The environment provides the reward. The dual-axis loop consumes it.
- **Primary moat:** Domain-specific RLVR environments with physics-grade verifiable rewards. Labs have training algorithms (PPO, GRPO, SFT, DPO — commodity). They NEED environments and reward functions. Building domain-specific reward functions requires domain expertise that can't be replicated with 3 engineers and Claude Code in a quarter. Moat compounds via: accumulated experiment evidence → benchmark adoption → switching costs → platform standard.
- **Research validation:** DeepSeek-R1 (2025) proved RLVR > RLHF for math/code. Math-Shepherd (ACL 2024), AgentPRM (2025), PAV (ICLR 2025) confirm step-level verifiable process rewards produce better training signal than outcome-only or LLM-as-judge. Detrix applies this paradigm to domain-specific agents where the verifier runs physics, not test cases.

### Phase 1 identity: QUALITY INFRASTRUCTURE, VERTICAL-FIRST
- The product is domain-specific quality infrastructure, not training infrastructure. Land with quality, expand with training.
- Sell outcomes ("your agent: 5x cheaper, 3x more reliable in 30 days"), not architecture ("custom fine-tuned model").
- Three verticals the founder knows from the inside: materials science (XRD), engineering simulation, quantitative trading.
- Materials science ships first (AgentXRD, 203 source files). Second domain validates the pattern generalizes.
- Prior investor rejection (Fledgling/ATL_25) was explicitly "too horizontal, too similar to OpenPipe." Quality-first avoids that trap.
- YC narrative: "We make domain-specific agents measurably better. Started in materials science, expanding to engineering and trading."

### Competitive positioning:
- **vs OpenPipe** (commercial, acquired by CoreWeave Sep 2025): Don't run from the comparison — own it and differentiate. OpenPipe proved trace-to-fine-tune works. They trained on everything (generic traces, LLM-as-judge quality). We train on traces that survived domain validation (physics-evaluated, governance-scored). Same loop, structurally better signal. OpenPipe got absorbed because "trace → fine-tune" has no domain lock-in. Detrix is unabsorbable if the domain evaluator is the moat. The Fledgling rejection was "you're similar to OpenPipe **and we can't see the difference**" — the governance spec + domain evaluator IS the visible difference.
- **vs Cascade** (YC W26, CLOSEST competitor): Trains org-specific evaluator models from production agent runs. Closed observe→learn→evaluate→improve loop. BUT: evaluators are learned behavioral patterns, not domain physics. Can't validate Rietveld — only that output matches historical approval patterns. Wins in domains WITHOUT computable ground truth (support, legal, content). We win in domains WITH it (materials, simulation, trading). ~6mo ahead on execution. Race is: ship governance gates before they figure out domain-specific physics eval produces better signal.
- **vs Paperclip** (36.6k stars, MIT): Organizational OS for AI agent teams — org charts, budgets, task hierarchies, multi-agent coordination, heartbeat scheduling. Different layer (coordination vs quality) but overlapping patterns. Paperclip coordinates WHO works on what. Detrix validates WHETHER the output is correct. Complementary: a Paperclip-managed agent team could use Detrix as the quality layer.
  - **Borrow from Paperclip:** (1) Heartbeat + persistent state pattern for autonomous operation — agents resume context across runs, SQLite-backed instead of their PostgreSQL. (2) Immutable audit logs with full tool-call tracing — maps to Tier 3 agent audit. (3) Config versioning + rollback UX pattern — apply to evaluator/gate/model versioning.
  - **Where Detrix goes further:** Domain physics evaluation (they can't validate Rietveld). Self-improving models from governance-scored traces (their agents don't get better from running). Deterministic gates that block bad outputs (their approval gates are organizational, not domain-specific).
- **vs LangSmith** (commercial): They do observability SaaS. We do governance + improvement baked into runtime.
- **vs MetaClaw** (MIT, UNC AIMING Lab, 2026): Self-improving agent proxy — intercepts conversations, injects skills, trains weights via GRPO. Closest OSS analog to Detrix's improvement loop. BUT: quality signal is LLM-as-judge (learned PRM), not domain physics (ground truth). No governance gates — never blocks bad outputs. Improves conversational agents, not structured domain pipelines. No audit trail for regulated industries. MetaClaw asks "does this look right?" Detrix asks "IS this right?" and proves it with physics.
  - **Borrow from MetaClaw (MIT):** (1) OMLS scheduler — train during idle windows, not during serving. (2) Skill auto-extraction — session → skill summary, apply to domain pack auto-generation v2. (3) Contexture memory layer — cross-session persistence for Detrix memory MVP. (4) GRPO training backend (Tinker) — for v3 RL if SFT/DPO plateau.
  - **Where MetaClaw is better today:** ships skill auto-evolution, ships memory layer (Contexture v0.4.0), ships GRPO training, zero-config improvement via proxy. Detrix requires defining domain evaluators upfront (that's the moat, not a weakness).
- **vs El Agente** (Zou et al. 2025, Matter/Cell Press): Autonomous LLM agent for quantum chemistry. Demonstrates the EXACT type of agent that needs Detrix: runs complex scientific workflows autonomously but has NO quality gates, NO self-improvement, NO governance. >87% success rate means 13% uncaught failures. If El Agente were wrapped in Detrix, you'd catch the bad DFT calculations, block them, and train a cheaper model from the good ones. El Agente is the agent. Detrix is the quality layer the agent needs. Same relationship applies to any autonomous scientific agent (agentic synchrotron, autonomous labs, etc.).
- **vs Unsloth Studio** (OSS, beta): No-code training UI. Data Recipes transforms docs into datasets. Model Arena for manual side-by-side chat comparison. 500+ architectures. Unsloth trains on whatever you give it with zero idea if the data is good or the result is correct. Its "evaluation" is manual chat comparison. Detrix is the intelligence layer above: (1) domain physics gates filter traces into quality-scored training data before Unsloth trains on them, (2) harness optimization is an axis Unsloth doesn't have at all, (3) automated quality-gated promotion decides whether to deploy based on domain evaluation, not vibes. Unsloth = HOW to train. Detrix = WHAT to train on + WHETHER to deploy. Complementary, not competitive. Already in our stack.
- **vs TensorZero, autoresearch** (open-source MIT/Apache-2.0): Component sources — cherry-pick what works. TensorZero: LLM gateway patterns, experimentation framework. Autoresearch: propose-train-evaluate loop, single-GPU approach.
- **Vertical expansion test:** "Can I write a Python function that returns a float measuring correctness using only the output and domain computation — no LLM, no human?" If yes → Detrix territory. If no → Cascade territory. Walk away.

### Reliability pattern: Stripe Blueprints + Domain Physics Gates

**How Stripe ensures agent reliability (Minions, Feb 2026):** A Blueprint is a state machine where deterministic code nodes alternate with agentic LLM nodes. The orchestrator runs deterministic nodes unconditionally — the LLM never decides whether to run a gate. The agent cannot skip, override, or negotiate. This is structural enforcement, not policy.

Sources: [Stripe Dev Blog Part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents) (Feb 9 2026), [Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2) (Feb 19 2026). Not open-source — internal system built on a fork of Goose (Block, MIT).

**How Detrix applies the pattern:** Same structural enforcement, different gate content. Stripe's gates check code quality (lint, CI, PR format). Detrix's gates check domain physics (Rietveld R_wp, DFT convergence, backtest Sharpe). Anyone can build the state machine. Nobody else has the domain physics gates.

```
Detrix reliability loop (Stripe Blueprints + domain physics RLVR):

[AGENTIC]  Agent runs step (e.g., XRD phase identification)
      |
[DET GATE] MetrologyGate: R_wp < threshold? Lattice params physical?
      | PASS → continue          | FAIL → block + log trace
[AGENTIC]  Agent runs next step (e.g., refinement)
      |
[DET GATE] RefinementQualityGate: convergence? chi-squared acceptable?
      | PASS → continue          | FAIL → block + retry/escalate
[AGENTIC]  Agent produces final output
      |
[DET GATE] ConfidenceGate: ensemble agreement? final verdict
      | PASS → deliver           | FAIL → human review
```

**Five enforcement properties (borrowed from Stripe, extended for domain physics):**
1. **Agent cannot skip gates** — orchestrator runs them unconditionally between agentic phases
2. **Tool scoping per phase** — each agentic node gets only relevant tools (no access to output delivery before passing gates)
3. **Bounded retries** — max N attempts before escalation to human review (no infinite loops)
4. **Failed traces stored with full context** — exact input, output, score, failure mode → becomes RLVR training data
5. **Terminal gate** — final output requires domain physics pass, never just LLM confidence

**Why NOT hooks/middleware:** Hooks fire pre/post on each step but don't control flow. The agent can emit output before the hook fires. A state machine with structural gates guarantees no output propagates without passing the deterministic node. Hooks are advisory. Gates are structural. This is the key distinction.

**Why NOT pipeline validators:** Too late. Pipeline validators post-process at the end. By then, bad intermediate results have already propagated through downstream steps, corrupting the trace. Step-level gates between agentic phases catch errors where they occur.

### Key differentiators:
1. **Observer → Enforcer runtime** — attach to any pipeline, observe execution, calibrate gates from real data, then enforce. No uncalibrated blocking. Stripe Blueprints pattern deployed via data-driven calibration, not upfront specification. Phase 1: observe and log verdicts. Phase 2: activate blocking on calibrated gates.
2. **Deterministic-first governance** — if physics/math can verify it, always deterministic code, never LLM. AgentXRD_v2 already implements: metrology guard, quality gates, verdict contract, FSM pipeline. LLM-as-judge is advisory Tier 2 only.
3. **Dual-axis self-improvement** — two improvement axes sharing one reward signal (domain physics evaluation):
   - **Axis 1: Harness optimization (hours, no GPU)** — Meta-Harness pattern (Lee, Nair, Zhang, Lee, Khattab, Finn 2026; https://yoonholee.com/meta-harness/). Coding agent proposes harness improvements (prompt construction, retrieval logic, memory management). Full execution traces as feedback (10M tokens/iter, not summaries — summaries actively hurt by compressing away causal information). Filesystem-as-feedback-channel: all prior candidates' source code, scores, and traces stored as flat files the proposer can browse via shell tools. Proposer: Claude Code / Codex initially, transition to local model once traces inform what's needed.
   - **Axis 2: Model distillation (overnight, local GPUs)** — ART pattern (Apache-2.0). Generate N completions → score with domain gates → train on best via Unsloth. Replace frontier model with domain-tuned 7B-14B at 1/100th inference cost. Challenger model evaluated through same gates before promotion. SFT (v1) → DPO (v2) → GRPO (v3 if needed).
   - **Why both:** Harness optimization is fast but bounded by model capability. Model distillation is deep but bounded by harness quality. Together they compound. Neither alone covers the full improvement surface.
4. **Domain packs** — pluggable expert workflows. First: AgentXRD (materials science, 203 source files). Each pack defines its own gates, evaluators, and training data format.
5. **Domain-specific active evaluation** — the evaluator runs domain validation (Rietveld refinement, ADMET filters), not just LLM text judging. Coding agents can parse your data. They can't tell you if the phase assignment is physically valid.
6. **Versioned governance artifacts** (internal infrastructure, not customer-facing differentiator) — evaluators, gates, thresholds, and trajectories are versioned and content-addressable. Required for: reward drift detection, shadow evaluation before promotion, rollback on regression. Without versioning, the self-improving loop corrupts itself. But versioning is plumbing (every tool does it), not a selling point. Lead with governance + domain eval.

### Governance Spec (implementation reference)
`docs/governance-spec.md` — VerdictContract, GovernanceGate ABC, DomainEvaluator ABC, pipeline integration, versioning layer, trajectory schema, MVP build order. Cross-model validated (Claude + Codex, 2026-03-28).

### Training strategy (ART pattern — RL-informed SFT from day one):
OpenPipe ART (Apache-2.0, github.com/OpenPipe/ART) is the training backbone. ART = generate N completions → score with grader → rejection sample → train on best. Detrix's governance gates ARE the grader. Use ART to ship faster, replace with custom solution only if needed.

- **v1: ART basic (rejection sampling + SFT)** — run agent N times per task, governance gates score each, train on gate-passed traces. One 3090, overnight. Ships in days.
- **v2: ART full (preference-weighted)** — gate-pass/fail pairs feed DPO-style preference weighting. Natural pairs from governance. Ships in weeks.
- **v3: ART + GRPO** — explicit RL optimization with gate composite as reward function. Only if v1-v2 plateau. Uses ART's GRPO backend (supports Qwen3.5, Llama, GPT-OSS).
- **Why ART, not custom:** The training loop is commodity. OpenPipe's founder said it himself: RL-SFT via ART is the way to go. The training SIGNAL from domain-validated governance scoring is the moat, not the training loop. Don't rebuild what's Apache-2.0.
- **Why Detrix's ART is better than OpenPipe's ART:** OpenPipe's grader is whatever the customer writes (often LLM-as-judge or simple heuristics). Detrix's grader runs Rietveld refinement, validates lattice parameters, checks convergence. That grader can't be written in 5 lines. That's the moat. Same loop, structurally better signal.

### Build order (MVP-first, iterate from data):
Build the thinnest possible observer, attach to AgentXRD_v2, run overnight, iterate from real data. Spec the eval metric (domain physics oracle), build the implementation iteratively. Karpathy autoresearch pattern: `program.md` (governance spec) is specified upfront, `train.py` (runtime implementation) evolves from experiments.

**Concrete sequence:**
1. VerdictContract + GovernanceGate ABC + DomainEvaluator ABC (spec exists, implement it)
2. Wire MetrologyGate as post-hoc observer on AgentXRD preprocessing (thin adapter)
3. Run 20+ real XRD analyses with observer attached → look at verdicts → calibrate
4. Activate enforcement on calibrated gates. Add ConfidenceGate, RefinementQualityGate.
5. Scoring bridge: verdicts → GovernedTrajectory → SFT export
6. First SFT run: Qwen2.5-7B + LoRA on gate-passed traces → shadow eval → promote
7. Wire ParabolaHunter with raw Python adapter (proves framework-agnostic)
8. Parallel experimentation: N gate configs on local GPUs, pick winner

**Anti-pattern:** Do NOT fully spec the runtime before building. Observe real failure modes from real pipelines. The data will tell you what the architecture should be. ~70% of the evaluator code already exists across AgentXRD_v2 and mission-control.

### Observer-Enforcer Brainstorm (2026-03-28)
Deep brainstorming session: 3 parallel research agents (20+ papers), 2 Codex adversarial reviews, Theo/Karpathy MVP-first analysis. Key decisions:
- **Observer-first runtime**: observe pipeline → calibrate thresholds from real data → enforce gates. Not blocking-first.
- **Deterministic-first hierarchy**: physics gates > structural gates > LLM advisory (never authoritative) > human review.
- **A+B together**: governance (A) + training loop (B) ship together on AgentXRD. Neither has value alone.
- **MVP-first build**: spec the eval metric (domain physics oracle), build thin runtime, iterate from data. Autoresearch pattern.
- **Product C (hybrid)**: auto-generated scaffolding (schema, type, range gates) + hand-built domain evaluators (physics). Layer 1 is onboarding hook, Layer 2 is moat.
- **Codex critique addressed**: "correctness is an oracle problem, not an orchestration problem" — agreed. The domain evaluator IS the product. Runtime is delivery mechanism.
- **Codex critique accepted**: hidden state in agent internals, enforcement-too-late for side effects, conservative collapse risk from Daikon-style invariant discovery. Address empirically.
- **Research validation**: Math-Shepherd (ACL 2024), AgentPRM (2025), PAV (ICLR 2025) confirm step-level governance scores produce better training signal than outcome-only. ML FMEA (SAE 2025) for automated gate placement. Adaptive constraint systems for graduated enforcement.
- **vs Cascade (YC W26)**: Cascade learns behavioral patterns. Detrix runs active experiments with physics as eval metric. Behavioral matching discovers "what usually happens." Physics evaluation discovers "what is actually correct."

### Codex Strategy Teardown (2026-03-27)
Cross-model review (OpenAI Codex) identified critical gaps. Full analysis: `docs/codex-strategy-teardown-20260327.md`

**Key actions from teardown:**
- Current detrix-core code is a YAML DAG runner with stubs, not the governance product. Close the gap.
- Stop selling infrastructure. Sell managed vertical outcomes with measurable ROI.
- Build order correction: domain evaluator and review ops FIRST, workflow instrumentation second, model-training loop last.
- Consider keeping detrix-core internal until proprietary domain signal exists. Open-sourcing thin layer advertises lack of moat.
- Expand wedge from "XRD" to "high-cost technical outputs requiring expert review with formal validation."
- "Materials + trading + engineering" is not a coherent wedge. Pick one, go deep, expand where eval machinery is reusable.

### Competitive Research (2026-03-27)
Deep 4-agent research across YC startups, big providers, OSS landscape, and moat defensibility. Full analysis: `docs/competitive-moat-research-20260327.md`

**White space confirmed:** No company found doing the specific combination: domain-specific physics evaluation + governance gates + trace-to-training + vertical domain packs. Closest: Vijil ($23M, horizontal enterprise), TensorZero ($7.3M, OSS horizontal, no domain scoring).

**Provider absorption risk: LOW if positioned on domain physics.** Structural reasons: breadth-depth tradeoff, liability exposure from domain-specific claims, GTM mismatch, lack of domain data. OpenAI RFT gets 70% of generic improvement loop but cannot validate materials physics.

**Acquisition pattern (2025-2026):** Generic horizontal infra gets absorbed (OpenPipe→CoreWeave, W&B→CoreWeave, Galileo→Alphabet, Langfuse→ClickHouse, Promptfoo→OpenAI). Domain-specific quality layers remain independent.

**Three defensible moats (ranked):**
1. Domain physics evaluation — build Rietveld evaluator FIRST, not the training loop
2. Governance-informed training signal — scored traces are structurally better training data than LLM-as-judge
3. Operational entanglement via FDE model — Palantir/Harvey playbook for Phase 1

**False moats to avoid:** generic trace-to-fine-tune (commodity), open-source core/paid cloud (gets forked), data exclusivity partnerships (renegotiable).

### Open-source strategy: Framework open, domain packs proprietary

The code is commodity. The domain intelligence is the moat. Open-source the delivery mechanism, keep the domain physics proprietary. MySQL/MongoDB model.

**Open (Apache-2.0) — `detrix-core`:**
- State machine orchestrator (Stripe Blueprints pattern)
- GovernanceGate ABC, DomainEvaluator ABC, VerdictContract
- Scoring bridge (verdicts → GovernedTrajectory → SFT export format)
- Adapter pattern (FSM, raw Python, LangGraph connectors)
- Benchmark runner CLI
- Harness optimization outer loop scaffold

**Proprietary — domain packs (e.g., `detrix-xrd`, `detrix-quant`):**
- Calibrated gate thresholds (tuned from 1000+ real analyses, not guessable)
- Domain evaluator internals (physics rules: space group constraints, thermal parameter bounds, site occupancy rules, convergence diagnostics)
- Digital twin scenarios and labeled evaluation sets
- Scored trace corpora from real pipelines
- Pre-trained domain-tuned models (LoRA weights)

**Why this is malus-proof (can't be recreated by AI reading docs):**
1. Gate STRUCTURE is open (state machine — anyone can build it). Gate CONTENT is domain physics (requires domain expertise to build AND calibrate). A cloned copy gets gates that don't know what to check.
2. Calibrated thresholds require running the experiments. Uncalibrated thresholds either block everything (useless) or pass everything (dangerous). Can't be fast-forwarded from documentation.
3. The benchmark IS the defense. Clones that evaluate against DetrixBench validate Detrix's standard-setting position. Every competitor benchmarking against you reinforces your position.
4. Evidence velocity > cloning velocity. By the time someone reads the paper and clones the framework, you've published the next set of results from 24/7 local GPU experiments.

**What this means for the repo:** `src/detrix/core/` and `src/detrix/runtime/` are open. Domain pack code lives in separate private repos (`detrix-xrd/`, `detrix-quant/`). The open core attracts contributors and establishes the standard. The domain packs generate revenue.

**Hardware advantage:** Local 2x RTX 6000 Pro + 3x 3090 + 512GB RAM = zero-marginal-cost improvement loop. Run 60 SFT experiments for the cost of 1 cloud run. Pre-build XRD Quality Benchmark from crystallographic databases. Demo on-prem for regulated customers.

**Build order correction:** Domain evaluator → governance gates → scored traces → training loop. NOT generic runtime → domain packs later.

### Scaling model: Agent-as-FDE (validated by Palantir AI FDE GA, March 2026)
In Phase 1, YOU are the FDE for the first 3-5 customers. The coding agent FDE is Phase 2+. Detrix is the RUNTIME — gates every execution, scores every session, trains overnight. Palantir validated Agent-as-FDE by shipping AI FDE to replace 1,000+ human FDEs.

### Evidence Plan (what each milestone proves)

The docs describe WHAT to build. This section defines HOW TO PROVE IT WORKS.

| Milestone | Evidence Produced | Metric | Baseline |
|---|---|---|---|
| 1. Wire MetrologyGate as observer | Gate precision/recall on 12 scenarios + 9 digital twin | Precision ≥95%, Recall ≥90% on labeled set | Current: evaluator exists but not measured as gate |
| 2. Run 20+ analyses with observer | Gate pass rate distribution, false positive rate | FP rate <5% before activating enforcement | Current: no data |
| 3. Activate enforcement | Blocked bad outputs count, escaped bad outputs count | Escape rate <10% on held-out patterns | Current: 0% blocked (no gates) |
| 4. Scoring bridge | Session score correlation with expert judgment | Spearman ρ ≥0.7 with expert ratings | Current: no scoring |
| 5. First SFT run (ART) | Before/after accuracy on held-out golden test set | ≥10% improvement in gate pass rate | Current: baseline Qwen accuracy TBD |
| 6. Domain-gated vs LLM-judged signal | Compare SFT from physics-gated traces vs LLM-scored traces | Physics-gated model passes more gates on held-out set | Proves the moat |

### AgentXRD Data Inventory (evidence base for validation)

Data exists in AgentXRD_v2 for benchmarking. This is the evidence base, not documented elsewhere.

| Asset | Count | Location | Purpose |
|---|---|---|---|
| CIF reference files (COD) | 2,521 | `data/cod_cifs/` | Reference crystal structures for retrieval/refinement |
| CIF reference files (curated) | 331 | `data/thesis_niti/assets/cif_library/` | High-quality curated reference set |
| Metrology guard scenarios | 12 | `data/eval/metrology_guard_scenarios_v1.json` | Labeled gate precision/recall evaluation |
| Digital twin metrology | 9 | `data/eval/metrology_guard_digital_twin_v1.jsonl` | Synthetic scenarios for gate testing |
| Paper evidence bridge | 1 file | `data/eval/paper_nitihf_evidence_bridge_v1.json` | Validation with verdict contracts |
| AB test results | 12 JSON | `results/ab_test/` | Ground truth comparison infrastructure |
| Golden test set v3 | present | `data/golden/v3/` | Held-out evaluation patterns |
| Metrology guard tests | 7 test files | `tests/unit/test_metrology_guard*.py` | Existing test coverage for first gate |

**XRD Quality Benchmark (to build):** Combine golden test set + COD references + labeled scenarios into a published benchmark. Score: composite gate pass rate (metrology + confidence + refinement quality). Baseline numbers produced by milestone 2. This is the credibility artifact for investors, customers, and papers.

### Autonomous Science Agents as Customers (not competitors)

Autonomous science agents are shipping with ~79% accuracy and no automated quality evaluation. These are the ideal Detrix customers:

| System | What it does | Accuracy | Quality gates? | Detrix opportunity |
|---|---|---|---|---|
| **Kosmos** (materials, synchrotron) | Autonomous characterization at beamlines | ~79% | None | Wrap with Rietveld gates, catch the 21% |
| **Sakana AI Scientist-v2** | Autonomous scientific paper generation | ICLR workshop accepted | LLM self-review only | Domain physics gates on experimental claims |
| **Google AI Co-Scientist** | Hypothesis generation + validation | Unknown | Internal only | Quality layer for external deployment |
| **Virtual Lab** (Stanford) | Multi-agent scientific research | Paper-quality | Peer review simulation | Deterministic domain validation |
| **El Agente** (quantum chem) | NL → quantum chemistry workflows | >87% | None | DFT convergence gates |

**Pitch to this market:** "Your autonomous science agent is 79% accurate. The 21% it gets wrong could invalidate a paper, waste a synchrotron session, or miss a phase. Detrix catches the bad outputs with domain physics, not LLM opinions, and trains the agent to make fewer mistakes tomorrow."

### Enterprise Infrastructure (from user demand signals):
Real-world agent deployments need "everything around the model" that nobody talks about:
- **Tenant-aware data access:** Agents need DB access with RBAC, row-level filters, audit logs — not raw creds. Patterns: mTLS, JWT passthrough, thin REST layer (DreamFactory-style) over SQL so tools never see direct connections. Detrix gates can enforce data access boundaries as structural gates.
- **Incident detection:** GPU OOM storms, runaway tool loops, queue collapse, poisoned embeddings. Observer phase detects these as anomalies in gate pass rates and step durations. Circuit breakers = governance gates that halt on anomaly.
- **Compliance for on-prem:** Self-hosted setups have different failure modes than SaaS LLMs. Detrix's local-first (SQLite), versioned audit trail, and deterministic gates map directly to compliance requirements (SOC2, HIPAA audit trails, FDA 21 CFR Part 11 for pharma).
- **Agent containment:** "How to stop prompt-level exfil" — Tier 3 agent audit (did the agent do what it claimed?) catches tool calls that don't match intent. Structural gates validate output schemas before delivery.
- **NOT v1 scope** but informs product roadmap. The observer runtime naturally surfaces these issues; enforcement is where the product value lives.

### Framework strategy:
- Detrix is NOT a framework. It WRAPS frameworks via adapters.
- `detrix.adapters.langgraph` — first customer-facing adapter (LangGraph is dominant)
- `detrix.adapters.fsm` — for AgentXRD's custom FSM (proves framework-agnostic)
- Don't rewrite AgentXRD or ParabolaHunter in LangGraph. They have working implementations.

## Build / Test / Run
- `uv run pytest` — run all tests
- `uv run ruff check .` — lint
- `uv run mypy src/detrix` — type check
- `uv run detrix run examples/seed_pipeline.yaml -v` — smoke test CLI
- `uv sync` — install deps (never pip)

## Architecture

### Runtime Model: Observer → Enforcer → Improve

Detrix attaches as a sidecar runtime to any pipeline via adapters. Three phases:

```
Phase 1: OBSERVE (default on first attach)
  Pipeline runs normally. Detrix hooks step boundaries via adapter.
  Every step output → domain evaluator scoring (post-hoc, advisory)
  Every verdict → SQLite audit log (VerdictContract)
  Discovers invariants from traces. FMEA risk scores per step.
  Output: reliability report + proposed gate config + calibrated thresholds

Phase 2: ENFORCE (activated per-gate after calibration)
  Gates switch advisory → blocking. Deterministic-first hierarchy:
    PHYSICS: domain math (Rietveld R_wp, convergence, backtest Sharpe) — ALWAYS deterministic, never LLM
    STRUCTURAL: schema, type, range — deterministic block
    ADVISORY: LLM-as-judge — scores only, NEVER blocks, never authoritative
    HUMAN: pause pipeline for expert review
  Gate-passed traces → GovernedTrajectory (positive training signal)
  Rejected traces → classified (input_quality vs output_quality for DPO)

Phase 3: IMPROVE (overnight loop, autoresearch pattern)
  Scored trajectories → SFT (v1) → DPO (v2) → GRPO (v3 if needed)
  Challenger model → shadow eval through same gates → promote if better
  Gates recalibrate from new performance distribution
  Parallel experimentation: N gate configs on local GPUs, pick winner
```

### Deterministic-First Hierarchy (core design axiom)

If the answer is checkable by deterministic math/physics, ALWAYS use deterministic code. Never LLM.
```
1. Physics/math verifiable? → Deterministic gate (Rietveld, convergence, backtest)
2. Structurally verifiable? → Deterministic gate (schema, type, range)
3. Only semantic judgment?  → LLM advisory (scores, never blocks)
4. Not verifiable?          → Human-in-the-loop checkpoint
```

### Autonomous Operation (Paperclip/OpenClaw pattern)

Detrix runs autonomously. The full observe → enforce → improve loop operates without human intervention once configured. Modeled on Paperclip's heartbeat scheduling and OpenClaw's autonomous agent execution.

```
Autonomous loop (overnight, recurring):
  1. HEARTBEAT: Detrix agent wakes on schedule (cron or event-driven)
  2. OBSERVE: Runs queued pipeline jobs, scores all outputs post-hoc
  3. ENFORCE: Calibrated gates block bad outputs automatically
  4. SCORE: Three-tier scoring (physics + LLM advisory + agent audit)
  5. TRAIN: SFT/DPO on governance-scored traces (local GPUs, zero cloud cost)
  6. EVALUATE: Challenger model through same gates as incumbent
  7. PROMOTE/ROLLBACK: Better model promotes. Regression rolls back. Versioned.
  8. RECALIBRATE: Gates adjust thresholds from new performance distribution
  9. RESUME: Persistent state across heartbeats — agents remember prior context
  10. REPEAT: Next heartbeat picks up where this one left off
```

**Human role:** Define what "correct" means (write the domain evaluator). Set the schedule. Review the reliability report. Override when needed. The runtime does the rest.

**Borrowed from Paperclip:** Heartbeat scheduling, persistent agent state across runs, immutable audit trail, config versioning + rollback. Applied to quality infrastructure instead of organizational coordination.

### Five-Layer Stack

Governance Rails is THE product. Everything above is bundled or sold as add-ons.
```
┌───────────────────────────────────────────────────────────┐
│  DOMAIN PACKS (first: AgentXRD, subscription Phase 3)     │
│  Domain-specific gates, evaluators, training configs      │
├───────────────────────────────────────────────────────────┤
│  IMPROVEMENT LOOP (managed service, $8-15K/mo)            │
│  v1: SFT + LoRA → v2: DPO → v3: GRPO if needed           │
│  Autoresearch: parallel experiments, overnight, local GPUs│
├───────────────────────────────────────────────────────────┤
│  SESSION SCORING (mission-control pattern)                │
│  Tier 1: Deterministic mechanical grading (per-step)      │
│  Tier 2: LLM-as-judge (per-session, advisory only)        │
├───────────────────────────────────────────────────────────┤
│  MEMORY LAYER (not yet implemented)                       │
│  MVP: append-only + KV retrieval                          │
│  Future: BM25 + semantic + graph recall                   │
├───────────────────────────────────────────────────────────┤
│  GOVERNANCE RAILS (Detrix Core — open-source, free)       │
│  Observer→Enforcer runtime + Stripe Blueprints gates      │
│  Provenance, audit trail, verdict contracts, versioning   │
│  Adapters: FSM (AgentXRD), raw Python, LangGraph          │
└───────────────────────────────────────────────────────────┘
```

### Monetization (revised 2026-03-27, supersedes design doc pricing)

**Hybrid Lock model — phased implementation:**
- **Phase 1 (now-6mo):** Vertical service, materials science. $15-30K paid pilots, converting to $8-15K/mo managed service. Free first run for qualified design partners.
- **Phase 2 (6-12mo):** Self-serve Detrix Cloud, $500/mo or usage-based. Gates on 5+ paying customers.
- **Phase 2.5:** Hosted inference, 30% of inference savings. Gates on 10+ training customers. Validate demand in Phase 1 discovery calls first.
- **Phase 3 (12mo+):** Domain pack subscriptions, contingent on aggregate learning validation.
- **Enterprise:** Self-hosted $3-10K/mo for pharma/defense who can't send data to cloud.

**What changed from design doc:** No license keys (Python source = trivially removable). No $99/mo Pro tier (too low, wrong signal). Managed compute is default path (not buried in Enterprise). Domain packs are subscriptions (not one-time) IF aggregate learning validates. See CEO plan: `~/.gstack/projects/gabegraves-detrix-core/ceo-plans/2026-03-27-monetization-restructuring.md`

### Credibility & Build Sequence (READ THIS BEFORE REVIEWING DETRIX-CORE)
**AgentXRD_v2 IS the product demo, not detrix-core.** The detrix-core repo is the extraction target, not the proof of concept. If you look at detrix-core in isolation, it looks like a YAML DAG runner with stubs. That's expected — the governance runtime is being extracted FROM AgentXRD_v2's working 203-file implementation, not built bottom-up from abstractions.

**What already works in AgentXRD_v2:** PipelineFSM with 12 states, metrology guard (`run_metrology_guard()`), quality gates (`QualityGates.evaluate()`), ensemble disagreement gate (92% recall at 100% precision), Rietveld FoM calculation, phase validator, verdict contract (`VerdictPayload`). These are real domain evaluators doing real physics. They're just not wired as blocking governance gates yet — that's what Detrix adds.

**The sequence:** AgentXRD_v2 proves the flywheel works end-to-end → extract governance/scoring/improvement into detrix-core as framework-agnostic ABCs → ParabolaHunter validates generality via raw Python adapter → detrix-core repo reflects the product.

**Do not critique detrix-core as if it should already be the finished product.** It's step 0 (scaffolding). The product demo lives in AgentXRD_v2's governance integration.

### Scoring System (three-tier, independent signals)
- **Tier 1: Deterministic physics gates** — domain math (Rietveld R_wp, convergence, backtest Sharpe). Authority. Always blocks. Never LLM.
- **Tier 2: LLM-as-judge** — per-session composite score. Advisory only. Never authoritative for domain validation.
- **Tier 3: Agent audit** — behavioral verification. Did the agent actually DO what it claimed? Tool calls match outputs? Intermediate results consistent with final claim? Independent from Tier 1/2 to break Goodhart circularity. Modeled on mission-control's agent audit pattern.
- **Training signal:** Only traces where all three tiers agree produce the cleanest SFT/DPO data. Tier 1 pass + Tier 3 verified = positive example. Tier 1 reject (output_quality) + Tier 3 verified = DPO negative. Tier 3 mismatch = exclude entirely (unreliable trace).

### Current Implementation (detrix-core repo)
- `src/detrix/core/` — models (StepDef, WorkflowDef, RunRecord, StepResult), cache, pipeline engine
- `src/detrix/runtime/` — audit log, artifacts, diff, provenance
- `src/detrix/improvement/` — ModelPromoter, eval harness, trace collector
- `src/detrix/cli/` — Click CLI commands
- `tests/` — all tests
- `examples/` — example pipelines and usage
- `.detrix/` — runtime data directory (cache.db, audit.db, artifacts/)

## Design Principles
- **Deterministic-first**: if physics/math can check it, ALWAYS use deterministic code, never LLM. LLM-as-judge is advisory only, never authoritative for domain validation.
- **Observer-first**: observe the pipeline running, calibrate from real data, THEN enforce. Don't block with uncalibrated thresholds.
- **MVP-first**: build thin, run on real pipelines, iterate from data. Spec the eval metric upfront, discover the implementation experimentally. Autoresearch pattern.
- **Framework-agnostic**: wrap LangGraph, LangChain, CrewAI, or raw Python via adapters — don't replace them
- **Local-first**: SQLite everywhere, no cloud accounts needed
- **Self-improving**: governance-scored traces feed fine-tuning, challenger models promote automatically through same gates
- **Pluggable**: GovernanceGate ABC, DomainEvaluator ABC, adapter pattern — implement what you need

## Working Rules
- All work must be tracked with beads and git
- Run `exec-report` skill at the end of every beads-tracked execution session before final handoff

## Quality Gates
- `uv run ruff check .` and `uv run mypy src/detrix` before committing
- `uv run pytest` before pushing
- Pre-commit hooks enforce lint and type checks via `make install-hooks` (when available)

## Git Rules
- Commit early and often
- One logical change per commit
- Conventional commits (feat/fix/docs/refactor)
- Include beads issue ID in commits when applicable: `git commit -m "feat: add trace collector (bd-abc)"`

## Conventions
- Click for CLI (not argparse)
- Pydantic v2 for all data models
- pytest for tests (no mocks of internal modules — integration tests only)
- ruff for linting (line-length=100)
- `uv` for all package management (never pip)
