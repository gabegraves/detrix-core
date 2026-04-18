# Competitive Landscape: RLVR Environments + Self-Improving Agent Harnesses

**Date:** 2026-04-18
**Sources:** 6 parallel research agents covering 30+ systems, 14 arxiv papers, 3 YC companies

---

## The Market Map

```
                         UPSTREAM                              DOWNSTREAM
                    (train the model)                    (improve deployed agents)
                    ─────────────────                    ────────────────────────

    GENERIC     │  Calaveras AI (STEM data)          │  Hermes/Atropos (binary verifiers)
    REWARD      │  HillClimb (Lean proofs, math)     │  MetaClaw (skill evolution + GRPO)
    (heuristic/ │  SWE-Gym (test pass, code)         │  CascadeFlow (cost routing)
    binary)     │  AgentRL (THUDM, multi-task)       │  OpenHands (eval-only, no training)
                │                                     │  Microsoft AGT (policy rules)
                │                                     │
    ────────────┼─────────────────────────────────────┼──────────────────────────────────
                │                                     │
    DOMAIN      │  Haladir (SMT/Gurobi, code+OR)     │  ← DETRIX (domain physics,
    PHYSICS     │  P1 (Physics Olympiad verifier)     │     self-improving, structural
    REWARD      │  VPRMs (medical, rule-based)        │     enforcement, local models)
    (determin-  │                                     │
    istic,      │                                     │
    continuous) │                                     │

    Legend:
    Upstream = sells to frontier labs for pre/post-training
    Downstream = sells to enterprises deploying agents
    Generic = format/correctness rewards (pass tests, match JSON, compile)
    Domain Physics = deterministic domain math as reward (R_wp, Sharpe, proof, convergence)
```

**Detrix is bottom-right: domain physics rewards for deployed agents.** That quadrant has zero commercial competitors.

---

## RLVR Environment Companies (Direct Category)

### Calaveras AI — Upstream STEM Data + Environments
- **What:** Pre-training data + verifiable RL environments for STEM. Code-centric confirmed.
- **Customers:** 4 of top 6 frontier labs (unnamed, likely OpenAI/Anthropic/Google/Meta)
- **Team:** 2 founders (ex-Magic.dev, ex-OpenAI, Stanford dropout). Lean.
- **Funding:** Undisclosed, likely pre-seed from lab contracts
- **Reward type:** Verifiable (binary, execution-based for code)
- **vs Detrix:** Different layer entirely. Calaveras sells picks-and-shovels to labs training foundation models. Detrix targets enterprises deploying those models. Complementary, not competitive.

