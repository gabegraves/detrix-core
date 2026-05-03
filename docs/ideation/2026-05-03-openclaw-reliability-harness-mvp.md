---
date: 2026-05-03
topic: openclaw-reliability-harness-mvp
focus: guaranteed OpenClaw Telegram readability MVP that can expand to AgentXRD and ParabolaHunter
mode: repo-grounded
---

# Ideation: OpenClaw Reliability Harness MVP

## Grounding Context

This run used `compound-engineering:ce-strategy` followed by `compound-engineering:ce-ideate`.
The subject is concrete enough to proceed without further interview: build the first
Detrix MVP around OpenClaw Telegram messages that keep becoming non-human-readable
despite repeated instructions.

User-provided canonical failure case: a Telegram screenshot where OpenClaw/J.A.R.V.I.S.
returns a dense phone-hostile paragraph with inline bullets, then acknowledges the
readability problem in another dense paragraph. The important failure is not only
formatting; it is that prompt instructions and self-critique did not create a reliable
send boundary.

Trace grounding:

- The public VM is reachable as `clawdbot@192.168.123.10` or
  `clawdbot@100.107.43.69` with `~/.ssh/id_ed25519`, per the Clawdbot ansible
  inventory.
- The requested public-VM operational log directory exists at `~/.openclaw/logs`, but the
  richer message/session trace corpus is under
  `~/.openclaw/agents/main/sessions/*.jsonl` and `~/.openclaw/cron/runs/*.jsonl`.
- The local host's `~/.openclaw` tree is not authoritative for Telegram failures; use the
  public VM for trace ingestion and replay fixture extraction.
- The public VM service `openclaw-gateway.service` was live during inspection, and its
  journal showed the current failure mode: `telegram-format-guard` loads, but AGENTS.md is
  truncated at the injection limit, and Telegram sends still happen without a hard
  readability admission step.
- Real trace evidence found:
  - `~/.openclaw/agents/main/sessions/4f0ed61b-2730-4a93-a198-2c0abf976172-topic-38.jsonl`
    line 70: assistant sent a 1,126-character single-line summary with six inline `•`
    separators and zero bullet lines.
  - The same session lines 71-74 show the injected `telegram-format-guard`, the user's
    complaint, and the model's apology. The apology itself still had a 241-character max
    line, proving the fix cannot rely on self-critique.
  - `~/.openclaw/agents/main/sessions/5c7f6386-d35c-4bef-81da-5460e183fc07-topic-971.jsonl`
    line 107 captured the screenshot's Hyperagent case: a 994-character single line,
    one paragraph, six inline `•` separators, zero bullet lines.
  - The same session line 109 captured the follow-up apology as a 671-character single
    line with no bullet lines.

Reusable local infrastructure:

- Detrix already has the core gate contract in `src/detrix/core/governance.py`:
  `Decision`, `VerdictContract`, `GovernanceGate`, and `DomainEvaluator`.
- Detrix already has `GovernedTrajectory` in `src/detrix/core/trajectory.py`; rejected
  traces cannot become SFT rows.
- Detrix already has append-only trajectory storage and version-contamination handling in
  `src/detrix/runtime/trajectory_store.py`.
- Detrix already has SFT/DPO/GRPO export surfaces in
  `src/detrix/improvement/exporter.py`, but those should only be used after admission
  labels are correct.
- Detrix AgentXRD replay/promotion patterns in `src/detrix/agentxrd/promotion_packet.py`
  and `src/detrix/agentxrd/drift_replay.py` are reusable as a template for OpenClaw.
- AI_ATL25 has useful trace capture/conversion surfaces, especially
  `python-pipeline/slm_swap/langfuse_dataset.py`, `run_dummy_pipeline.py`, and the local
  trace visualization described in `AGENT_TRACE_VISUALIZATION_README.md`. Borrow capture
  and offline JSONL conversion, not its placeholder training/status claims.

External source grounding:

- Hermes Agent is directly relevant because its README describes Telegram/gateway
  operation, self-improving skills/memory, session search, and research trajectory
  generation. It is a strong future runtime/gateway candidate, but switching runtimes is
  not the fastest proof if the current failure exists in OpenClaw.
