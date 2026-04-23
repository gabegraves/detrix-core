# AutoResearch Landscape Evaluation — 2026-04-23

Evaluated three repos against Detrix's self-improvement loop, AutoML goals, and AgentXRD_v2 acceleration.

## Verdict Summary

| Repo | Relevance | Action |
|------|-----------|--------|
| MLAgentBench (Stanford SNAP) | **HIGH** — ready-made RLVR environment | Adopt as Phase 2 training ground + validation benchmark |
| awesome-autoresearch | **MEDIUM** — surfaced direct competitors + RLVR environments | Mine GEPA, AIDE, ML-Agent as competitive intel; MLE-bench + ScienceAgentBench as additional training grounds |
| AutoResearchClaw (Aiming Lab) | **MEDIUM** — live MetaClaw deployment to study | Study their MetaClaw integration (SkillEvolver + PRM). Not a component to adopt, but validates the skill evolver path |

---

## MLAgentBench — github.com/snap-stanford/MLAgentBench

**What**: Benchmark suite (arXiv 2310.03302) — 13 real-world ML tasks (Kaggle, CIFAR-10, BabyLM, CLRS, etc.) with deterministic evaluation, full trajectory logging, and sandboxed execution. Agents autonomously write code, train models, and improve metrics against quantitative baselines.

**Architecture**: `environment.py` provides an interactive sandbox per task with a fixed action space (file read/write, execute, Python REPL). Hidden `eval.py` per task contains a `get_score()` function that computes deterministic metrics (accuracy, SMAPE, etc.) against ground truth. Agents interact via `(action, observation)` pairs with time limits (5h, 50 steps). Pluggable agent implementations (ReAct, LangChain, AutoGPT).

**Why it matters for Detrix**:

1. **RLVR training ground.** Every task's `get_score()` is a deterministic, domain-specific verifiable reward function — Detrix Tier 1. Trajectories logged as action/observation pairs = ready-made training data for SFT/DPO/GRPO.

2. **Governance validation benchmark.** Can test whether Detrix's observer→enforcer→improve loop actually makes agents better on standardized tasks. Quantitative proof that governance works.

3. **DomainEvaluator reference implementations.** The 13 hidden `get_score()` functions are narrow, deterministic, authoritative — exactly the pattern for Detrix `DomainEvaluator` ABCs. Could serve as templates.

4. **The gap Detrix fills.** MLAgentBench measures agent capability at a point in time. Detrix drives improvement over time. MLAgentBench provides the harness; Detrix closes the loop by feeding scored traces into training. No existing agent in MLAgentBench does this.

**Gaps**:
- Evaluates at task-completion level, not per-step. Detrix needs per-step gate scoring → extend with intermediate checkpoints.
- Tasks are generic ML engineering, not domain-specific physics. Proves framework works but doesn't test domain expertise.
- No RL training loop — agents are prompted LLMs, not RL-trained policies. The environment is RL-shaped but used only for evaluation.

**Concrete integration path**:
- Phase 2: Ingest MLAgentBench trajectories as seed data for SFT/DPO. Map task metrics to GovernedTrajectory reward fields.
- Phase 4: Use as shadow eval environment for model promotion. New model must match or beat baseline on MLAgentBench tasks.
- Phase 5: First non-crystallography domain pack = ML engineering, using MLAgentBench tasks as evaluation gates.

**For AgentXRD_v2**: No direct speedup. Confirms the evaluation harness pattern is sound. Could test whether XRD governance generalizes to ML engineering (proof of framework-agnostic claim).

---

## awesome-autoresearch — github.com/alvinreal/awesome-autoresearch

**What**: Curated awesome-list (1,586 stars, CC0) indexing autonomous improvement loops, research agents, and self-improving systems descended from Karpathy's `autoresearch` project. Single-file README — no code.

### High-Value Finds (Competitive Intel)

**Direct competitors to Detrix's improvement loop:**

