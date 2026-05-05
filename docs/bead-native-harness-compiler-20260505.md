# Bead-Native Harness Compiler Direction — 2026-05-05

## Status

Strategic direction and repo-context audit for Detrix after the 2026-05-05 cross-project audit and open-source/paper comparison.

Tracked by bead: `detrix-core-mch`.

## Goal

Detrix's #1 goal is to extract recurring failure patterns from previous agent sessions and use them to self-improve the agent harness so future work across projects reaches goals faster, with fewer false claims, fewer repeated mistakes, and stronger evidence.

## Direction

Detrix should be a **bead-native harness compiler** for high-stakes agent work.

The product should not be framed as generic observability, generic deterministic gates, generic memory, or generic fine-tuning. It should convert raw agent sessions into atomic execution beads, run an adversarial builder/verifier loop around those beads, mine recurring failure patterns, propose harness mutations, and promote only the mutations that improve held-out bead suites without weakening domain gates.

```text
raw sessions
  -> beadized task ledger
  -> builder execution
  -> verifier falsification
  -> typed failure-pattern bank
  -> harness mutation proposal
  -> held-out replay / admission gates
  -> promote, reject, or quarantine
```

## Research implications

### Natural-Language Agent Harnesses

Paper: <https://arxiv.org/abs/2603.25723>

The relevant lesson is not "add more gates." The paper shows that agent performance depends heavily on the harness and that harness behavior should be externalized into editable, portable, ablatable artifacts. Its module ablations imply that more orchestration is not automatically better: verifier modules and multi-candidate search can hurt when their local success criteria diverge from the real evaluator, while self-evolution and artifact-addressable control can help.

Implication for Detrix: keep deterministic gates only where they encode real project acceptance criteria. Do not add generic blockers. Make the harness itself measurable, editable, and replay-promoted.

### Meta-Harness

Paper: <https://arxiv.org/abs/2603.28052>
Project page: <https://yoonholee.com/meta-harness/>

Meta-Harness treats the harness itself as the optimization target: what the system stores, retrieves, presents, checks, and routes. Its core finding for Detrix is that raw execution traces and scores are more useful than compressed summaries when searching for harness improvements.

Implication for Detrix: the durable asset is not a dashboard of traces. It is the promotion discipline that turns raw traces into evaluator-aligned harness changes.

## Competitive distinction

### Microsoft Agent Governance Toolkit

Repository: <https://github.com/microsoft/agent-governance-toolkit>

AGT is a runtime governance and policy-enforcement layer: action policies, identity, sandboxing, SRE controls, audit logs, and OWASP agentic-risk coverage. It answers whether an agent action is allowed.

Detrix should answer a different question: why did agents repeatedly fail to reach a project goal, what harness mutation would prevent that, and did the mutation improve held-out bead execution?

AGT-style controls are useful adapters for Detrix's policy/admission layer, not the whole product.

### Reflexio

Repository: <https://github.com/ReflexioAI/reflexio>

Reflexio is a self-improvement harness centered on user corrections, profiles, playbooks, expert responses, and retrieval. It is closer than AGT because it learns from interactions.

Detrix should be execution-outcome-centric rather than correction/playbook-centric: every lesson must tie back to bead acceptance, artifact evidence, evaluator distance, and project-specific promotion gates.

Reflexio-style playbook extraction can be a memory adapter, but Detrix's moat is evaluator-aligned trace-to-harness promotion.

### recursive-improve

Repository: <https://github.com/kayba-ai/recursive-improve>

recursive-improve is the closest open-source baseline. It captures LLM calls, analyzes traces for failure patterns, generates metrics/evals, proposes prompt/code fixes, benchmarks, and ratchets improvements.

Detrix must be narrower and stronger: multi-project, bead-native, domain-gated, and promotion-controlled. The unit of improvement is not "the agent got better"; it is "this harness mutation improved a held-out suite of atomic project beads without increasing unsafe transitions."