- pi-mono is a broad TypeScript AI-agent toolkit with agent core, coding-agent CLI,
  session sharing, and unified LLM APIs. It is still a good future harness substrate, but
  it is not required to fix an existing Telegram send-boundary failure.
- Prime Verifiers defines environments as dataset + harness + reward/rubric and
  integrates with PRIME-RL and hosted training. That is useful after Detrix has admission
  packets and replay cases; it is not the v0 reliability harness.

Process note: five read-only subagents were used after closing stale threads: Detrix reuse,
AI_ATL25 reuse, runtime choice, critic review, and Clawdbot VM access/log mapping. This
artifact uses those scans plus direct repo, public-VM, and web inspection.

## Raw Candidate Ideas

1. **Inline Telegram Readability Gate**
   Add a deterministic send-boundary gate that scores text before Telegram delivery and
   emits `PASS`, `REWRITE`, or `BLOCK`.

2. **Replay-First Formatter Promotion**
   Treat the formatter/prompt/skill as a promoteable policy. Any change must pass a frozen
   replay suite of real OpenClaw bad outputs before it can ship.

3. **Qwen Fine-Tune Immediately**
   Build SFT data from bad and fixed Telegram messages, fine-tune Qwen 3.6, and demo model
   improvement.

4. **Hermes Migration First**
   Move OpenClaw to Hermes Agent and use Hermes's gateway/skill/memory machinery as the
   reliability harness.

5. **pi-mono Extension First**
   Build a Detrix pi extension and use pi sessions as the canonical harness/runtime before
   solving Telegram readability.

6. **Prime Verifiers Environment First**
   Package Telegram readability as a Prime Verifiers environment and optionally run
   PRIME-RL.

7. **Trace Digest + Admission Packet Compiler**
   Build a thin importer that reads OpenClaw JSONL logs, extracts input/output/delivery
   spans, and emits Detrix admission packets plus governed trajectories.

8. **OpenClaw + AgentXRD Paired Demo**
   Use OpenClaw for the visible 60-second readability proof, then show one AgentXRD packet
   using the same admission contract so the demo is not “just a formatter.”

9. **AI_ATL25 Local Trace Viewer Reuse**
   Borrow the local JSONL trace viewer/data shape for self-hosted evidence review.

10. **LLM Judge For Readability**
    Use a judge model to decide whether the message is readable and generate rewrite
    feedback.

## Ranked Ideas

### 1. OpenClaw Readability Admission Pack

**Description:** Build the first domain pack around Telegram sendability:
`raw_message -> readability_gate -> admission_packet -> admitted_message`.
The deterministic gate should check phone-readable constraints:

- max message length for inline send
- max paragraph/chunk length
- required blank lines between bullets or sections
- inline bullet separators such as `•` split into real lines
- no dense paragraph-bullets
- no tables/code dumps in Telegram unless explicitly requested
- long version saved elsewhere with a short Telegram summary

**Warrant:** direct: The user screenshot shows repeated prompt failure and dense
Telegram output; local Detrix already has `GovernanceGate` and `VerdictContract` to
represent the admission decision.

**Rationale:** This is the most guaranteed-to-work MVP because the gate is deterministic,
the expected output is human-visible, and success does not require model training. It
also proves the core Detrix claim: prompts are advisory; admission is enforced inline.

**Downsides:** Alone, this can look like a formatter. It needs replay/promotion evidence
and an AgentXRD bridge to avoid looking trivial.

**Confidence:** 92%

**Complexity:** Low

**Status:** Ready for implementation; public-VM evidence confirms prompt-only failure.

### 2. Public-VM OpenClaw Trace Digest

**Description:** First implementation task should run on the public VM or against copied
VM logs:

```bash
ssh -i ~/.ssh/id_ed25519 clawdbot@192.168.123.10 \
  "find ~/.openclaw/agents/main/sessions ~/.openclaw/cron/runs -type f -name '*.jsonl'"

ssh -i ~/.ssh/id_ed25519 clawdbot@192.168.123.10 \
  "rg -n 'traceId|spanId|telegram|sendMessage|message_thread|format|•|human readable' \
    ~/.openclaw/agents/main/sessions ~/.openclaw/cron/runs"
```

