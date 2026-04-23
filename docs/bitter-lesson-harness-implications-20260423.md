# Bitter Lesson of Agent Harnesses — Implications for Detrix

Source: Browser Use blog (browser-harness repo, ~600 lines total).
Core claim: Don't wrap the LLM. Don't wrap its tools. Give maximal action space + SKILL.md + thin helpers. Agent writes what's missing.

## The Argument

1. Every click(), type(), scroll() helper is an abstraction the RL'd model fights around
2. LLMs already know CDP — they were trained on millions of tokens of it
3. Give raw access, agent self-heals (writes missing functions, handles Chrome crashes)
4. 4 files: run.py (13 lines), helpers.py (192 lines), daemon.py (220 lines), SKILL.md
5. "The complexities you're hiding aren't something to hide. They're something to let the model see."

## Where It Validates Detrix

### Observer-first is correct
The Bitter Lesson says don't constrain actions — evaluate outputs. Detrix's observer pattern does exactly this. We're not wrapping the agent's tools; we're scoring what comes out. The observer sits alongside the pipeline, not inside it.

### MetaClaw skill evolver is validated
Their "self-heal loop" — agent writes missing helpers.py functions mid-task — is MetaClaw's SkillEvolver discovered accidentally. "We didn't tell it to do this." Detrix builds this deliberately with governance scoring: agent evolves skills, physics gates validate the evolution. Their accidental discovery confirms the mechanism works.

### Thin adapters are right
600-line harness vs. heavy framework wrappers. Phase 5 framework adapters should be as thin as possible. Don't rebuild LangGraph internals — observe its outputs. The adapter should be a shim that captures trajectory data, not a wrapper that constrains agent behavior.

## Where It Challenges Detrix

### Stripe Blueprints enforcement — the core tension
"Agent CANNOT skip gates" = structural constraint on action space. The Bitter Lesson says that's what kills performance under RL training.

**Critical distinction:**
- Gate on **process** (must call gate X before step Y) = wrapping = bad
- Gate on **results** (output must pass physics check) = evaluation = good

If Detrix enforces "you must call the Rietveld gate before proceeding," that's a process constraint the RL'd model has to route around. If Detrix runs Rietveld evaluation on whatever the agent produced and rejects bad output, that's evaluation — the agent never sees the constraint in its action space.

### Complexity budget
Detrix is growing toward hundreds of files. Browser-harness is 4 files. Every line of governance code is potential overhead. The question: is a physics gate more like daemon.py (necessary infrastructure the agent shouldn't have to think about) or like click() (unnecessary abstraction that constrains the agent)?

Answer: Physics gates are like daemon.py — they're infrastructure. The agent shouldn't have to re-derive Rietveld refinement convergence criteria. But the enforcement mechanism (how gates are wired into the pipeline) should be minimal.

### Agent should edit its own governance
Their best insight: the agent fixed its own helpers when they were wrong. If Detrix's gates are miscalibrated (bad threshold, false positive), the agent should propose gate edits. This is Meta-Harness (Phase 6) but they argue it should be default behavior, not a future phase.

Implication: Make governance configs editable by the agent from day one. The agent proposes a threshold change → human approves or a meta-gate validates → config updates. Don't wait for Phase 6.

## Design Changes for Detrix

### 1. Gates evaluate outputs, not constrain actions

```
# WRONG — process enforcement (wrapping)
orchestrator.require_gate("rietveld_convergence")
agent.run_step()  # agent's action space includes "must satisfy gate"

# RIGHT — output evaluation (observing)
result = agent.run_freely()  # maximal action space
score = rietveld_gate.evaluate(result)
if score < threshold:
    trajectory.mark_rejected(result, reason=score)
    # agent gets another attempt with the rejection signal
```

### 2. Stripe Blueprints = evaluation checkpoints, not action restrictions

The "blueprint" is a state machine of evaluation checkpoints the orchestrator runs unconditionally AFTER each phase. The agent has full freedom between checkpoints. The agent never sees the gate in its action space — it just sees "your output was rejected, try again" or "your output was accepted, proceeding."

This preserves:
- Deterministic physics authority (gates still block bad outputs)
- Structural enforcement (orchestrator runs gates unconditionally)
- Maximal agent action space (agent doesn't know about gates)

### 3. Governance config is agent-editable (move from Phase 6 to Phase 1)

Don't wait for Meta-Harness to make governance editable. From day one:
- Gate thresholds live in a config file the agent can read
- Agent can propose threshold changes via a structured edit
- Changes require either human approval or validation against a held-out test set
- This IS the Meta-Harness, just without the LLM proposer — the agent itself is the proposer

### 4. Adapter layer = trajectory capture shim, nothing more

Phase 5 adapters should be ~50 lines each:
- Hook into framework's output/callback mechanism
- Capture (input, output, metadata) as GovernedTrajectory
- Pass to evaluation pipeline
- Return accept/reject signal

No tool wrapping. No action space modification. No framework internalization.

## Implications for AgentXRD_v2

AgentXRD_v2's 6 governance gates are currently wired as pipeline stages (process enforcement). Under the Bitter Lesson framing, they should be refactored to:
1. Agent runs the full XRD analysis with maximal freedom
2. Gates evaluate the output at each natural checkpoint (post-refinement, post-phase-ID, etc.)
3. Rejection feeds back as a signal, not a blocked action

This is a meaningful refactor but aligns with observer-first principles we already claim to follow.

## The One-Line Summary

The Bitter Lesson says "delete your wrappers." Detrix's gates aren't wrappers — they're evaluators. But the enforcement mechanism that wires gates into the pipeline IS a wrapper if it constrains the agent's action space. Fix: gates score outputs after the fact, orchestrator decides accept/reject, agent never sees the gate in its action space.