## Bead contract

Every improvement loop should start from a bead contract:

```yaml
bead_id: detrix-core-example
project: AgentXRD_v2 | ParabolaHunter | OpenClaw | detrix-core
objective: one atomic outcome
acceptance_evaluator: deterministic adapter plus allowed semantic checks
required_artifacts:
  - paths or trace ids proving the outcome
forbidden_claims:
  - claims that must not be made without evidence
domain_gates:
  - project-specific invariants
risk_class: low | medium | high
baseline_harness_id: current prompt/skill/config/tooling version
promotion_policy: held-out replay and no hard-gate regression
```

## Builder/verifier loop

### Builder

The builder owns one bead. It may plan and execute, but it must emit structured claims and an artifact manifest:

```json
{
  "bead_id": "...",
  "claims": [
    {"claim": "what changed", "evidence": ["path", "command", "trace_id"]}
  ],
  "blocked_claims": [],
  "next_actions": []
}
```

### Verifier

The verifier tries to falsify the builder's claims. It should use deterministic adapters first and LLM judgment only for evaluator-aligned semantic interpretation. It must report:

- verified claims,
- unverified claims,
- false or overstated claims,
- missing artifacts,
- likely harness failure pattern,
- recommended harness mutation.

### Failure miner

Repeated verifier failures become typed failure patterns, for example:

- planned-but-not-implemented,
- stale artifact used as current proof,
- support-only evidence promoted as benchmark-ready,
- fallback/priced-simulation claim treated as real-priced evidence,
- broad task not beadized before execution,
- deterministic gate substituted for evaluator-aligned replay,
- raw trace compressed before the useful failure signal was mined.

### Harness proposer

The proposer may mutate prompts, AGENTS.md rules, skill routing, bead templates, verifier checklists, trace-capture schemas, or domain adapters. It may not directly promote a change.

### Promotion judge

A candidate harness is promoted only if it improves a held-out bead suite and does not regress hard gates. Failed mutations should be stored as rejected transition records so future agents do not rediscover them.

## Project validation suites

### AgentXRD_v2

Hard gates:

- `wrong_accept_count == 0`
- `support_only_accept_violations == 0`
- support-only / eval-only evidence never becomes benchmark-ready promotion
- Qwen or any LLM proposes transitions; deterministic AgentXRD/Detrix gates admit or reject them

Representative beads:

- detect support-provenance blocker despite strong Pawley fit,
- route row to REQUEST_MORE_DATA instead of forced ACCEPT,
- generate a governed next action with required evidence,
- reject unsafe threshold or training-route mutation.

### ParabolaHunter

Hard gates:

- headline claims require real-priced evidence,
- fallback/Black-Scholes/paper evidence cannot substitute for real-priced replay,
- stale trace/config drift cannot be promoted,
- blocked promotion should emit typed next actions rather than false success.

Representative beads:

- classify strict real-priced zero-trade case without erasing diagnostic signal,
- split pricing quality from signal-source coverage,
- block promotion while preserving validated evidence,
- generate replay requirements for the next run.

### OpenClaw / Telegram

Hard gates:

- send-boundary readability must be evaluated against the real message envelope,
- synthetic target/payload evidence is not enough when live gateway shape differs,
- formatter/prompt changes must pass replay before promotion.

## Detrix-core repo-context audit

### What helps

- `AGENTS.md` already contains the right high-level invariants: transition admission, validated decision boundaries, post-hoc evaluation, replay-gated promotion, and no generic fine-tuning claims.
- `STRATEGY.md` already frames Detrix as a reliability harness around state transitions rather than a generic pipeline engine.
- Existing source has useful seed components: `src/detrix/core/admission.py`, `src/detrix/core/trajectory.py`, `src/detrix/runtime/trajectory_store.py`, `src/detrix/openclaw/*`, and `src/detrix/agentxrd/*`.
- Existing tests prove some admission, replay, OpenClaw, AgentXRD, promotion-packet, and trajectory behavior.
- Beads are already installed and active, which matches the atomic-task execution model.

