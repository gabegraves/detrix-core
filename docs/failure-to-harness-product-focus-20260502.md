# Detrix Failure-to-Harness Product Focus

Date: 2026-05-02

## Decision

Detrix should focus on a failure-to-harness compiler, not an expert marketplace,
generic agent scaffold, generic RL trainer, or observability dashboard.

The product direction:

> Give Detrix traces, artifacts, goals, and failure examples. Detrix mines the
> failure modes, proposes deterministic gates, replay-tests them, and emits a
> runnable domain harness/environment that can govern and train future agents.

This is the scalable path between two traps:

- Too vertical: Detrix becomes an AgentXRD-only science app.
- Too horizontal: Detrix becomes abstract RLVR/framework consulting before the
  real failure modes are understood.

AgentXRD should be the first proof domain, but the product is the repeatable
process that turns operational failures into gates, rewards, replay fixtures,
training labels, and environment adapters.

## Mercor Risk

If Detrix becomes "hire experts to label traces and build evals," it competes
directly with Mercor-style expert-data marketplaces.

Mercor's center of gravity is expert labor, expert datasets, benchmarks,
evaluation environments, RL tasks, and verifiers. Detrix should not try to beat
that by building another expert marketplace.

The anti-Mercor positioning:

> Mercor scales expert annotation. Detrix compiles failed operational traces into
> replay-tested deterministic harnesses.

Human experts still matter, but they should seed and audit boundaries rather than
label every trace. The target workflow is:

1. Experts define expensive-failure boundaries and domain invariants.
2. Detrix mines failures from real traces and artifacts.
3. Detrix proposes gates, reward components, and next-action policies.
4. Replay accepts or rejects those proposals against historical evidence.
5. Experts review unresolved ambiguity and boundary changes, not every run.

## Product Thesis

Detrix turns failure evidence into reusable domain harnesses.

Inputs:

- Agent traces.
- Runtime artifacts.
- High-level workflow goals.
- Good and bad outcome examples.
- Existing tools and scaffold logs.
- Domain constraints.
- Optional expert notes.

Outputs:

- Failure taxonomy.
- Deterministic gates.
- Reward functions.
- Replay fixtures.
- Training labels.
- Next-action policies.
- Domain pack.
- Environment adapter for `verifiers`, ORS/OpenReward, OpenEnv, or pi.

Loop:

1. Observe agent runs.
2. Mine recurring failure modes.
3. Infer what the workflow was trying to accomplish.
4. Propose deterministic checks and missing-evidence gates.
5. Replay gates against historical traces.
6. Reject gates that overfit, leak truth, or block known-good cases.
7. Package accepted gates as a harness/environment.
8. Use the harness for runtime governance and training export.

## Scaffold Boundary

Detrix should build a reference harness, but not make the generic scaffold its
moat.

The scaffold runs the agent: prompt loop, tools, memory, context, retries, and
planning. That market is crowded: pi, LangGraph, OpenClaw, OpenEnv, ART examples,
OpenHands, Codex, Claude Code, and custom Python loops.

Detrix should generate the evaluation and improvement harness around those
scaffolds:

- What artifacts matter?
- What counts as success?
- What must fail closed?
- What should be retried?
- What evidence is missing?
- What traces are trainable?
- What replay proves improvement?

Reference implementation is still necessary for demos. The first AgentXRD/local
Qwen reference harness should do only this:

```text
load evidence packet
call local Qwen for structured proposal
run deterministic Detrix/AgentXRD gates
emit reward vector + admission label
write trace/training row
replay challenger on held-out set
promote only if gates improve without precision regression
```

The reference harness proves the product, but the moat is the generated domain
reward boundary.

## AgentXRD Proof

AgentXRD should demonstrate that Detrix can build from failure modes, not just
handwritten gates.

The first proof should show Detrix doing this:

1. Read AgentXRD traces and row artifacts.
2. Infer recurring blockers:
   - provenance gap
   - support-only evidence
   - truth conflict
   - refinement failure
   - no evidence delta
   - unsafe promotion pressure
3. Generate candidate gates and next-action policies.
4. Replay them on binary20 and row packets.
5. Reject unsafe gates and keep useful gates.
6. Export an AgentXRD domain pack as a `verifiers` or ORS environment.
7. Run local Qwen against that environment.

The desired narrative:

> Detrix watched AgentXRD fail, inferred the failure modes, built deterministic
> gates, replay-tested them, and produced a local RLVR environment.

## CLI Shape

Initial command:

```bash
detrix synthesize-harness \
  --goal "identify PXRD phases without wrong ACCEPTs" \
  --traces outputs/diagnostics/binary20_governed_judge_cohort_v0 \
  --artifacts outputs/diagnostics/pxrd_failure_router_v0 \
  --domain xrd \
  --target verifiers
```

Expected outputs:

- `failure_taxonomy.json`
- `candidate_gates.py`
- `replay_report.json`
- `reward_schema.json`
- `training_routes.jsonl`
- `agentxrd_domain_pack/`
- `verifiers_env.py`

## What To Avoid

- Expert marketplace.
- Broad human labeling.
- Generic RL training platform.
- Generic agent framework.
- Generic observability.
- "Trace to fine-tune to cheaper models" without deterministic gates.
- Universal harness abstractions before the AgentXRD failure compiler works.

## Near-Term Focus

Build `detrix synthesize-harness` around AgentXRD first.

Minimum credible v0:

1. Input existing AgentXRD governed row artifacts.
2. Mine failure taxonomy from row packets, router decisions, and gate outcomes.
3. Generate a small candidate-gate set.
4. Replay candidate gates against known rows.
5. Emit a deterministic reward schema and training-route labels.
6. Package the result as a `verifiers` environment.
7. Keep local Qwen as proposer, not judge.

Do not claim self-improving Qwen until there is at least one governed positive,
a frozen held-out replay split, and a working local model path.
