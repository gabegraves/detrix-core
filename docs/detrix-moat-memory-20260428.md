# Detrix Moat Memory - 2026-04-28

Status: repo-local strategic memory. This is a durable reference for Detrix positioning, YC demo framing, and future agent guidance. It is not an implementation claim.

## Executive Thesis

Detrix should not claim defensibility from using Claude, Codex, Qwen, or any other model as a judge. Those are replaceable components.

The moat is the accumulated, validated, domain-specific reliability infrastructure that turns high-stakes agent traces into safe decisions, allowed next experiments, and governed training data.

Short version:

> Codex, Claude, Hermes, pi, or internal agents make things happen. Detrix decides what survived, what failed, what may be tried next, and what is safe to learn from.

After evaluating PydanticAI, add it to the same category as pi, LangGraph, Codex, and Claude: useful runtime/eval infrastructure, not the Detrix moat.

## What Is Easy To Copy

Competitors can copy these quickly:

- calling Claude/Codex/Qwen as a judge
- typed Pydantic/PydanticAI structured outputs
- PydanticAI tool approval, graph, eval, or observability scaffolding
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

PydanticAI plus Codex or Claude can get a strong team most of the generic way there:

- typed agent I/O
- structured outputs
- tool calls and approvals
- eval datasets
- custom evaluators
- trace/spans through observability tooling
- coding-agent assistance to write validators quickly

That is not enough for Detrix's target customer unless the team also owns and maintains the domain decision boundary. Detrix must therefore compete on prebuilt and compounding admission assets: domain gates, evidence provenance, replay surfaces, false-accept calibration, failure taxonomies, policy-approved next actions, and governed training/export eligibility.

The decisive demo pattern is:

1. PydanticAI or a coding agent produces valid structured output.
2. Detrix rejects or abstains because domain evidence is missing, provisional, support-only, non-replayable, or unsafe to promote.
3. Detrix emits a governed next action or a training route label.
4. A local Qwen 3.6-class model proposes the next step from that packet.
5. Detrix admits or rejects the proposed transition using the same gates and replay policy.

If that loop is not visible, the product looks like consulting plus validators.

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

Expanded rule after the PydanticAI comparison:

> PydanticAI can make an agent typed. Detrix makes the agent's learning admissible.

Do not say Detrix can do something a user with PydanticAI and Codex cannot do at the framework level. Say Detrix gives them the validated domain gates, replay corpus, provenance rules, promotion packets, and training eligibility labels they would otherwise have to invent, calibrate, and maintain themselves.

## Local Qwen 3.6 Proof Requirement

The next product proof should show Detrix working around a local Qwen 3.6-class agent or challenger.

Required proof shape:

1. Qwen proposes a structured next action, memory update, skill change, policy change, evidence admission, or training/export route.
2. Detrix evaluates the proposal against a deterministic evidence snapshot and domain policy.
3. The result is an admission packet: admitted, rejected, REQUEST_MORE_DATA, eval-only, DPO-negative, SFT-positive, excluded, or hard stop.
4. Replay verifies that admitted updates improve or preserve the validated decision boundary.

AgentXRD demo shape:

- Qwen is the local proposer around the AgentXRD trace, not the judge.
- AgentXRD gates plus Detrix admission are the RLVR environment: they turn a trace and proposal into deterministic rewards, blocker labels, evidence-delta measurements, training eligibility labels, and replay promotion decisions.
- The reward target should be a narrow verifiable decision task, for example `trace -> blocker_class`, `trace -> allowed_next_action`, `proposal -> admitted/rejected`, or `evidence_delta -> promote/reject/trainable`.
- "Self-improving" means the harness accumulates gate-scored positives, negatives, and eval-only traces; runs SFT/LoRA or DPO on admitted examples; and promotes a challenger only after held-out replay proves no precision regression.
- Do not describe the entire XRD workflow as an RL environment at first. Start with row-level or transition-level AgentXRD tasks where the deterministic gates already produce falsifiable labels.

Honesty boundary:

