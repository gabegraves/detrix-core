# YC GTM Demo And Outreach Plan - 2026-04-27

Status: approved brainstorming spec for the 2026-04-27 to 2026-05-04 YC customer-discovery sprint.

Scope: demo narrative, first customer wedge, customer-repo implementation model, Langfuse trace-diagnosis boundary, and open-core moat. This is a planning artifact, not an implementation claim.

## Core Question

The demo and outreach should answer one customer question:

> If we let an AI agent touch expensive technical work, how do we know not only which outputs are safe, but which next corrective experiment is allowed, evidence-backed, policy-compliant, and worth running?

The problem is not "teams need another agent framework." The problem is that teams already have agents, traces, Claude/Codex reviews, and observability tools, but still lack a defensible production decision boundary.

After the PydanticAI review, treat the default competitor baseline as even stronger:

> A capable Python team can use PydanticAI plus Codex or Claude to build typed agents, structured outputs, tool approvals, eval datasets, traces, and custom validators. Detrix only matters if it proves the domain admission layer those tools do not ship: evidence provenance, replay against prior accepted/rejected cases, failure taxonomies, promotion rules, and governed training eligibility.

## Positioning

One-line positioning:

> Run agents where sensitive data already lives. Detrix adds local governance, clarification, audit trails, and promotion evidence so repo, database, and science agents can move from impressive demos to defensible production.

Short customer-facing version:

> Your agent already creates traces. Detrix turns failed traces into governed next actions: diagnose, propose a bounded fix or experiment, policy-check data and resources, execute, compare evidence delta, and stop at ACCEPT, SET, REQUEST_MORE_DATA, or a hard policy limit.

Do not pitch Detrix as:

- a generic pipeline framework
- a replacement for pi, LangGraph, Langfuse, Braintrust, or Claude/Codex
- a replacement for PydanticAI, Pydantic evals, or typed agent frameworks
- a trace viewer
- "fine-tune on traces" by itself
- a horizontal RLVR platform before customer urgency is proven

Pitch Detrix as:

- a local-first governance and improvement layer for production-agent reliability
- a domain admission layer that can sit after PydanticAI, pi, LangGraph, Codex, Claude, Hermes, or raw Python agents
- post-hoc evaluation of agent outputs, not action-space wrapping
- a way to turn failures into structured eval, training, and promotion evidence
- a governed self-correction loop for high-stakes agents, not just a trace classifier
- a policy-checked action recommender that decides what experiment may run next
- an evidence-delta comparator that proves whether the next run improved the decision boundary
- a private deployment path for sensitive repos, databases, and domain workflows

## Moat And Defensibility

Do not frame the moat as "we use Claude/Codex/Qwen as a judge" or "we fine-tune on traces." Those are implementation tactics and are easy to copy.

The defensible asset is the compounding validated decision boundary per domain:

- failure corpora with near misses, false accepts, support-only cases, and ambiguous cases
- deterministic gate semantics that encode what counts as valid evidence
- provenance rules for what may become benchmark-grade, eval-only, or training-positive
- action policies for which next experiments are allowed after failure
- evidence-delta ledgers that prove whether a retry improved the decision boundary
- calibration and wrong-accept analysis over held-out replay surfaces
- governed SFT/DPO/GRPO exports that exclude unsafe or unverified traces

The customer can use Claude or Codex to inspect one trace. Detrix should be the reusable system that decides what survived, what failed, what may be tried next, and what is safe to learn from.

The customer can also use PydanticAI to force structured outputs and run evals. That is table stakes. Detrix must show the next layer:

- a well-typed agent output that is structurally valid but still rejected because domain evidence is missing or unsafe
- a failed trace routed to DPO/eval-only rather than SFT-positive by explicit admission policy
- a policy-approved next experiment with resource and provenance limits
- a replay result that proves whether the proposed change improved the decision boundary without increasing wrong accepts
- a training/export row that exists only after gate, provenance, replay, and promotion rules agree

Near-term domain packs:

- XRD / scientific instrumentation: PXRD gates, CIF provenance, Pawley/Rietveld evidence, support-only rules, terminal routes, and wrong-ACCEPT constraints.
- Options trading / market agents: real-priced evidence, replay/live parity, risk gates, stale-data gates, alert hygiene, and promotion packets for strategies or alerts.

YC-safe claim:

> Detrix compounds domain-specific reliability assets. Each deployment creates reusable gates, evals, provenance rules, failure taxonomies, calibration data, action policies, and governed training traces.

## ICP Decision

Materials science remains the proof domain. It is not the only first customer wedge.

Primary customer-discovery wedge:

> Applied AI, platform, or product engineering teams with production or near-production agents touching customers, regulated workflows, code, data, financial decisions, scientific work, or internal operations where errors are expensive.

Outreach allocation for this sprint:

- 70% production-agent reliability teams
- 30% materials, science, R&D, and technical-workflow teams

The hair-on-fire customer is not simply "materials teams." The hotter pain is likely teams that already tried to deploy agents and hit production failures, audit gaps, human-review bottlenecks, or trace-review overload.

Signals to prioritize:

- agents already in production or pilot
- customer-facing or regulated outputs
- high manual review cost
- Langfuse, LangSmith, Braintrust, or custom tracing already installed
- public discussion of evals, hallucinations, tool failures, or reliability
- team cannot send sensitive traces to large providers
- unclear promotion process for model, prompt, skill, or policy changes

## Demo Architecture

The demo should be problem-first and artifact-backed:

1. Open with production-agent incident framing.
2. Show a hard-mode proof domain where wrong acceptance is worse than abstention.
3. Replay one AgentXRD-style artifact or governed run that failed or abstained.
4. Diagnose why the run failed or abstained.
5. Propose the next allowed scientific or workflow action: more data, candidate expansion, refinement retry, policy-safe replay, or stop.
6. Policy-check data access, compute budget, external sources, support-only status, and promotion eligibility.
7. Execute one bounded experiment or replay when policy allows it.
8. Compare evidence delta against the prior run.
9. Iterate until ACCEPT, SET, REQUEST_MORE_DATA, or a hard policy/resource limit.
10. Export eval/training rows only when deterministic gates and provenance allow it.
11. Close by mapping the same pattern to support, finance, coding, database, and science agents.

The demo must also include a commodity-framework contrast:

1. Run or replay a PydanticAI/Codex/Claude-style agent step that produces valid structured output.
2. Show that schema validity is not enough: the output is rejected or routed to REQUEST_MORE_DATA because evidence, provenance, replay, or domain policy is insufficient.
3. Run the same admission packet through Detrix and emit the exact route: SFT-positive, DPO-negative, eval-only, excluded, governed next action, or hard stop.
4. Show a local Qwen 3.6 agent or challenger consuming the governed packet and proposing the next action.
5. Detrix admits or rejects the Qwen-proposed transition under the same domain gates. The proof is the admission decision and replay evidence, not Qwen's raw answer.

AgentXRD is the evidence source and domain narrative. It should not be overclaimed as a live customer-ready product. The safe claim is that it demonstrates a high-stakes abstention and domain-gate pattern.

Safe demo claims:

- Detrix captures runs, gates, verdicts, and evidence.
- Detrix separates accepted, rejected, abstained, and support-only outputs.
- Detrix creates audit-ready traces and training or eval rows from governed outcomes.
- AgentXRD is proof that domain gates matter when wrong acceptance is costly.

Unsafe demo claims:

- AgentXRD is broadly customer-ready.
- Detrix prevents every production failure.
- Detrix has already proven quality improvement on real customer production traces.
- Mission Control already proves measured self-improvement.
- Local Qwen or pi is the main reason buyers care.

Required Qwen 3.6 honesty boundary:

- Say "we are demonstrating the governed loop on a local Qwen 3.6-class model" only when the local run actually executes.
- If the local model path is blocked, say it is blocked and replay the same admission packet with stored artifacts.
- Do not claim Qwen 3.6 is reliable because Detrix accepted one output.
- Do not claim training improved Qwen 3.6 until a before/after held-out replay shows improvement without precision regression.
- The buyer-facing proof is that Detrix can govern a local model without sending sensitive traces to a frontier provider.

## Customer Repo And Database Implementation

Detrix should not require customers to upload sensitive repos, DB rows, or traces to Detrix Cloud.

Default architecture:

1. `detrix init` inside the customer repo or VPC.
2. `.detrix/policy.yaml` defines allowed sources, forbidden paths/tables, PII rules, egress policy, model endpoints, allowed experiment actions, max iterations, resource budgets, allowed artifact sources, support-only handling, promotion eligibility rules, and stop conditions.
3. Read-only connectors parse repos, DB replicas, logs, traces, CI output, and pi/LangGraph agent events.
4. A privacy ingress pipeline validates, classifies, redacts, minimizes, and normalizes data before storage.
5. Evidence lands in customer-controlled SQLite or Postgres.
6. Local model routing uses Qwen/vLLM/Ollama or customer-approved endpoints by policy.
7. Remote provider calls are disabled unless explicitly allowed.
8. Export defaults to signed summaries, hashes, metrics, schemas, and failure taxonomies, not raw payloads.

Fail closed rules:

- no policy means no sensitive parse
- no egress approval means no external model/provider call
- no baseline means no improvement claim
- no resolved clarification means no promotion
- no gate-passed provenance means no training/export eligibility
- no allowed next action means no experiment execution
- no resource budget means no bounded replay or training run
- no evidence delta means no improvement claim
- hard policy limit routes to REQUEST_MORE_DATA or blocked, never silent continuation

## Clarification Loop

Detrix should ask questions the way strong planning tools do: after context gathering, one high-leverage question at a time, only when the system lacks authority or evidence.

Clarification should be a product state, not just chat behavior.

Required `ClarificationState` fields:

- `run_id`
- `question_id`
- `blocking_gate`
- `missing_evidence`
- `question`
- `allowed_responses`
- `assumptions`
- `non_goals`
- `resolved_by`
- `resume_command`

Promotion, export, or training eligibility must pause until required clarification is resolved.

## Langfuse Boundary

Detrix should integrate with Langfuse, not compete with it as a trace viewer.

Mission Control evidence shows the distinction clearly:

- Langfuse-style collection and readback are useful for observability.
- Trace review can produce suggestions and audit artifacts.
- That does not prove quality improvement unless baselines, post-change measurements, and replay/eval outcomes exist.

Observed local Mission Control state on 2026-04-27:

- `langfuse_traces`: 3159
- `improvement_suggestions`: 1258
- applied suggestions: 52
- `suggestion_effectiveness`: 0
- `audit_session_grades`: 0

Interpretation:

> Mission Control proves the cockpit and diagnosis substrate. It does not yet prove the measured improvement loop.

Customer response when they already use Langfuse:

> Good. Detrix should use your Langfuse traces. Langfuse tells you what happened. Detrix turns those traces into governed failure taxonomies, replayable evals, training eligibility, and promotion evidence.

Detrix adds:

- failure taxonomy
- deterministic and domain-specific gates
- trace eligibility filters
- replayable eval set construction
- before/after promotion packets
- regression accounting
- local/private data handling
- clarification states for missing evidence
- governed training/export rows

Core boundary:

> Trace diagnosis is the input, not the product. The product is the governed decision: reject, ask, fix, replay, promote, or train.

## Open-Core Moat

If Detrix is open source and runs locally with Qwen inside a pi agent harness, customers should not pay for the basic local loop.

Free/open core:

- local runner
- canonical schemas
- SQLite/Postgres evidence store
- pi/Qwen/Ollama/vLLM support
- basic gates
- simple local reports
- Langfuse/JSONL trace import

Paid surfaces:

- domain gate packs
- private deployment appliance
- VPC or air-gapped install support
- SSO/RBAC/SCIM/audit retention
- benchmark suites and holdouts
- CI promotion gates
- signed evidence bundles
- governed improvement runs
- custom repo, database, and science workflow integrations
- support, SLA, and compliance documentation

The moat is not the harness, model, or trace viewer. The moat is:

- validated gates customers trust more than LLM judges
- holdout benchmarks that become acceptance standards
- failure taxonomies and governed trace metadata
- promotion evidence showing improvement without regression
- private deployment expertise for sensitive data environments
- workflow-specific integration depth

## Outreach Plan

Primary target titles:

- Head of AI
- Applied AI lead
- AI platform lead
- product engineering lead for agent workflows
- CTO/founder of vertical AI product
- R&D automation lead
- scientific computing lead
- data platform lead with AI-agent ownership

Problem-led outbound angle:

> Saw you are working on production agents/evals/tracing. Curious how you decide when an agent output is safe to promote versus requiring human review. We are building a local-first governance layer that turns traces into gate verdicts, clarification states, and replayable eval/training signal. Are you already seeing failures that observability alone does not resolve?

Discovery questions:

- Where are agents already touching real users, code, data, or decisions?
- What happens when the agent is wrong?
- How do you know a trace is safe to learn from?
- What must be true before a model, prompt, policy, or skill change is promoted?
- Which data cannot leave your environment?
- Do you already use Langfuse, LangSmith, Braintrust, or a custom trace store?
- What do those tools still not answer for you?
- Would you pay for a one-workflow pilot that produces a promotion packet and replayable eval set?

Commitment ladder:

1. Problem interview.
2. Private trace/audit review on one workflow.
3. Written pilot scope with named workflow and success metric.
4. Paid founding pilot.
5. Design-partner LOI if payment is blocked.

Weak signals:

- generic interest
- no named workflow
- no painful failure mode
- no data access path
- no owner for promotion decisions
- "we already have Langfuse" with no unresolved reliability pain

## First Pilot Shape

The first customer pilot should not be "install the whole platform."

Pilot promise:

> In one week, Detrix will connect to one sensitive agent workflow, ingest local traces or artifacts, classify failures, add one to three deterministic/domain gates, and produce a promotion packet showing what is safe, unsafe, unknown, and eligible for eval/training.

Pilot deliverables:

- local install or VPC sidecar
- policy file and egress map
- one connector
- one normalized artifact schema
- one to three gates
- trace failure taxonomy
- clarification queue
- replay/eval set from real failures
- promotion packet

Success metric examples:

- reduce unclassified failures by 50%
- identify top three repeat failure modes from production traces
- create a regression set from ten real failures
- block unsafe promotion when required evidence is missing
- prove no regression on the existing holdout replay
- generate training/export rows only from gate-passed traces

## Required Build Implications

Current repo assets:

- bridge ingestion exists
- AXV2 adapter exists
- audit and trajectory stores exist
- governed trajectory/export concepts exist
- Langfuse observer exists
- Mission Control can collect Detrix audit DBs
- `REQUEST_MORE_DATA` exists as a verdict concept

Missing for this product shape:

- adapter registry
- PydanticAI trace/output adapter
- pi extension implementation
- privacy ingress policy layer
- redaction/minimization middleware
- customer repo/DB connectors
- persisted clarification queue
- Langfuse import to canonical artifact schema
- baseline snapshot capture
- suggestion/effectiveness measurement loop
- promotion packet generator
- signed evidence bundle export
- next-action recommendation schema
- policy-checked experiment runner
- iteration ledger with prior evidence, experiment action, new evidence, and delta
- hard stop evaluator for policy, budget, provenance, and promotion limits
- AgentXRD-style terminal verdict mapping: ACCEPT, SET, REQUEST_MORE_DATA, blocked

The immediate implementation plan after this spec should be a narrow proof path:

1. Define canonical trace/artifact payload plus sensitivity profile.
2. Add adapter registry with AXV2, PydanticAI, and Langfuse/JSONL import.
3. Add policy-gated privacy ingress.
4. Persist clarification states.
5. Generate a promotion packet from one replayed artifact set.
6. Add a governed-next-action packet that records diagnosis, allowed action, policy checks, execution result, evidence delta, and terminal route.
7. Add a local Qwen 3.6 demo lane that consumes the governed packet, proposes one next action, and has Detrix admit or reject the proposed transition.
8. Export the resulting governed examples to eval/training rows with explicit route labels: SFT-positive, DPO-negative, eval-only, excluded, or hard stop.

## Transition-level admission framing

Use the Hermes-style drift question as a differentiation point:

> Inspectable memory and skills are useful, but observability is not control. Detrix constrains which proposed state transitions are admissible: memory updates, skill changes, policy edits, evidence admission, promotion decisions, and training/export rows all require explicit gates, provenance, replay, and domain policy.

Short phrasing:

> Hermes makes agent learning visible. Detrix makes agent learning admissible.

Demo implication: show an agent or judge proposing an unsafe learning/update path, then show Detrix rejecting that transition, emitting a governed next action, and preserving training/export safety.

## Final Demo Close

Use this close:

> Observability tells you what happened. Detrix tells you what is safe to do next — and keeps trying policy-compliant experiments until the workflow reaches ACCEPT, SET, REQUEST_MORE_DATA, or a hard stop.

Expanded close:

> Your agents already produce traces. Your team can already ask Claude or Codex to inspect them. The missing layer is a governed self-correction boundary: which traces are safe, which failures need clarification, which next experiments are allowed, which fixes actually improve a replay set, when to ask for more data, and which outcomes are eligible for training or promotion. That is Detrix.