| Project | What it does | Detrix relevance |
|---------|-------------|-----------------|
| **GEPA** (ICLR 2026) | Genetic-Pareto prompt evolution. Reflective prompt optimization that **explicitly outperforms GRPO** on benchmarks. DSPy integration. | Directly comparable to MetaClaw's gradient-free skill evolver. Competitive threat if they add domain gates. Study their Pareto selection mechanism. |
| **AIDE/aideml** (Weco) | Tree-search agent that autonomously improves model performance against any metric. | Closest analog to Detrix's overnight improvement loop. Agent explores solution tree, evaluates branches, keeps best. No governance gates though. |
| **ML-Agent** (MASWorks) | "Reinforcing LLM agents for autonomous ML engineering. Learns from trial and error." RL-based. | Directly in Detrix's territory — RL agent improvement from task outcomes. Unclear if they have deterministic evaluation or just LLM scoring. |
| **recursive-improve** | Captures execution traces, analyzes failure patterns, applies targeted fixes with keep-or-revert evaluation. | Mirrors Detrix's observe-enforce-improve arc. Trace-based self-repair. |
| **ADAS** (ICLR 2025) | Meta-agents that invent novel agent architectures by programming them in code. | Related to Detrix's Meta-Harness (Phase 6) — LLM proposes governance config improvements. Same meta-optimization idea, different target. |
| **autoevolve** | Elo-rated self-play code mutations. | Interesting selection mechanism (Elo) but narrow to code quality, not domain physics. |

**Domain-specific validation of Detrix thesis:**

| Project | Domain | Verifiable reward |
|---------|--------|-------------------|
| **atlas-gic** | Trading | Rolling Sharpe ratio. Keep-or-revert loop against domain physics metric. Proves the pattern works. |
| **autovoiceevals** | Voice AI | Adversarial evaluation for voice agents. Domain-specific verifiable eval. |
| **Driveline** | Biomechanics (baseball) | Domain physics in sports science. |
| **autokernel** | GPU kernels | Performance benchmarks as reward signal. |

**Additional RLVR environments (beyond MLAgentBench):**
- **MLE-bench** (OpenAI) — Kaggle-style ML engineering benchmarks. Larger task set than MLAgentBench.
- **MLR-Bench** — ML research benchmark with quantitative evaluation.
- **ScienceAgentBench** — Data-driven scientific discovery. Closer to domain-specific evaluation.
- **AgentBench** (ICLR 2024) — Multi-domain agent benchmark.

**Research agents (potential Detrix consumers):**
- **The AI Scientist v1/v2** (Sakana AI) — end-to-end research pipeline. Crude self-improvement via review.
- **AgentLaboratory** — autonomous scientific pipelines.
- **ChemCrow / BioPlanner** — domain-specific agents, natural customers for Detrix domain packs.

### Key Takeaway

The improvement loop space is heating up. GEPA, AIDE, ML-Agent, and recursive-improve all attack parts of Detrix's value prop. **None of them combine deterministic domain-physics gates + tiered scoring + governance enforcement + training signal extraction.** Detrix's moat is the full stack, not any single component.

---

## AutoResearchClaw — github.com/aiming-lab/AutoResearchClaw

**What**: 23-stage autonomous research pipeline (11.5k stars, MIT) that takes a research idea and produces a conference-ready paper. 8 phases: scoping → literature → synthesis → design → execution → analysis → writing → finalization. "Co-Pilot" mode with 6 levels of human-in-the-loop.

**Revised assessment**: More relevant than initially thought — they integrate MetaClaw.

### MetaClaw Integration (v0.3.0)

AutoResearchClaw has a 5-layer MetaClaw integration:
- **L1**: Proxy passthrough to MetaClaw API
- **L2**: Stage-aware skill injection (skills injected into LLM calls per-stage)
- **L3**: Lesson-to-skill bidirectional bridge (pipeline failures → structured lessons → reusable skills)
- **L4**: PRM (Process Reward Model) quality gating at stages 5, 9, 15, 20
- **L5**: Optional RL fine-tuning from research conversation traces (requires GPU)

Reported **+18.3% robustness improvement** from MetaClaw integration. Self-learning lessons have 30-day time-decay.

