# Detrix Reliability-First Positioning

Date: 2026-05-03

## Decision

Detrix should be positioned as the reliability layer for production agents, not
as an RL environment company.

Core identity:

> Detrix makes production agents reliable by governing what their outputs are
> allowed to change.

RL environments, SFT, DPO, GRPO, and Prime/ART/OpenPipe exports are downstream
uses of the reliability layer. They are not the product identity.

## Product Model

Every meaningful agent output proposes a state transition:

- send this message
- update this memory
- accept this scientific result
- place this trade
- change this policy
- promote this skill
- export this trace for training
- deploy this model checkpoint

Detrix evaluates whether that transition is admissible.

The core loop:

```text
agent output
  -> evidence capture
  -> deterministic / domain gate
  -> admission decision
  -> allowed action, rewrite, retry, request more data, block, or promote
  -> audit + replay fixture
  -> optional training signal
```

This is reliability first. Learning is downstream, but it should use both good
and bad traces. The admission layer decides the route: clean positives can teach
desired behavior; wrong outputs can become DPO negatives, RL penalties,
abstention examples, replay tests, failure classes, or next-action cases.

## Capture Model

Borrow the useful part of Orchestra Research's Agent-Native Research Artifacts
approach: capture the full branching trajectory, not only the polished winning
path. Their ARA format separates human overview, logic, executable source/config,
trace graph, dead ends, pivots, and evidence. That maps cleanly to Detrix, but
Detrix adds admission decisions and training-route policy.

Detrix capture should preserve:

- `overview`: human-readable task, goal, and current state
- `logic`: claims, assumptions, constraints, decision criteria, and expected
  evidence
- `execution`: tools, configs, inputs, environment, model/prompt/skill versions
- `trace`: full action graph, retries, dead ends, pivots, and unchanged-evidence
  loops
- `evidence`: raw outputs, logs, metrics, artifacts, hashes, and provenance
- `admission`: gate verdicts, reason codes, training route, next action, replay
  status, and promotion eligibility

The key difference from ARA: Detrix is not only preserving research knowledge.
It is deciding which captured objects are allowed to become production state,
training rows, replay fixtures, or promoted policies.

## Positioning

Do not lead with:

> We create RL environments.

Lead with:

> Detrix stops unreliable agent outputs from becoming production state.

Or:

> Detrix is the reliability layer for production agents: it decides what agent
> outputs can be accepted, retried, remembered, trained on, or promoted.

The YC version:

> Agents fail because their outputs are allowed to change the world without
> enough evidence. Detrix puts an admission layer between agent outputs and
> production state.

## OpenClaw First Demo

OpenClaw readable Telegram output should be the first demo because it is the
fastest legible proof of the Detrix abstraction.

The failure:

- The model is instructed to write readable Telegram messages.
- It keeps emitting dense, non-human-readable paragraphs with inline bullets.
- Prompting alone does not reliably fix the behavior.

The Detrix demo:

```text
OpenClaw model output
  -> Telegram readability gate
  -> PASS / REWRITE / BLOCK
  -> replay cases saved
  -> bad outputs become negative examples
  -> formatter, prompt, or skill changes must pass replay before promotion
```

The important claim:

> The model can propose text, but only readable output is admitted to the
> Telegram channel.

This is not a large-market demo by itself. It is the simplest possible proof
that Detrix is an admission layer, not just a workflow runner.

### Demo Script

1. Show bad OpenClaw output: one dense Telegram paragraph with inline bullets.
2. Show that readability instructions already existed and still failed.
3. Run a deterministic Detrix readability gate.
4. Emit an admission packet:
   - `decision=REWRITE` or `decision=BLOCK`
   - `failure_class=dense_telegram_output`
   - `reason_codes=[inline_bullets, over_length, missing_spacing]`
   - `training_route=dpo_negative` or `training_route=eval_only`
5. Show the admitted readable output.
6. Show replay cases that future prompt, formatter, skill, or model changes must
   pass before promotion.

This demo makes the product concrete before asking the audience to understand
PXRD or domain-specific scientific gates.

## AgentXRD Second Demo

AgentXRD should be the serious domain-specific proof.

```text
AgentXRD output
  -> PXRD/provenance admission gates
  -> ACCEPT / UNKNOWN / REQUEST_MORE_DATA / training-blocked
  -> failure class
  -> governed next action
  -> promotion replay
```

OpenClaw proves the general mechanism. AgentXRD proves the moat: domain-specific
evidence, provenance rules, false-ACCEPT prevention, and training contamination
prevention.

For AgentXRD, the state transition is not "send this message." It is:

- accept this PXRD result
- promote this evidence
- mark this row SFT-positive
- use this trace as DPO-negative
- request more data
- run a bounded next experiment
- promote or block a challenger

## Three-Domain Ladder

Use the proof domains in this order:

1. OpenClaw: readable-output admission
   - Question: can this message be sent?
2. AgentXRD: scientific-evidence admission
   - Question: can this result become truth or training data?
3. ParabolaHunter: economic-outcome admission
   - Question: can this strategy, alert, or policy be promoted?

Same product, different gates.

## Scaling Without Outsourcing

Detrix should not scale by manually building gates for every customer domain.
It should scale by building a repeatable admission-pack factory around real
failures.

The repeatable loop:

```text
1 real failure
  -> capture trace + artifact
  -> write or derive one deterministic gate
  -> add replay fixture
  -> assign failure class
  -> define admission consequence
  -> add promotion test
  -> export optional training label
```

Every failure becomes product surface.

### Reusable Software

The reusable product surfaces are:

- trace intake
- joinability audit
- failure mining
- gate proposal
- replay validation
- admission decisions
- training route compiler
- promotion gate

### Custom Per-Domain Surface

The custom part should be smaller:

- domain-specific gate logic
- examples
- thresholds
- admission consequences

Experts should validate boundaries, not label every trace or build the system.

The customer onboarding promise should become:

> Give us 10 real failures and one domain owner for a review. Detrix proposes a
> governed admission pack that stops those failure classes from poisoning
> production or training.

## Relationship To Training And RL

Training is a consequence of reliable admission, not the starting point. Failed
or wrong traces should still feed improvement when their route is explicit. The
unsafe move is learning from every trace as if it were a positive outcome.

Product ladder:

1. Runtime reliability gates.
2. Replay and audit.
3. Promotion governance.
4. Failure mining.
5. Training / RL environment export.

Do not claim self-improvement until the replay evidence exists. First prove that
Detrix can block, rewrite, request more data, and prevent unsafe promotion.

## What To Avoid

- "Detrix is an RL environment company."
- "Detrix is a better n8n."
- "Detrix is a generic eval dashboard."
- "Detrix trains cheaper models from traces."
- "Every trace becomes reward."
- "We do not need domain experts."

The correct framing:

> Detrix governs which agent-produced state transitions are admissible. Some
> admitted transitions become training signal.
