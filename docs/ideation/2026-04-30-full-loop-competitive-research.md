# Full Self-Improvement Loop: Competitive Research + Readiness Assessment

Generated 2026-04-30 from 5 parallel research agents.

## The 5-Step Loop

```
EXPLORE codebase/data with agents
  → DIAGNOSE failures from Langfuse traces
    → SKILLIFY: create skills to fix failure points
      → TRAIN local model from governed traces
        → SERVE as always-on Hermes-style local agent
```

## Key Finding: Nobody Wires All 5 Steps Together

Confirmed across web research, competitor analysis, and academic survey. The gap is the **governed bridge** between failure diagnosis and local model training/serving.

## Competitive Landscape

### Hermes Agent (NousResearch, 127k stars)
- Steps covered: 1, 3 (partial), 5
- Architecture: 61 tools, 18+ providers, 7 terminal backends, gateway mode for always-on
- Skill creation: After 5+ tool calls, background process creates SKILL.md. Self-evolution via GEPA/DSPy.
- Local models: Qwen 3.5 35B via Ollama/vLLM (64k context minimum)
- **Critical gaps:** Skill promotion is self-assessed (no holdout). No signed provenance. No reward contamination protection. Skill poisoning unresolved. "Self-learning loop tends toward self-congratulation" (AgentConn).

### OpenClaw (345k stars, built on Pi)
- Steps covered: 1, 5
- 13,000+ community skills (human-written, not agent-generated)
- **Critical gaps:** 12% malware rate in ClawHub (341/2,857). 9 CVEs in 4 days. No skill self-generation. No learning loop.

### HF ml-intern (shipped April 21, 2026)
- Steps covered: 1, 2, 4 (target model only)
- Architecture: smolagents, SubmissionLoop, ContextManager (compacts at 170k tokens), doom-loop detector
- Performance: Qwen3-1.7B 10% → 32% on PostTrainBench in 10h on 1 H100
- **Critical gaps:** No governance layer. No self-improvement of agent itself. Cloud LLMs only.

### ML-Agent (MASWorks, arXiv 2505.23723)
- Steps covered: 1, 2, 4
- Qwen-2.5-7B trained via RL on MLAgentBench. Outperforms DeepSeek-R1 (671B).
- **Proves trace → local model loop works at 7B.**
- **Critical gaps:** No skill creation. No always-on deployment. No governance.

### Karpathy Autoresearch (66k stars, March 2026)
- Steps covered: 1, 2, 4
- 9-step ratchet: hypothesize → edit → train 5min → evaluate → keep/revert
- 700 experiments in 2 days, 20 winners, 11% speedup
- **Critical insight:** Fitness oracle is the bottleneck. val_bpb = oracle for ML. Detrix gates = oracle for domains.
- Karpathy progression: vibe coding → agentic engineering → autoresearch ("the loopy era")
- SETI@home vision: finding optimizations is expensive, verifying them is cheap
- **Critical gaps:** Only for ML training code. Not generalizable to arbitrary agent workflows.

### AIDE/aideml (WecoAI, production-grade)
- Steps covered: 1, 2
- Tree-search over code variants against any metric
- SOTA on MLE-Bench
- **Critical gaps:** No skill creation. No local training. No serving.

### GEPA (ICLR 2026 Oral, in DSPy)
- Steps covered: 2, 3 (prompts only)
- Outperforms GRPO 6-20% with 35x fewer rollouts
- Reflective genetic-Pareto prompt evolution
- **Critical gaps:** No model training. No always-on deployment. Text artifacts only.

### SWE-RL (Meta/NeurIPS 2025)
- Steps covered: 1, 4
- Self-play bug-inject/solve RL on 32B model. +10.4 pts SWE-Bench Verified.
- **Critical gaps:** No failure diagnosis pipeline upstream. No skill creation.

### SWE-Gym (Berkeley)
- <500 trajectories → +14% absolute gains on SWE-Bench Verified
- Confirms small trace sets sufficient for significant gains
- Validates Detrix "10-trace onboarding" concept

### Letta/MemGPT
- Steps covered: 1, 3 (reflection-based), 5
- Three-tier memory, git-backed skills, reflection → creation pipeline
- Terminal Bench 2.0: 36.8% gain with feedback-informed skill refinement
- **Critical gaps:** Same self-assessment issue as Hermes. No holdout. No physics gates.

### Atropos (NousResearch, 1.1k stars)
- RL rollout handler. NOT an agent runtime. Trained DeepHermes models.
- 4.6x improvement on parallel tool-calling benchmarks
- **Not a governance competitor.**

## Detrix Readiness Matrix

| Component | Status | Details |
|-----------|--------|---------|
| Pi-Extension Observer | ✅ EXISTS | 285+237 lines, batches tool_result events, 9 XRD tools |
| Trace Parsing + Failure Diagnosis | ✅ EXISTS | LangfuseImporter + FailurePatternCorpus, SQLite-based |
| Live Langfuse API Integration | ⚠️ SPEC | Judge-bridge blueprint only, not integrated |
| Skillify Registry (Wave 1) | ✅ EXISTS | Schema + SQLite store |
| Skillify Generation (Waves 2-4) | ❌ SPEC ONLY | Wrong-Side Gate, Routing Validator, Skill Generator, Orchestrator |
| Trajectory Store | ✅ EXISTS | SQLite, version contamination detection |
| Training Exporters (SFT/GRPO/DPO) | ✅ EXISTS | ChatML format, HF Datasets, production-ready |
| SFT Trainer (Unsloth+TRL) | ✅ EXISTS | LoRA adapters, GPU selection, production-ready |
| GRPO Trainer (ART) | ✅ EXISTS | Trajectory grouping, async backend, production-ready |
| Governance Gates | ✅ EXISTS | 4 gates: Rwp, Lattice, WrongAccept, Chemistry. 443 lines. |
| Privacy Worker (ml-intern) | ✅ EXISTS | Subprocess boundary, redaction, artifact whitelisting |
| Local Model Serving | ❌ MISSING | No vLLM/Ollama integration, no inference server |
| Always-On Runtime | ❌ MISSING | No persistent agent, no adapter loading, no continuous re-training |
| Docker/Packaging | ⚠️ PARTIAL | pip-installable, no Docker, no release distribution |

**Overall: 60% implemented. ~4-5 weeks to close gaps.**

## Support-Query Versioning: Unique Differentiator

**Zero analogs found in any observed system.** Flush trace buffer on ANY gate/evaluator version change to prevent reward contamination. This is a genuine blind spot in all prior art — Hermes, Letta, AIDE, ml-intern, autoresearch all lack this.

## The Positioning

"We're building the Karpathy Loop for domain-specific agents — but governed."

Detrix gates ARE the fitness oracle. Autoresearch uses val_bpb. KLA uses wafer inspection metrology. Detrix uses deterministic physics gates. Same structural pattern, different domains, with the critical addition of governed promotion and reward contamination protection.
