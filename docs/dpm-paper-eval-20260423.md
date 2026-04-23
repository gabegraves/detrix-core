# Paper Eval: Stateless Decision Memory for Enterprise AI Agents (2604.20158)

**Date evaluated:** 2026-04-23
**Authors:** Vasundra Srinivasan (April 2026)
**Verdict:** LOW relevance — orthogonal layer, file for future reference

## Summary

Deterministic Projection Memory (DPM): append-only event log + single task-conditioned LLM
projection at decision time. Core claim: statelessness (not decision quality) explains why
enterprises prefer weak RAG over sophisticated stateful memory. 2 LLM calls vs 83-97 for
summarization = 7-15x speed improvement.

Evaluated on LongHorizon-Bench: 10 regulated decisioning cases (mortgage + insurance), 82-96
events per case. Model: claude-haiku-4-5. DPM gains +0.52 factual precision at 20x compression.

## Detrix Relevance

**No overlap with core architecture.** DPM solves memory/context compression. Detrix solves
post-hoc output evaluation. Different layers.

- No self-improvement mechanism (fixed prompts, frozen model)
- Won't speed up AgentXRD_v2 (physics gates don't reason over compressed narratives)
- Zero relevance to RLVR, MetaClaw, training loops, model promotion

## Two Applicable Ideas

1. **Tier 2 scoring optimization (future).** If HaikuGrader ever scores trajectories >10k tokens,
   DPM's compress-first-judge-once beats incremental summarization. Optional pre-processing step.
   Not urgent — Tier 2 is advisory only.

2. **Enterprise positioning language.** DPM's "four enterprise properties" (replay, audit,
   isolation, statelessness) are useful framing for regulated industry pitches. Detrix satisfies
   all four by construction. Cite in pitch materials.

## Action

File for future reference. Memory layer is deferred (not Phase 1). If memory layer work begins,
validate that GovernedTrajectory stores raw events immutably with no intermediate summarization
(DPM's append-only pattern).