Then build `detrix openclaw digest-traces` to extract:

- `trace_id`
- `span_id`
- Telegram topic/thread
- user input
- model output
- delivery attempt
- prompt/skill/model version if present
- readability verdict
- rewrite/block decision

**Warrant:** direct: The user confirmed `~/.openclaw/logs` is the OpenClaw session-log
surface and that `traceId` / `spanId` can follow a request path.

**Rationale:** Real trace evidence prevents the demo from looking canned. It also starts
the compounding asset: replay cases from production failures.

**Downsides:** The logs are not present in the current local `~/.openclaw` tree, so this
requires public-VM access or log export before the claim is honest.

**Confidence:** 88%

**Complexity:** Low-Medium

**Status:** Partially explored; VM access, session paths, and two real readability failure
sessions are confirmed.

### 3. Replay-Gated Formatter / Prompt / Skill Promotion

**Description:** Do not claim self-improving Qwen first. Show system self-improvement:
bad trace becomes a replay fixture; a formatter/prompt/skill candidate is proposed; replay
accepts or rejects it. A candidate can promote only if held-out readability failures do
not regress.

**Warrant:** reasoned: The critic scan correctly identified that self-improvement without
fine-tuning is credible only as reliability-boundary improvement, not model-weight
improvement.

**Rationale:** This gives a real improvement loop by the YC deadline:
failure -> gate -> replay -> better admitted output -> promotion packet. It avoids the
high-risk Qwen fine-tune path while preserving the product thesis.

**Downsides:** It may still be dismissed as deterministic postprocessing unless paired
with state-transition consequences and AgentXRD portability.

**Confidence:** 86%

**Complexity:** Medium

**Status:** Unexplored

### 4. Portable Admission Packet Contract

**Description:** Define one schema shared by OpenClaw, AgentXRD, and ParabolaHunter:

```text
TraceEnvelope
  -> EvidencePacket
  -> GateVerdict[]
  -> AdmissionDecision
  -> TrainingRoute
  -> ReplayStatus
  -> PromotionEligibility
```

For OpenClaw, the transition is `send this message`. For AgentXRD, it is `accept this
scientific result` or `export this row for training`. For ParabolaHunter, it is `promote
this alert/strategy/policy`.

**Warrant:** direct: Detrix already has reusable trajectory, gate, exporter, and
promotion primitives; AgentXRD already uses the admission/replay pattern.

**Rationale:** This prevents the OpenClaw MVP from becoming rigid. The gate logic is
domain-specific, but the harness contract is portable.

**Downsides:** Over-abstracting before the first OpenClaw gate works would slow the demo.
Keep the schema thin.

**Confidence:** 84%

**Complexity:** Medium

**Status:** Unexplored

### 5. OpenClaw + AgentXRD Two-Step Demo

**Description:** Demo sequence:

1. OpenClaw: “Can this Telegram message be sent?”
2. AgentXRD: “Can this PXRD result become accepted evidence or training data?”

Both emit the same Detrix admission packet shape.

**Warrant:** direct: Existing `docs/reliability-first-positioning-20260503.md` already
positions OpenClaw as the readable first proof and AgentXRD as the domain-specific moat
proof; the critic scan says OpenClaw alone is too low-stakes.

**Rationale:** OpenClaw is understandable in seconds. AgentXRD makes the company-level
stakes real and shows the same harness handles high-stakes technical outputs.

**Downsides:** It requires more demo choreography and at least one AgentXRD packet ready
alongside the OpenClaw packet.

**Confidence:** 81%

**Complexity:** Medium

**Status:** Unexplored

### 6. Borrow AI_ATL25 Capture, Not Its Claims

**Description:** Reuse ideas/code shapes from AI_ATL25 for local JSONL trace viewing and
offline trace-to-dataset conversion, especially the `--trace-json` path. Do not import
its placeholder training metrics or UI as product proof.

**Warrant:** direct: The AI_ATL25 scan found reliable trace capture, Langfuse conversion,
and offline dataset tooling, but also cautioned against placeholder training/status paths.

