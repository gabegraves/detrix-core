# Agent Instructions

## Design Doc (source of truth)

**Read before any strategic work:** `~/.gstack/projects/gabegraves-detrix-core/gabriel-main-design-20260331-022621.md`

Contains: positioning, competitive landscape, architecture (with Stripe/Anthropic patterns), existing asset map, testing plan, monetization model, agent-as-FDE scaling, hiring timeline, and 14-day sprint plan.

**Research references:**
- Autoresearch landscape + competitive intel: `docs/autoresearch-landscape-eval-20260423.md`
- Bitter Lesson of Agent Harnesses implications: `docs/bitter-lesson-harness-implications-20260423.md`

## Product Context

Make domain-specific agents reliable enough to deploy and cheap enough to scale. Post-hoc physics evaluation + domain scoring + overnight improvement from governance-scored traces. Agents improve from yesterday's failures without constraining today's action space.

**Core design principle (Bitter Lesson-aligned):** Gates evaluate outputs post-hoc — the agent has maximal action-space freedom, zero awareness of gates. The orchestrator runs evaluation checkpoints unconditionally after each phase. AgentXRD_v2 already implements this correctly: handlers have no gate awareness (see `pipeline.py:_post_score_governance()`).

**Phase 1 identity: VERTICAL-FIRST (materials science)**
- In Phase 1, sell "managed materials science pipeline improvement" — AgentXRD is the customer-facing product
- Detrix is the internal infrastructure brand, extracted later as the platform
- Prior investor rejection (Fledgling) was "too horizontal, too similar to OpenPipe" — vertical-first avoids that trap

**Positioning rules for all agents:**
- Never describe Detrix as "a pipeline framework" or "a DAG executor" — it is a governance + improvement runtime
- Never position against LangGraph — position as the layer above it (evaluates outputs from any framework via thin trajectory-capture shims)
- **Never pitch "trace → fine-tune → cheaper models" alone** — that's OpenPipe. Differentiation requires post-hoc domain physics evaluation + tiered scoring + autonomous improvement from governance-scored traces.
- **Never describe gates as "blocking" or "constraining" agent actions.** Gates evaluate outputs after the fact. The agent has full freedom; the orchestrator accepts or rejects results. This is the Bitter Lesson distinction: evaluation, not wrapping.
- Open-source projects (MetaClaw, TensorZero, autoresearch, MLAgentBench) are component sources under MIT/Apache-2.0, NOT competitors.
- AgentXRD (materials science) is the Phase 1 product. ~70% of the architecture already exists in AgentXRD_v2 and mission-control.
- **Training strategy:** SFT + LoRA first (v1), DPO second (v2), GRPO/RL only if needed (v3). Don't start with RL.
- **Build order:** Finish AgentXRD_v2 end-to-end → extract infra into detrix-core. Preserve AgentXRD_v2's post-hoc gate pattern during extraction — it's already correct.
- **Competitive landscape (2026-04-23):** 6+ projects attack parts of the improvement loop (GEPA, AIDE, ML-Agent, recursive-improve, ADAS, autoevolve). None combine all four differentiators: deterministic physics gates + tiered scoring + post-hoc enforcement + training signal extraction. GEPA (ICLR 2026) outperforms GRPO via gradient-free Pareto evolution — closest threat to MetaClaw skill evolver. Full analysis: `docs/autoresearch-landscape-eval-20260423.md`, `docs/competitive-moat-research-20260327.md`
- **Provider absorption risk is LOW** if positioned on domain physics. OpenAI RFT gets 70% of generic improvement loop but cannot validate materials physics. Generic horizontal infra gets acquired (OpenPipe, W&B, Galileo, Langfuse, Promptfoo all absorbed 2025-2026).
- **The training loop is commodity.** TensorZero, MetaClaw, OpenAI RFT all ship versions. The moat is domain-validated training SIGNAL from governance scoring, not the loop mechanics.
- **Hardware advantage:** Local GPUs (2x Blackwell + 3x 3090 + 512GB RAM) enable zero-marginal-cost improvement loops, on-prem demos for regulated customers, and pre-built domain benchmarks.

## AgentXRD_v2 Application

AgentXRD_v2 is the proving ground for Detrix — its gate architecture is already Bitter Lesson-aligned:

**What's already correct (preserve during extraction):**
- 6 gates implemented as post-hoc output evaluators in `pipeline.py`
- Handlers have zero awareness of gates — `_post_score_governance()` and `_post_refinement_governance()` run after handler completion
- `TerminalRoute` rejects outputs without blocking agent actions
- `GateRecord` captures every evaluation for trajectory scoring
- State machine (`INIT→PREPROCESS→METROLOGY_GUARD→SCORING→REFINEMENT→VERDICT`) sequences evaluation checkpoints, not action constraints

**What to add during detrix-core extraction:**
- Agent-editable gate thresholds: gate configs readable/proposable by the agent, validated against held-out test set (Phase 1, don't defer to Phase 6)
- GovernedTrajectory schema wrapping GateRecords + handler outputs as SFT/DPO training data
- MLAgentBench integration as secondary RLVR training ground (13 ML tasks with deterministic `get_score()`)
- MetaClaw SkillEvolver: gradient-free skill evolution scored by existing gates (reference: AutoResearchClaw's 5-layer integration, +18.3% robustness)

**What NOT to do:**
- Don't refactor gates into action-space constraints during extraction — the post-hoc pattern is correct
- Don't build heavy framework adapters — thin trajectory-capture shims (~50 lines each)
- Don't wrap agent tools — evaluate agent outputs

**When writing copy, docs, or landing page content:**
- One-liner: "Make domain-specific agents reliable enough to deploy and cheap enough to scale."
- Competitive line: "OpenPipe trains on traces. Detrix trains on traces that survived domain physics evaluation."
- Elevator: "We score your agent's output with domain physics — post-hoc, no wrapping, full agent freedom. Then we train on what survived. Agents improve from yesterday's failures without constraining today's action space."
- Hero framing: "Your agents work in demos. Detrix makes them work in production."
- Bitter Lesson framing: "Don't wrap the agent. Evaluate what it produces. Train on what survives."
- Quickstart: `detrix init → detrix observe → detrix score → detrix improve → detrix promote`
- Always include "Works with: LangGraph, LangChain, CrewAI, Python — no framework changes required"
- **Monetization:** Phase 1: vertical service ($2-5K/engagement) → Phase 2: Detrix Cloud ($500/mo) → Phase 2.5: hosted inference (30% of savings) → Phase 3: domain pack subscriptions

## Working Rules
- All work must be tracked with beads and git
- Run `exec-report` skill at the end of every beads-tracked execution session before final handoff

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work atomically
bd close <id>         # Complete work
bd dolt push          # Push beads data to remote
```

## Quality Gates
- `uv run ruff check .` and `uv run mypy src/detrix` before committing
- `uv run pytest` before pushing

## Git Rules
- Commit early and often
- One logical change per commit
- Conventional commits (feat/fix/docs/refactor)
- Include beads issue ID in commits when applicable: `git commit -m "feat: add trace collector (bd-abc)"`

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

<!-- BEGIN BEADS INTEGRATION profile:full hash:d4f96305 -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Dolt-powered version control with native sync
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - `uv run ruff check .`, `uv run mypy src/detrix`, `uv run pytest`
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Exec report** - Run `exec-report` skill at end of every beads-tracked session
8. **Hand off** - Provide context for next session using exec report as summary

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- NEVER skip `exec-report` at end of a beads execution session
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->