### What Detrix should study

1. **Lesson-to-skill bridge (L3)** — structured failure → reusable skill is exactly MetaClaw's SkillEvolver in production. Study their lesson schema and skill injection mechanism.
2. **PRM quality gating (L4)** — process reward model at intermediate stages is closer to Detrix's per-step scoring than MLAgentBench's task-completion scoring. However, their PRM is LLM-based, not deterministic.
3. **Stage-aware injection (L2)** — skills injected contextually per pipeline stage. Relevant to how Detrix domain packs should inject evaluation context.

### Why it's still NOT a component to adopt

1. **All evaluation is LLM-advisory or structural.** PRM is LLM-based. Quality checks are word counts, citation existence, NaN detection, NeurIPS checklist compliance. No deterministic domain-physics gates.
2. **"Self-improvement" is prompt engineering.** L3 lesson→skill is skill injection into prompts, not model fine-tuning via verifiable rewards. L5 RL training is optional and uses conversation traces, not structured reward signals.
3. **Wrong target.** Optimizes for paper production, not production agent reliability.
4. **Domain adapters are shallow.** Physics/chemistry/biology adapters handle code generation prompts and Docker profiles, not domain-specific physics evaluation gates.

### Potential value
- **Customer demo**: AutoResearchClaw's 23-stage pipeline could benefit from Detrix governance gates at each stage transition. Natural customer narrative.
- **MetaClaw reference implementation**: Their L1-L5 integration is the most complete MetaClaw deployment in the wild. Study for Phase 1 (skill evolver) implementation details.

---

## Cross-Cutting Findings

### Competitive Landscape Update

The self-improvement loop space has 6+ active projects (GEPA, AIDE, ML-Agent, recursive-improve, ADAS, autoevolve). **None combine all four Detrix differentiators:**
1. Deterministic domain-physics gates (Tier 1 authority)
2. Tiered scoring (deterministic > LLM advisory > agent audit)
3. Stripe Blueprints structural enforcement (agent cannot skip gates)
4. Training signal from governance-scored traces (SFT/DPO/GRPO)

GEPA is the closest competitive threat — it outperforms GRPO on benchmarks using gradient-free evolution, directly comparable to MetaClaw's skill evolver. But it has no governance gates or domain physics.

### Verifiable Reward Supply

Four RLVR environments worth targeting:
1. **MLAgentBench** (Stanford) — 13 tasks, deterministic `get_score()`, trajectory logging. **Primary.**
2. **MLE-bench** (OpenAI) — Kaggle-style, larger task set. **Secondary.**
3. **ScienceAgentBench** — scientific discovery, closer to domain-specific. **Investigate.**
4. **AgentXRD_v2** (internal) — crystallography, 6 governance gates. **Proving ground.**

### AutoML Positioning

MLAgentBench tasks (hyperparameter tuning, architecture search, feature engineering) ARE AutoML. Detrix governing an agent on MLAgentBench tasks = Detrix doing AutoML with governance gates. Natural positioning story: "AutoML with physics-grade quality gates."

### AgentXRD_v2 Acceleration

No direct speedup from any repo. Value is:
- MLAgentBench validates the evaluation harness pattern XRD already uses
- AutoResearchClaw's MetaClaw integration shows the skill evolver path works (+18.3%)
- GEPA's Pareto selection could improve XRD's prompt evolution if integrated

### Action Items

1. **Deep-dive GEPA** — competitive threat. Understand Pareto selection vs MetaClaw skill evolution.
2. **Clone MLAgentBench** — set up as Phase 2 RLVR training ground. Map `get_score()` functions to GovernedTrajectory schema.
3. **Study AutoResearchClaw's L3 lesson-to-skill bridge** — reference for Phase 1 SkillEvolver implementation.
4. **Investigate MLE-bench + ScienceAgentBench** — additional RLVR environments for Phase 4 shadow eval.
5. **Track ML-Agent (MASWorks)** — RL-based agent improvement, most direct competitor. Monitor for domain physics additions.