**Rationale:** This is the fastest way to get repeatable local trace fixtures without
inventing trace visualization or conversion from scratch.

**Downsides:** Its data model is oriented around tool-call fine-tuning, so the Detrix
adapter still needs admission labels and replay semantics.

**Confidence:** 78%

**Complexity:** Low-Medium

**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Qwen fine-tune immediately | Too risky for the guaranteed MVP. Current docs already warn that Qwen self-improvement requires held-out replay, sufficient governed positives, and a working model path. |
| 2 | Hermes migration first | Hermes is relevant, but migrating runtime before proving the send-boundary gate adds risk and can mask the simple OpenClaw failure. |
| 3 | pi-mono extension first | pi is a good future harness substrate, but the current failure is in OpenClaw Telegram delivery; switching to pi first is slower than gating the current boundary. |
| 4 | Prime Verifiers environment first | Prime is useful after Detrix packets exist. Starting with Prime turns a reliability problem into an RL-environment packaging problem. |
| 5 | LLM judge for readability | Prompt/judge behavior is exactly what failed. A judge may be advisory, but the MVP needs deterministic admission. |

## Recommended MVP

Build the MVP in this order:

1. **Digest real OpenClaw logs on the public VM.**
   If the logs are not locally available, copy a small sanitized JSONL bundle into
   `fixtures/openclaw/telegram-readability/`.

2. **Implement deterministic readability admission.**
   Gate result should include `decision`, `reason_codes`, `evidence`, `admitted_text`,
   `raw_text_hash`, and `training_route`.

3. **Create replay and promotion packets.**
   A prompt, formatter, skill, or model change promotes only if replay pass rate improves
   and no held-out case regresses into dense output.

4. **Export routed improvement data.**
   `PASS` rows can become SFT positives only when unchanged and human-readable. `REWRITE`
   rows produce chosen/rejected DPO pairs. `BLOCK` rows are eval-only or negative
   examples. Do not fine-tune by default.

5. **Show one AgentXRD packet with the same schema.**
   This proves the OpenClaw gate is a legible instance of a broader reliability harness.

## Runtime Decision

Use the existing OpenClaw send boundary for v0. The most reliable first patch is a
post-generation, pre-`sendMessage` formatter/gate near delivery, plus an offline replay
CLI over captured logs.

Use Hermes later if the deployment is migrating anyway. Hermes is attractive because it
has Telegram gateway, skills, memory, session search, and research trajectory generation,
but migrating before the first gate works is unnecessary risk.

Use pi-mono later as a portable agent-harness adapter and session source. It is not needed
for the first Telegram proof.

Use Prime Verifiers later as an export target when Detrix has stable admission packets,
replay cases, and enough trajectories. Do not use Prime/PRIME-RL to prove readability v0.

## Qwen / Fine-Tuning Decision

Fine-tuning is not needed for the minimum reliable output goal. The guaranteed feature is
deterministic admission plus rewrite/block/replay.

Qwen can appear only as a proposer, not the authority:

- propose a concise rewrite;
- propose a failure class;
- propose a training route;
- propose a next action.

Detrix gates decide whether the proposal is admissible. Claim Qwen improvement only after:

- at least 20-50 real OpenClaw traces are labeled;
- the replay split is frozen;
- a before/after held-out replay shows fewer unreadable outputs;
- no regression in false blocks or message usefulness;
- model/prompt/formatter versions are recorded.

## Minimum Demo Claim

The first demo should claim:

> I told the agent to write readable Telegram messages and it kept failing. Detrix turned
> that failure into an inline admission gate, replay suite, and promotion rule. The model
> can propose text, but only phone-readable text is allowed into Telegram.

The second sentence should connect the real company:

> The same harness decides whether AgentXRD can accept scientific evidence or export a
> trace for training.

## Sources

- Hermes Agent GitHub README: https://github.com/nousresearch/hermes-agent
- pi-mono GitHub README: https://github.com/badlogic/pi-mono
- Prime Verifiers GitHub README: https://github.com/PrimeIntellect-ai/verifiers
- PRIME-RL GitHub README: https://github.com/PrimeIntellect-ai/prime-rl