### HillClimb (YC F25) — Human-Curated Math RL Environments
- **What:** IMO medalists + Lean formalization experts curate math problems + reasoning traces
- **Proof:** Trained Nomos 1 (Nous Research collab): 87/120 on Putnam 2025 (#2 out of 3,988)
- **Customers:** Nous Research confirmed. Angels from OpenAI, Anthropic, DeepMind, xAI, Meta.
- **Team:** 4 people. YC partner: Garry Tan.
- **Reward type:** Lean proof compilation (binary, deterministic, ungameable)
- **vs Detrix:** Upstream math environments. Zero overlap today. Watch: if they expand to scientific domains (chemistry, physics), they'd be upstream competition in Detrix's verticals.

### Haladir (YC W26) — Formal Verification as RLVR Reward
- **What:** RL post-training for code gen (SMT/Z3 via Dafny) + operations research (Gurobi)
- **Key insight:** Unit tests check finite sample points (gameable). Formal contracts prove correctness over ALL inputs (ungameable).
- **Papers:** RLFR (Jan 2026) + ConstraintBench (Feb 2026, arXiv:2602.22465)
- **Results:** +3.7pp LiveCodeBench, beats DeepSeek-Coder-33B with 7B model
- **Team:** 4 undergrad founders (CMU, Princeton). YC partner: Diana Hu.
- **Reward type:** Continuous (SMT proof + Gurobi optimality gap). Deterministic.
- **vs Detrix:** CLOSEST structural analog. Same philosophy (deterministic non-LLM verification as reward). Different domains (code/OR vs materials/trading). Different stack position (upstream for labs vs downstream for enterprises). Haladir trains the hammer. Detrix ensures it hits the right nail in production.

---

## Self-Improving Agent Harnesses

### Hermes Agent + Atropos (Nous Research)
- **What:** Open-source self-improving agent (95.6k stars) + Atropos RL framework
- **Training:** Hermes 4 uses ~1,000 binary verifiers via Atropos. 60B tokens, 5M samples.
- **Reward:** Primarily binary (exact JSON match, test pass, format check). Length penalty.
- **Agent loop:** Full runtime with tools, skills, memory, Docker isolation
- **Self-improvement:** Trajectory capture → batch RL → next model. Latency-separated.
- **Gates:** Security gates (command approval, container isolation). NO domain physics gates.
- **vs Detrix:**
  - Hermes rewards are binary/generic (JSON matched? Y/N). Detrix rewards are continuous/domain-specific (R_wp = 12.3%).
  - Hermes has no runtime enforcement. The model is expected to self-regulate. Detrix structurally blocks bad outputs.
  - Hermes trains on format/instruction-following signal. Detrix trains on domain correctness signal.
  - Hermes's 1,000 verifiers are breadth. Detrix's domain packs are depth.

### MetaClaw (AIMING Lab, MIT)
- **What:** Continual meta-learning: skills (gradient-free) + GRPO (gradient-based)
- **Key pattern:** OMLS scheduler, support-query versioning, skill evolver
- **Results:** 21.4% → 40.6% accuracy (skills + RL), +18.3% composite robustness
- **vs Detrix:** Detrix ports MetaClaw's patterns (OMLS, skill evolver) but replaces the generic PRM with domain physics gates. MetaClaw's reward is a generic file-check. Detrix's reward is Rietveld refinement.

### Microsoft Agent Governance Toolkit (April 2026)
- **What:** Seven-package runtime governance. YAML/OPA Rego/Cedar policies. <0.1ms p99.
- **Unique:** Agent Lightning package handles RL training with policy-enforced runners
- **Gates:** Policy-rule based (human-authored rules). Covers OWASP Agentic Top 10.
- **vs Detrix:** Closest to Detrix's enforcement layer. But Microsoft enforces static human-authored policies. Detrix enforces domain physics (math-verifiable, auto-derived from domain). Microsoft doesn't learn from gate signals. Detrix's gates generate training signal.

### CascadeFlow (lemony-ai, MIT)
- **What:** Cost/latency optimizer via model cascading (cheap model first, escalate if quality fails)
- **Quality:** Heuristic (hedging detection, response length, model confidence). Not domain-specific.
- **Training:** None. Adaptive thresholds in-memory only.
- **Patterns to steal:** Three-mode harness (off/observe/enforce), lazy imports, composite validators
- **vs Detrix:** Different problem. CascadeFlow asks "which model is cheapest?" Detrix asks "is this actually correct?" Complementary — could cascade models AND governance-gate outputs.

---

## Key Arxiv Papers (2025-2026)

### Most Important for Detrix Architecture

| Paper | ID | Key Finding |
|---|---|---|
| **VPRMs** | 2601.17223 | Deterministic mid-step verification beats LLM-as-judge by 20% F1. THE theoretical backbone for Detrix's gates as training signal. |
| **OpenClaw-RL** | 2603.10165 | Princeton. 4-component async infrastructure (env + PRM + trainer + server) for live-deployment RLVR. The architecture Detrix's overnight loop should follow. |
| **Agent-RLVR** | 2506.11425 | Guidance from failures bootstraps positive trajectories. Gate rejections → training signal. SWE-Bench 9.4% → 27.8%. |
| **P1 Physics** | 2511.13612 | Physics-Verifier as deterministic RL reward. Gold medal IPhO 2025. Closest existing physics-domain RLVR. |
| **EigenData** | 2601.22607 | Co-generates executable per-instance checkers alongside training data. Verifiers as first-class artifacts. |

### Also Relevant

| Paper | ID | Key Finding |
|---|---|---|
| AgentRL | 2510.04206 | Production GRPO harness for multi-turn multi-task. Cross-policy sampling. |
| PEARL | 2601.20439 | Separate planning rewards from execution rewards in GRPO. |
| Darwin Godel | 2505.22954 | Self-modifying agent using benchmarks as reward. 20% → 50% SWE-bench. |
| Med-RLVR | 2502.19655 | Domain RLVR for medicine. 3B model, 8-point accuracy gain on OOD. |
| Crossing Reward Bridge | 2503.23829 | Extends RLVR to chemistry, psychology, economics. Soft rewards from verifiers. |
| AgentPRM | 2511.08325 | Step-level "promise + progress" for agent tasks. TD-based. 8x compute efficiency. |
| ToolPRMBench | 2601.12294 | First benchmark for tool-use PRMs. Specialized PRMs >> general PRMs. |
| Meta HyperAgents | 2603.19461 | Self-modifying harness code. Meta-level improvements transfer across domains. |
| AlphaEvolve | 2506.13131 | DeepMind. Deterministic evaluation for algorithms. Inference-time evolution. |

---

## The Competitive Gap (Confirmed)

No published system or commercial product combines all four:

| | Deterministic Eval | Trains Model Weights | Domain Physics Reward | Blocks Bad Outputs at Runtime |
|---|---|---|---|---|
| SWE-Gym | Yes (tests) | Yes (RL) | No (generic code) | No |
| Hermes/Atropos | Yes (binary) | Yes (RL) | No (generic format) | No |
| Haladir | Yes (SMT/Gurobi) | Yes (GRPO) | Partial (formal, not physical) | No |
| AlphaEvolve | Yes (math) | No (inference) | Yes (algorithms) | Implicit |
| Microsoft AGT | Yes (policy) | Partial (Lightning) | No (human rules) | Yes |
| MetaClaw | No (PRM) | Yes (GRPO) | No (generic) | No |
| CascadeFlow | No (heuristic) | No | No | No |
| **Detrix** | **Yes (physics gates)** | **Yes (GRPO/Unsloth)** | **Yes (Rietveld, backtest)** | **Yes (Stripe Blueprints)** |

---

## Strategic Implications

### 1. The RLVR Environment Category Is Real and Funded
Calaveras, HillClimb, and Haladir all raised money selling verifiable reward environments to frontier labs. The category is validated. But they're all UPSTREAM (selling to model trainers). Detrix is DOWNSTREAM (selling to model deployers). Different buyer, different value prop, same underlying insight.

### 2. Haladir Is the Closest Analog — Learn From Them
Same philosophy (deterministic verification as RLVR reward), different domains. Their RLFR paper shows a 7B model beating a 33B model on code benchmarks using formal verification rewards. If Detrix can show a 7B model approaching frontier quality on XRD analysis using physics rewards, it's the same story in a different domain. The ConstraintBench methodology (Gurobi as ground-truth oracle) is directly portable to Detrix's domain packs.

### 3. Hermes Is Infrastructure, Not Competition
Hermes/Atropos provides the RL training infrastructure. Detrix provides the DOMAIN-SPECIFIC reward signal that feeds into that infrastructure. A future integration: Detrix domain packs as Atropos environments. Nous Research is a potential partner, not a competitor.

### 4. Microsoft AGT Is the Enterprise Governance Competitor
Microsoft's Agent Governance Toolkit is the closest to Detrix's runtime enforcement. But it enforces human-authored policy rules, not physics-derived gates. The moment a customer needs "is this Rietveld refinement correct?" rather than "does this comply with our policy?", Microsoft can't help. That's Detrix territory.

### 5. The Papers Validate Every Design Decision
- VPRMs prove deterministic mid-step verification > LLM-as-judge (Detrix's Tier 1 > Tier 2)
- Agent-RLVR proves gate failures → training signal works (Detrix's improvement loop)
- OpenClaw-RL provides the async infrastructure pattern (Detrix's overnight loop)
- P1 proves physics evaluation drives RL training (Detrix's core thesis)
- ToolPRMBench proves specialized PRMs >> general PRMs (Detrix's domain packs > generic verifiers)

### 6. The Unfilled Quadrant
Bottom-right of the market map (domain physics rewards + downstream deployment) has zero commercial competitors. Every player is either upstream (sells to labs) or generic (format/correctness, not domain physics). Detrix's positioning in that quadrant is defensible because building domain-specific physics evaluators requires domain expertise that software companies don't have.

---

## Sources

All papers, repos, and company profiles cited inline. 6 research agents, 30+ systems analyzed.
Full agent outputs available in session artifacts.