### What pollutes or confuses context

- `README.md` had been pitching a generic pipeline/DAG/reproducibility product, and its lower quickstart/runtime sections still preserve that older seed architecture. That history conflicts with `AGENTS.md` rules that say never describe Detrix as a pipeline framework or DAG executor unless clearly labeled as legacy infrastructure.
- `AGENTS.md` is very long and includes stale YC-deadline instructions plus many older product assumptions. It is useful as historical guardrails, but it can dominate agent context and obscure the May 5 direction.
- The repo contains large transcript/export docs such as `docs/session-main-io-appendix-2026-05-02-03.md` and `docs/session-export-agentxrd-182bad6c.md`; these are valuable evidence archives but extremely noisy as default context.
- The checkout includes nested or generated surfaces (`claude-code-clone/`, `outputs/`, `.omx/`, `.omc/`, caches, `.pi/`, `unsloth_compiled_cache/`) that should not be default context for a clean product-harness implementation.
- Existing source mixes older workflow-engine abstractions, OpenClaw MVP proof, AgentXRD demos, training/export experiments, and YC audit artifacts. That history is useful evidence, but it makes the clean harness compiler boundary harder to see.
- The worktree is already dirty with unrelated edits and untracked documents, so broad refactors here risk mixing strategy, local evidence, and implementation history.

## Recommendation: create a clean repo, keep detrix-core as evidence/archive

Create a new clean repo for the bead-native harness compiler **if the next step is implementation of the core product/harness**, not just strategy docs.

Recommended split:

- New clean repo: `detrix-harness` or `bead-harness-compiler`
  - owns canonical bead schema,
  - raw trace ingestion contract,
  - builder/verifier protocol,
  - failure-pattern bank,
  - harness mutation proposal records,
  - held-out replay/promotion engine,
  - adapters for Codex/Claude/OMX/beads.
- Keep `detrix-core` as:
  - evidence archive,
  - historical strategy source,
  - domain adapter incubator,
  - OpenClaw/AgentXRD/ParabolaHunter validation-pack reference,
  - source of prior tests and fixtures to migrate selectively.

Do **not** abandon `detrix-core`; it contains useful proof and domain-specific guardrails. But do avoid making it the clean core repo for the new harness direction unless it is first aggressively slimmed or context-scoped.

## If staying inside detrix-core temporarily

Use a narrow subpackage and avoid repo-wide context:

```text
src/detrix/harness/
  bead.py
  claim_ledger.py
  verifier.py
  failure_patterns.py
  mutations.py
  promotion.py

tests/test_harness_*.py
```

Default context should include only:

- `docs/bead-native-harness-compiler-20260505.md`
- `STRATEGY.md`
- `src/detrix/core/admission.py`
- `src/detrix/core/trajectory.py`
- selected `src/detrix/agentxrd/*` or `src/detrix/openclaw/*` files for validation
- specific bead fixtures

Avoid loading large session appendices or broad docs unless investigating provenance.

## Immediate next implementation plan

1. Create clean repo scaffold or isolated `src/detrix/harness/` package.
2. Define `BeadContract`, `ClaimLedger`, `VerificationReport`, `FailurePattern`, `HarnessMutation`, and `PromotionDecision` schemas.
3. Add a tiny replay suite with one AgentXRD-style bead and one ParabolaHunter-style bead.
4. Implement deterministic verifier adapters for evidence path existence, required claim coverage, forbidden claim detection, and hard-gate regression.
5. Add a mutation record format but keep mutation application manual until replay proves safety.
6. Add CLI:
   - `detrix bead verify <claim-ledger> --contract <bead>`
   - `detrix harness propose --failures <patterns>`
   - `detrix harness promote --candidate <mutation> --suite <heldout>`
7. Only then wire Codex/Claude/OMX session ingestion.

