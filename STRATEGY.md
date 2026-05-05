---
name: Detrix
last_updated: 2026-05-05
---

# Detrix Strategy


## Current strategic direction: bead-native harness compiler

Detrix's current product direction is a bead-native harness compiler for agent
execution. Raw sessions are converted into atomic beads; builder agents execute one
bead and emit structured claims; verifier agents try to falsify those claims;
recurring failures become typed failure patterns; harness mutations are proposed;
and only replay-safe mutations are promoted.

The moat is not generic observability, generic governance, generic memory, or generic
fine-tuning. The moat is evaluator-aligned promotion: a harness change must improve
held-out project beads without weakening hard gates such as AgentXRD support-only
boundaries or ParabolaHunter real-priced evidence requirements. See
`docs/bead-native-harness-compiler-20260505.md`.

## Target problem

Teams are putting agents into workflows where plausible but wrong outputs can become
production state, memory, policy, training data, or promoted behavior. Logs and eval
dashboards show what happened after the fact, but they do not run inline with execution
to decide what is admissible before the output changes the world.

## Our approach

Detrix is the reliability harness around agent state transitions. The agent proposes;
Detrix captures evidence, applies deterministic gates, emits an admission decision,
creates replay cases, and only then allows the output to be sent, accepted, retried,
remembered, trained on, or promoted.

## Who it's for

**Primary:** Technical teams deploying production or near-production agents - they're
hiring Detrix to make agent outputs reliable enough to act on and improve from without
trusting prompts, dashboards, or raw trace fine-tuning.

**Secondary:** Teams moving from frontier APIs to local models - they're hiring Detrix
because gates make the local switch safer by catching smaller-model failures before
they reach production or training data.

## Key metrics

- **Admission coverage** - percent of meaningful state-transition boundaries that pass
  through Detrix; measured from harness trace logs.
- **Replay pass rate** - percent of held-out failure and success cases passed by a
  proposed prompt, formatter, skill, model, policy, or gate change.
- **Unsafe transition rate** - count of wrong sends, false accepts, unsafe promotions,
  or contaminated training exports admitted after Detrix evaluation.
- **Failure-to-gate yield** - number of recurring real failure classes converted into
  replay-tested gates and admission consequences per customer workflow.
- **Local-model safety delta** - before/after held-out replay improvement for local
  model proposals without increasing unsafe transitions.

## Tracks

### OpenClaw Readability Harness

The first guaranteed MVP: digest real Telegram/OpenClaw traces, enforce a deterministic
readability gate at the send boundary, rewrite or block unreadable messages, and make
future prompt/formatter/model changes pass replay before promotion.

_Why it serves the approach:_ It is the fastest visible proof that Detrix is an inline
admission harness, not another prompt instruction or trace dashboard.

### Portable Admission Contracts

Define the common packet shape for trace, evidence, gate verdict, admission route,
training route, replay status, and promotion eligibility.

_Why it serves the approach:_ The same contract must cover a Telegram message, an
AgentXRD scientific result, and a ParabolaHunter trading decision.

### Domain Reliability Packs

Turn recurring failures in a workflow into deterministic gates, failure labels, allowed
next actions, replay fixtures, and promotion rules.

_Why it serves the approach:_ Domain packs are where the validated decision boundary
compounds; generic harness code is not the moat.

### Governed Improvement Loop

Use rejected and accepted traces as routed improvement signal: replay cases first,
prompt/formatter/skill promotion second, SFT/DPO export third, and RL/Prime/Verifiers
only after replay evidence and enough governed trajectories exist.

_Why it serves the approach:_ Self-improvement should start with the reliability
boundary getting better, not with unsafe model training claims.

## Milestones

- **2026-05-04** - OpenClaw Telegram readability admission demo from real trace evidence,
  with before/after replay and a clear AgentXRD portability bridge.

## Not working on

- A generic RL environment company or hosted trainer.
- A generic n8n/LangGraph/pi replacement.
- Qwen self-improvement claims without held-out replay proof.
- Prime/Verifiers integration before Detrix admission packets and replay cases exist.
- Hand-labeling every customer trace as a services business.

## Marketing

**One-liner:** Detrix makes high-stakes AI agents reliable enough for production.

**Key message:** Agents propose outputs. Detrix decides what can be sent, accepted,
retried, remembered, trained on, or promoted. The first demo is readable Telegram
output; the durable product is the same admission harness for scientific,
engineering, and financial agent workflows.
