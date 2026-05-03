# Detrix YC Pitch: Application Copy

Date: 2026-05-03

## One-Liner

Detrix makes high-stakes AI agents reliable enough for production.

Expanded:

> Detrix is a reliability harness for technical AI agents. It verifies each
> output, decides whether it can be accepted, retried, blocked, or trained on,
> and prevents bad traces from poisoning future models.

## 90-Second Pitch

Detrix makes high-stakes AI agents reliable enough for production.

Companies want to use AI agents for technical workflows, but agents make
plausible mistakes. That is dangerous twice: first when a bad output reaches
production, and again when that trace gets reused for fine-tuning.

Detrix wraps an agent workflow with a reliability harness: domain gates, failure
labels, replay tests, and training rules. It decides whether each output should
be accepted, retried, blocked, used as an eval, or exported for fine-tuning.

We start with materials characterization through AgentXRD. A local model proposes
the next XRD action; Detrix checks the scientific evidence and only lets properly
routed outputs become production results or training data.

LangGraph runs the agent. Unsloth trains the model. Detrix is the reliability
harness that decides what the agent is allowed to do and learn from.

## YC Application Answers

### What Are You Building?

Detrix is a reliability harness for high-stakes AI agents. It wraps one agent
workflow, captures traces, checks domain evidence, and decides whether each
output should be accepted, retried, blocked, used as an eval, or exported as
training data.

We start with AgentXRD, an X-ray diffraction workflow for materials
characterization. A local model proposes the next action or classification;
Detrix checks the proposal against deterministic scientific gates and only
allows correctly routed traces into training or promotion.

### What Problem Are You Solving?

Teams are starting to fine-tune and deploy agents from their own traces, but raw
traces are dangerous. A failed trace does not automatically mean "negative
example": it might mean missing evidence, bad provenance, tool failure,
support-only evidence, or "ask for more data."

Detrix turns agent outputs into governed decisions and raw traces into typed
learning signal instead of letting companies deploy or train on garbage.

### Why Now?

Three things happened at once: agent frameworks became good enough for real
workflows, fine-tuning became accessible to ordinary AI teams, and companies
started discovering that training on raw traces can make agents worse.

The bottleneck is the grader. Generic graders fail in technical domains because
a structurally valid output can still be scientifically or operationally wrong.

### Why Are You Different?

Pydantic validates structure. LangGraph runs workflows. Unsloth trains local
models.

Detrix decides what is safe to accept, retry, promote, or learn from.

For one trace, Detrix can output:

- `SFT-positive`: do more of this
- `DPO-negative`: prefer another action
- `eval-only`: keep as a regression case
- `request-more-data`: do not guess
- `excluded`: bad provenance or contaminated label

That routing is the product.

### What Is The First Product?

A Detrix reliability harness for one workflow: the gates, failure labels, replay
set, and training rules that make one agent workflow production-safe.

Install it around an agent, point it at outputs and traces, and get governed
decisions: accepted, rejected, retry, request more data, eval-only,
training-positive, training-negative, or excluded.

For AgentXRD, the first demo is:

```text
evidence packet
  -> local model proposal
  -> deterministic gate verdicts
  -> reward/training label
  -> replay-gated promotion decision
```

The honest v0 demo is:

> Detrix prevented unsafe scientific outputs from becoming production results or
> training data.

The stronger v1 demo is:

> Detrix used governed positives and negatives to improve a local model on
> held-out replay without increasing false accepts.

### Business Model

Start with paid pilots for one governed workflow.

- Pilot: $10k-$25k for one domain pack and replay harness.
- Production: $50k-$150k/year per governed workflow.
- Enterprise/on-prem: $250k+/year when traces cannot leave the customer
  environment.

Pricing is tied to governed workflows, evaluated trace volume, and local/on-prem
deployment. The budget anchor is existing lab, characterization, and engineering
software: Detrix sits beside those systems as the trust layer for AI agents.

### Market

The initial beachhead is R&D and engineering teams deploying AI agents in
materials, chemistry, biotech, semiconductor, and technical services workflows.

Near-term SAM assumption for YC discussion:

> 2,000 technical R&D teams with active agent or automation pilots x $50k/year
> average contract = $100M near-term SAM.

The broader market expands to every technical team that needs agent outputs,
traces, skills, prompts, actions, or model checkpoints verified before
production or promotion.

### Traction

Current honest version:

> We have a working internal AgentXRD governance demo and are using it to prove
> fail-closed trace admission. The demo shows Detrix blocking unsafe scientific
> outputs from becoming accepted results or training data, while preserving
> wrong traces as negatives, replay fixtures, and next-action examples.

Replace with stronger copy as soon as available:

> We are scoping pilots with [customer/team] around [workflow].

Or:

> We have an LOI to govern one technical agent workflow and prove Detrix can
> reduce expert review while producing safer training data.

### Why You?

I studied materials science at Georgia Tech and did hands-on XRD and materials
workflow work. I have also built applied ML/agent systems and high-stakes
automation where noisy evidence and false positives matter.

I am not starting with generic agent evals. I am starting with a scientific
workflow I understand deeply enough to know why schema validation is not enough.

### Why Will This Become Big?

Every serious agent deployment eventually needs the same control plane: capture
traces, evaluate evidence, route failures, improve prompts/skills/models, and
promote only with replay proof.

Models, trainers, and runtimes will commoditize. The durable asset is the domain
admission boundary.

## Lines To Keep

Use these in the YC app or interview:

> Bad traces are dangerous twice: first when they reach production, and again
> when they become fine-tuning data.

> LangGraph runs the agent. Unsloth trains the model. Detrix is the reliability
> harness that decides what the agent is allowed to do and learn from.

> The product is the routing: positive, negative, eval-only, request-more-data,
> or excluded.

> Detrix prevented unsafe scientific outputs from becoming production results or
> training data.

## Lines To Avoid

Do not open with:

- RLVR
- GRPO / DPO / SFT / LoRA
- Prime / NeMo / ART / ORS landscape details
- "we automate science"
- "Qwen already self-improves"
- "domain pack" before explaining the problem

Technical details can come after the plain-English pitch lands.