- Qwen is not the judge and not the moat.
- One accepted Qwen output is not a model-quality claim.
- No self-improvement claim is valid without before/after held-out replay.
- If the local Qwen runtime or training path is blocked, report the blocker and use replay artifacts rather than implying a live loop.

## Small-Model Training Memory - Labonne / Liquid AI Talk (2026-05-02)

Source processed through the ParabolaHunter YouTube path: AI Engineer video
`fLUtUkqYHnQ`, "Everything I Learned Training Frontier Small Models - Maxime
Labonne, Liquid AI" (uploaded 2026-04-29). Repo-local extraction used
`backend.collectors.youtube_collector.fetch_transcript` plus local Qwen-style
structured analysis.

Detrix takeaway:

> Small/local models should be narrow verifiable workers, not mini-frontier
> generalists. Detrix's product value is the environment, verifier, and
> admission boundary around those workers.

Apply this to Detrix:

- Treat local Qwen/Hermes-class models as task-specialized actors for trace
  classification, blocker routing, next-action proposal, schema repair, and
  evidence-delta explanation.
- Do not start with RLVR. First build cold-start SFT/LoRA examples that match
  the exact later reward task: `trace -> blocker_class`, `trace -> allowed_next_action`,
  `evidence_delta -> promote/reject/trainable`, and `proposal -> admitted/rejected`.
- Use DPO for chosen/rejected trajectory pairs once deterministic gates can say
  which rollout is better. Use GRPO/RLVR only after enough verifiable task
  environments and held-out replay checks exist.
- Track doom loops as governed failures: repeated same action, recursive retry,
  repeated tool call, same blocker with no evidence delta, or long reasoning
  that never reaches a valid final answer.
- Compensate for low model knowledge with tools, retrieval, and deterministic
  evidence snapshots. Do not ask the local model to memorize crystallography,
  trading rules, or customer policy.
- Represent long traces as structured state snapshots and evidence ledgers
  instead of raw context dumps.

Product implication:

> Detrix is a narrow verifiable environment factory for local small models.
> The training loop is useful only after Detrix has admitted the examples.

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

## Transition-Admission Memory - Hermes Thread Update (2026-04-29)

A Reddit discussion about Hermes-style self-improving agents sharpened the Detrix positioning.
The core question was whether a runtime built from memory, skills, and heuristics can prevent
long-term behavioral drift without a formal state-transition system:

```text
S = agent state (memory + skills + context)
E = new interaction / tool result
δ(S, E) -> S'
```

Hermes-style systems emphasize plaintext state, inspectability, and post-hoc skill refinement.
That is valuable, but it is mostly observability plus correction. Detrix should be positioned
one layer stronger: transition-level admission.

Detrix's durable claim should be:

> Agents may propose state transitions, but Detrix decides whether those transitions are
> admissible under explicit, domain-specific policy.

This means Detrix is not just trace logging, not just a judge, and not just a retry loop.
It is the harness that constrains which state changes are allowed to become trusted state.

### Required State-Transition Shape

Detrix should model durable learning updates as proposals:

```text
prior trusted state S
+ event / trace / tool result E
-> proposed transition P
-> policy/domain validators V
-> admitted trusted state S' OR rejected transition + governed next action
```

Raw agent output should not directly mutate trusted memory, skills, domain evidence,
training sets, or promotion state. It should emit a proposal that Detrix admits, rejects,
or routes to a bounded next action.

### Practical Invariants

Detrix cannot honestly promise global formal guarantees for open-ended agents. It can and
should promise enforceable local invariants:

- no export without an admission packet;
- no benchmark claim without a domain evidence tuple;
- no skill activation without fixture/regression replay;
- no memory promotion without source/provenance and scope;
- no policy update without replay against prior accepted/rejected cases;
- no LLM/judge score overriding deterministic domain gates;
- no support-only/proxy/provisional evidence becoming benchmark-grade without a promotion packet.

### Product Positioning

Hermes makes agent learning visible. Detrix should make agent learning admissible.

Short competitive framing:

> Agent runtimes decide what to try. Detrix decides what survived, what may safely change
> trusted state, what must be replayed, and what is safe to learn from.

