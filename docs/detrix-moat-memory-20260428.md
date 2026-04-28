# Detrix Moat Memory - 2026-04-28

Status: repo-local strategic memory. This is a durable reference for Detrix positioning, YC demo framing, and future agent guidance. It is not an implementation claim.

## Executive Thesis

Detrix should not claim defensibility from using Claude, Codex, Qwen, or any other model as a judge. Those are replaceable components.

The moat is the accumulated, validated, domain-specific reliability infrastructure that turns high-stakes agent traces into safe decisions, allowed next experiments, and governed training data.

Short version:

> Codex, Claude, Hermes, pi, or internal agents make things happen. Detrix decides what survived, what failed, what may be tried next, and what is safe to learn from.

## What Is Easy To Copy

Competitors can copy these quickly:

- calling Claude/Codex/Qwen as a judge
- deterministic scripts around traces
- a basic trace store
- an agent retry loop
- generic SFT/DPO export
- Langfuse or Braintrust integration
- local-first deployment claims
- generic policy YAML

Do not pitch any of those alone as the moat.

## What Is Hard To Copy

The durable advantage is the compounding decision boundary per domain:

- trusted benchmark and replay surfaces
- labeled failure corpus, including near misses and false accepts
- domain gate semantics
- provenance and promotion rules
- support-only / eval-only / training-positive separation
- terminal route semantics
- evidence-delta ledgers
- calibration curves and wrong-accept analysis
- domain action policies for what an agent may try next
- governed positive and negative training traces
- reusable customer-facing evidence reports

This is not just data. It is data plus domain rules plus replayable proof that the rules prevent unsafe promotion while still allowing useful self-correction.

## Validated Decision Boundary

The strongest phrase is:

> Detrix compounds validated decision boundaries for high-stakes agents.

A validated decision boundary answers:

1. What output is valid in this domain?
2. What evidence is required before promotion?
3. What failures are safe to retry?
4. What failures require human input or more data?
5. Which traces are SFT-positive, DPO-negative, eval-only, or excluded?
6. Did a proposed fix improve the evidence without increasing catastrophic risk?

## Why In-House Claude/Codex Is Not Enough

A strong internal team can build a first evaluator. The hard part is sustaining the loop without contaminating evidence or training data.

Common in-house failure modes:

- judge approval gets treated as truth
- support-only evidence becomes benchmark-grade by accident
- thresholds are relaxed to show progress
- post-hoc discoveries leak into training labels
- generated/provisional truth becomes promotion evidence
- traces lack enough provenance to replay decisions
- teams cannot prove a new policy improved without increasing wrong accepts

Detrix must make these failure modes visible and structurally hard to ship.

## Relationship To Hermes-Style Agents

Hermes-like systems are autonomous actors. Detrix is the trust and learning layer around autonomous actors.

- Hermes/Codex/Claude/pi chooses and executes actions.
- Detrix observes outputs, applies domain gates, diagnoses failures, proposes allowed next actions, checks policy/resources, measures evidence deltas, and decides training/export eligibility.

Detrix should therefore be positioned as complementary to agent runtimes, not a replacement for them.

## Domain Examples

### XRD / Scientific Instrumentation

Current proof domain: AgentXRD_v2.

Compounding assets:

- PXRD truth surfaces and benchmark artifacts
- CIF provenance and support-only policies
- Pawley/Rietveld evidence gates
- wrong-ACCEPT constraints
- candidate-discovery and polymorph failure taxonomies
- terminal routes: ACCEPT, SET, UNKNOWN, REQUEST_MORE_DATA
- governed judge cohorts and export eligibility reports

The current lesson is that governance caught unsafe over-promotion, but scientific capability still needs more governed positives. That is acceptable only if Detrix keeps converting UNKNOWN into a policy-allowed next experiment rather than stopping at rejection.

### Options Trading / Market Agents

Second likely domain: ParabolaHunter-style trading agents.

Compounding assets:

- real-priced vs proxy-priced evidence separation
- replay/live parity checks
- stale quote and data-source gates
- risk/reward and drawdown gates
- alert hygiene failure modes
- promotion packets for strategies or alerts
- governed training traces from accepted/rejected trade decisions

The product must be framed as reliability infrastructure, not alpha generation.

## Product Rule

Never say:

> We collect traces and fine-tune agents.

Say:

> We determine which traces are safe to learn from, which failures are safe to retry, and which outcomes require more evidence. Then we train only on governed examples that survived domain-specific gates.

## YC-Safe Moat Claim

> Detrix is the reliability layer for high-stakes agents. Each deployment compounds a domain pack: gates, evals, failure taxonomies, provenance rules, action policies, calibration data, and governed training traces. Claude or Codex can inspect one trace. Detrix builds the reusable decision boundary that says what survived, what failed, what to try next, and what is safe to learn from.

## Proof Standard

A future demo should prove the moat with before/after evidence:

1. A generic judge or agent makes a plausible but unsafe recommendation.
2. Detrix catches the unsafe promotion using deterministic domain gates.
3. Detrix classifies the blocker.
4. Detrix proposes the next allowed bounded experiment.
5. The experiment runs under policy/resource limits.
6. Detrix measures evidence delta.
7. Only gate-passed traces become training/export eligible.

This is the step-change from trace logging to governed self-correction.