### AgentXRD Concrete Example

For AgentXRD, the transition from `pattern_origin=unknown` to
`pattern_origin=experimental` must not happen because a folder is named CNRS, EMPA, HKUST,
or USC. It requires a source contract, source evidence path, reviewed labels, wavelength /
profile provenance, sample allowlist, matched CIF provenance, and replayable policy version.

Blocked transitions should become `GovernedNextAction` rows, not dead ends. This preserves
self-correction while preventing unsafe drift.

## Telegram Gate Memory - Product Boundary Update (2026-05-02)

The OpenClaw Telegram formatting failure is the simplest non-scientific example of the
Detrix thesis:

> Instructions are advisory. Gates are enforceable.

The user repeatedly told the model to emit human-readable Telegram topic messages, but the
model kept compressing pseudo-bullets into one dense paragraph. The correct fix is not a
better prompt or a skill alone. The correct fix is a deterministic outbound gate at the
Telegram send boundary:

```text
model output
-> telegram_readability_gate
-> pass / rewrite / block with fallback
-> sendMessage
```

For this case:

- **Harness:** OpenClaw Telegram gateway.
- **Task:** produce a human-readable Telegram topic reply.
- **Gate:** validate/rewrite spacing, bullet newlines, length, tables, code dumps, and fallback behavior.
- **Reward:** pass if the message is Telegram-readable; reject or rewrite if it is dense, malformed, or overlong.
- **Trace:** original model output, gate decision, rewritten/admitted output, and delivery result.
- **Training data:** bad dense paragraph paired with admitted readable message.

A skill can document the desired behavior. A hook can provide the delivery mechanism. The
gate is the product primitive because it deterministically admits, rewrites, or blocks the
state transition before it reaches the user.

This is a good public analogy because everyone understands it: "I told the model to format
Telegram messages. It ignored me. Detrix made the formatting contract enforceable." The
AgentXRD version is the same pattern with higher stakes: "I told the model to be
scientifically careful. It guessed. Detrix made the scientific contract enforceable."

### Product Boundary

Detrix should not try to own every harness. The harness is how the agent runs:

- OpenClaw;
- pi;
- LangGraph;
- Claude Code;
- Codex;
- custom Telegram bots;
- AgentXRD.

Detrix's product is the governed environment generated around that harness:

- tasks and replay cases;
- deterministic gates;
- failure taxonomy;
- admissible next actions;
- reward labels;
- training/export eligibility;
- promotion rules;
- evidence ledgers.

The concise product identity is:

> Detrix is a failure-to-environment compiler for agents.

Given failed traces, user goals, examples, artifacts, operational constraints, and domain
rules, Detrix should produce deterministic gates, replayable evals, reward functions,
bounded next actions, training/export labels, and promotion criteria.

### Anti-Commoditization Memory

Do not say the non-commoditized asset is:

- the generic harness;
- a prompt hook;
- a formatting skill;
- a deterministic script by itself;
- a Qwen/Claude/Codex judge;
- a fine-tuning loop.

Those are copyable implementation pieces. The durable asset is the compounding environment
state created by repeated deployment:

- observed failure modes;
- accepted/rejected replay cases;
- gate semantics that survived historical replay;
- policy-approved rewrite/block/next-action behavior;
- evidence of which gates overfit or underfit;
- training rows with admission labels;
- promotion tests that prevent regressions;
- domain/operator-specific calibration.

In the Telegram example, a competitor can copy a newline formatter. They cannot copy the
customer's accumulated communication policy, failure corpus, topic-specific formatting
regressions, accepted/rejected examples, and replay suite. In AgentXRD, the same principle
is stronger: a competitor can copy a gate shape, but not the accumulated PXRD failure
taxonomy, provenance decisions, calibration evidence, wrong-ACCEPT history, support-only
boundaries, and governed training eligibility corpus.

The moat is therefore not "we have gates." The moat is:

> Detrix turns repeated operational failures into validated environments that become harder
> to reproduce with every admitted trace, replay, calibration update, and promotion
> decision.
