# Handoff: Automated Skillify Loop for AgentXRD v2

**Date:** 2026-04-24
**Epic:** detrix-core-j0v
**Branch:** main (create feature branch `feat/skillify-loop` before starting)
**Target runtime:** Qwen 3.6 via vLLM on pi agent harness
**Build tools:** uv (never pip), pytest, ruff, mypy

---

## Why This Exists

Garry Tan's "skillify" pattern (2026-04-22 post) describes turning every agent failure into a permanent structural fix: a skill with deterministic code and tests that prevents the failure from recurring. His loop is manual — human says "skillify" and a 10-step pipeline runs. Detrix should automate this: governance gates detect the failure pattern, MetaClaw generates the skill, and GRPO trains Qwen 3.6 to follow the skill.

The core insight: "the latent space builds the deterministic tool, then the deterministic tool constrains the latent space." This IS Detrix's deterministic-first hierarchy applied to self-repair.

## What Detrix Already Has (Read These First)

| File | What It Contains |
|------|-----------------|
| `src/detrix/core/governance.py` | `GovernanceGate` ABC, `VerdictContract`, `Decision` enum, `DomainEvaluator` ABC, `GateContext` |
| `src/detrix/core/trajectory.py` | `GovernedTrajectory` schema with `to_sft_row()`, `to_grpo_row()`, `verdicts`, `governance_score` |
| `src/detrix/adapters/axv2.py` | AXV2 adapter: `gate_record_to_verdict()`, `run_artifact_to_trajectories()` — shows how to convert external gate records to Detrix verdicts |
| `src/detrix/runtime/trajectory_store.py` | `TrajectoryStore` — append-only SQLite store with `query(domain, min_score, rejection_type)` |
| `src/detrix/improvement/exporter.py` | `TrainingExporter` — exports SFT/DPO/GRPO JSONL and HF Datasets from trajectory store |
| `src/detrix/improvement/promoter.py` | `ModelPromoter` — challenger vs incumbent comparison with threshold-based promotion |
| `src/detrix/improvement/trace_collector.py` | `TraceCollector` ABC — stub for extracting training examples from RunArtifact |
| `src/detrix/scoring/types.py` | Scoring types: `ApproachGrade`, `HaikuScorecard`, `SessionDigest` |
| `src/detrix/core/models.py` | `RunRecord`, `StepResult`, `StepStatus` |
| `docs/governance-spec.md` | Full governance spec with ABCs, verdict contracts, build order |
| `CLAUDE.md` | Architecture decisions, deterministic-first hierarchy, build sequence, conventions |

## Beads Task Graph

```
detrix-core-7oy: Skill Registry schema + SQLite store     [READY — start here]
    ├── detrix-core-1n5: Wrong-Side Detection Gate          [blocked by 7oy]
    │       ├── detrix-core-3kz: Skill Generator            [blocked by 7oy, 1n5]
    │       └── detrix-core-czm: Skill-aware scoring + GRPO [blocked by 7oy, 1n5]
    ├── detrix-core-hv7: Skill Routing Validator            [blocked by 7oy]
    └── detrix-core-twj: Version-aware trace flush          [blocked by 7oy]

detrix-core-2qt: Skillify Pipeline Orchestrator             [blocked by 1n5, 3kz, hv7, czm]
```

**Wave execution order:**
- Wave 1: `detrix-core-7oy` (Skill Registry)
- Wave 2 (parallel): `detrix-core-1n5` (Wrong-Side Gate), `detrix-core-hv7` (Routing Validator), `detrix-core-twj` (Version Flush)
- Wave 3 (parallel): `detrix-core-3kz` (Skill Generator), `detrix-core-czm` (Skill-Aware Scoring)
- Wave 4: `detrix-core-2qt` (Skillify Orchestrator)

## Task Specifications

### Wave 1: detrix-core-7oy — Skill Registry Schema + SQLite Store

**Create:** `src/detrix/core/skill_registry.py`

```python
# Pydantic models needed:

class DeterministicTool(BaseModel):
    tool_id: str                    # e.g. "rietveld_rwp_calc"
    script_path: str                # relative path to deterministic script
    input_schema: dict[str, Any]    # JSON schema for expected inputs
    output_schema: dict[str, Any]   # JSON schema for expected outputs
    domain: str                     # e.g. "xrd", "trading", "calendar"
    version: str

class SkillDefinition(BaseModel):
    skill_id: str                   # e.g. "xrd-rwp-validation"
    name: str
    description: str                # when this skill should be used
    triggers: list[str]             # intent patterns that should route here
    deterministic_tool_ids: list[str]  # tools this skill requires
    test_intents: list[str]         # intents for routing validation
    domain: str
    version: str
    created_from_trajectory_id: str | None = None  # trace that spawned this skill
    created_at: datetime
    status: Literal["candidate", "validated", "active", "retired"] = "candidate"

class SkillRouting(BaseModel):
    intent_pattern: str
    skill_id: str
    confidence_threshold: float = 0.8
```

**Create:** `src/detrix/runtime/skill_store.py`

Follow the exact same pattern as `TrajectoryStore`:
- SQLite-backed, append-only for skills, upsert for routing
- Tables: `skills`, `deterministic_tools`, `skill_routings`
- Methods: `register_tool()`, `register_skill()`, `add_routing()`, `get_skill()`, `list_skills(domain, status)`, `get_tools_for_domain()`, `find_routing(intent)`
- Index on domain, status, skill_id

**Tests:** `tests/test_skill_registry.py`, `tests/test_skill_store.py`

**Acceptance:** `uv run pytest tests/test_skill_registry.py tests/test_skill_store.py -v` passes. `uv run mypy src/detrix/core/skill_registry.py src/detrix/runtime/skill_store.py` clean.

---

### Wave 2a: detrix-core-1n5 — Wrong-Side Detection Gate

**Create:** `src/detrix/core/wrong_side_gate.py`

Subclass `GovernanceGate`. The gate:

1. Takes `inputs` dict with keys:
   - `tool_calls: list[dict]` — agent's tool call log from the run
   - `agent_output: str` — the agent's final output
   - `domain: str` — to look up available deterministic tools

2. Loads available `DeterministicTool` entries for the domain from `SkillStore`

3. For each registered tool, checks if the agent's output contains data that the tool would produce (e.g., Rwp values, timezone calculations, file search results) WITHOUT the agent having called that tool

4. Detection heuristics (deterministic, no LLM):
   - Check tool_calls list for presence of registered tool_ids
   - If a registered tool exists for the domain AND was NOT called AND the agent produced output in the tool's output_schema domain → `Decision.CAUTION` with `reason_code='wrong_side_latent'`
   - If tool was called → `Decision.ACCEPT`
   - If no relevant tools registered → `Decision.ACCEPT` (nothing to check)

5. `VerdictContract` evidence includes: `available_tools`, `tools_called`, `tools_skipped`, `output_domain_match`

**Key design constraint:** This is Tier 3 (behavioral verification). Zero LLM cost. Pure structural check. The gate evaluates WHETHER the agent used the right tool, not whether the answer is correct.

**Tests:** Test with fixture data:
- Agent called the tool → ACCEPT
- Agent skipped available tool and produced output in same domain → CAUTION
- No tools registered for domain → ACCEPT
- Agent used some tools but skipped others → partial CAUTION

---

### Wave 2b: detrix-core-hv7 — Skill Routing Validator

**Create:** `src/detrix/improvement/skill_validator.py`

Two components:

**RoutingValidator:**
- Takes a `SkillDefinition` and a `SkillStore`
- Runs each `test_intent` from the skill through `skill_store.find_routing(intent)`
- Checks: does the routing return the correct skill_id?
- Returns: `ValidationResult` with `passed_intents`, `failed_intents`, `false_positives` (routed to wrong skill)

**ReachabilityAuditor:**
- Scans all skills in store with `status='active'`
- For each skill, checks: does at least one routing entry point to it?
- For each routing, checks: does the target skill exist and is it active?
- Reports: `orphan_skills` (no route), `dead_routes` (target missing), `duplicate_routes` (overlapping patterns)

**DRYAuditor:**
- Checks for skills with overlapping `deterministic_tool_ids` in same domain
- Flags skills that could be consolidated

**Tests:** Fixture-based. Register skills, add routings, verify validator catches missing/wrong/duplicate routes.

---

### Wave 2c: detrix-core-twj — Version-Aware Trace Buffer Flush

**Modify:** `src/detrix/runtime/trajectory_store.py`
**Create:** `src/detrix/runtime/version_tracker.py`

`VersionTracker`:
- Tracks hash of all active `evaluator_version` + `gate_version` values
- On version change detection: marks all trajectories in current epoch as `contaminated`
- Starts new epoch (integer counter stored in SQLite)
- `TrajectoryStore.query()` gets optional `epoch` param to only return current-epoch trajectories
- `TrainingExporter` should default to current epoch only

Add `epoch` and `contaminated` columns to `governed_trajectories` table (migration-safe: default epoch=0, contaminated=false for existing rows).

**Tests:** Insert trajectories, change version, verify old trajectories excluded from queries.

---

### Wave 3a: detrix-core-3kz — Skill Generator from Failure Traces

**Create:** `src/detrix/improvement/skill_generator.py`

`SkillGenerator`:
- Input: `GovernedTrajectory` where wrong-side gate fired (verdict has `reason_code='wrong_side_latent'`)
- Extracts from verdict evidence: `tools_skipped`, `output_domain_match`
- For each skipped tool: generates a candidate `SkillDefinition`:
  - `name`: derived from tool_id + domain
  - `triggers`: extracted from the trajectory's prompt (what the agent was asked to do)
  - `deterministic_tool_ids`: the skipped tool(s)
  - `test_intents`: 5 synthetic intents generated from the prompt pattern
  - `status`: "candidate"
  - `created_from_trajectory_id`: links back to the failure trace
- Writes candidate to `SkillStore`

**This is the MetaClaw gradient-free path.** No GPU, no training. Just structural generation of skills from failure patterns. The gradient-based path (GRPO) trains the model to follow these skills over time.

**Tests:** Create a mock trajectory with wrong-side verdict, run generator, verify skill is written to store with correct fields.

---

### Wave 3b: detrix-core-czm — Skill-Aware Trace Scoring + GRPO Reward

**Modify:** `src/detrix/core/trajectory.py`

Add to `GovernedTrajectory`:
```python
used_correct_substrate: bool = True  # default True for backward compat
substrate_penalty: float = 0.0       # 0.0 = no penalty, 1.0 = full penalty
```

Update `to_grpo_row()`:
```python
def to_grpo_row(self) -> dict[str, Any]:
    substrate_multiplier = 1.0 - self.substrate_penalty
    return {
        "prompt": self.prompt,
        "completion": self.completion,
        "governance_score": self.governance_score * substrate_multiplier,
        "gate_verdicts": [v["decision"] for v in self.verdicts],
        "used_correct_substrate": self.used_correct_substrate,
    }
```

**Modify:** `src/detrix/improvement/exporter.py`

Add `export_grpo_skill_aware()` method that:
- Queries trajectories with wrong-side verdicts
- Sets `substrate_penalty` based on how many available tools were skipped
- Positive traces (used skill correctly) get governance_score * 1.0
- Negative traces (ignored skill) get governance_score * (1.0 - penalty)
- This creates the reward signal that trains Qwen 3.6 to be *disciplined*, not just accurate

**Tests:** Verify GRPO rows have correct substrate-adjusted scores. Verify backward compat (existing trajectories without wrong-side data export normally).

---

### Wave 4: detrix-core-2qt — Skillify Pipeline Orchestrator

**Create:** `src/detrix/improvement/skillify.py`

`SkillifyPipeline`:
- Orchestrates the full 10-step promotion adapted for Detrix:

```
Step 1:  Detect — WrongSideGate fires on a trajectory
Step 2:  Generate — SkillGenerator creates candidate SkillDefinition
Step 3:  Unit test — Run deterministic tool's script against fixture data
Step 4:  Integration test — Run tool against real domain data (if available)
Step 5:  LLM eval — (deferred to Phase 5 gate factory, stub for now)
Step 6:  Route — Add SkillRouting entries to store
Step 7:  Validate routing — RoutingValidator checks test_intents
Step 8:  Audit — ReachabilityAuditor + DRYAuditor on full store
Step 9:  Smoke test — (stub: would run full agent loop, needs pi integration)
Step 10: Activate — Set skill status from "candidate" to "active"
```

- Steps 5 and 9 are stubs (marked as requiring pi integration)
- Steps 1-4, 6-8, 10 are fully deterministic
- Pipeline returns `SkillifyResult` with per-step pass/fail and the final skill status
- If any step fails, skill stays "candidate" and result includes failure reason

**Config:** `SkillifyConfig` Pydantic model with:
- `auto_activate: bool = False` — require manual promotion by default
- `min_routing_pass_rate: float = 0.8` — 80% of test_intents must route correctly
- `max_duplicate_overlap: float = 0.5` — DRY threshold

**Tests:** End-to-end: create trajectory → run full pipeline → verify skill is in store with correct status. Test failure cases: routing validation fails → skill stays candidate.

---

## Conventions (MUST follow)

- `uv` for all package management. Never pip.
- Pydantic v2 for all data models.
- pytest for tests — integration tests, no mocking internal modules.
- ruff for linting (line-length=100).
- Click for any CLI additions.
- Commit at every logical milestone with conventional commits: `feat:`, `fix:`, `refactor:`.
- Include beads issue ID: `feat: add skill registry schema (detrix-core-7oy)`.
- Run `uv run ruff check .` and `uv run mypy src/detrix` before committing.
- Run `uv run pytest` before pushing.

## Architecture Constraints

1. **Gates evaluate outputs, never constrain actions.** The WrongSideGate scores post-hoc. It does NOT prevent the agent from doing latent-space work. It flags it for skill generation.

2. **Deterministic-first.** If it can be checked without an LLM, check it without an LLM. Every gate and validator in this epic is deterministic (zero LLM cost) except Step 5 (LLM eval, deferred).

3. **Support-query versioning is non-negotiable.** Flush trace buffer on ANY gate/evaluator version change. Reward contamination is silent and deadly.

4. **Built on pi.** Pi provides the agent loop. Detrix provides governance. The skillify pipeline generates skills that feed BACK into the pi agent's skill set. But pi integration (Steps 5, 9) is deferred — build the Detrix-side infrastructure first.

5. **Agent-editable governance.** Skills and routing are stored in SQLite config the agent can query. Don't hardcode thresholds.

## How to Start

```bash
cd ~/Desktop/detrix-core
git checkout -b feat/skillify-loop
bd update detrix-core-7oy --claim
bd ready  # confirms 7oy is ready
# implement skill registry, commit, close:
bd close detrix-core-7oy --reason="Skill Registry schema + SQLite store implemented"
bd ready  # should unblock 1n5, hv7, twj for Wave 2
```

## Verification

After all tasks complete:
```bash
uv run pytest -v                    # all tests pass
uv run ruff check .                 # clean
uv run mypy src/detrix              # clean
bd stats                            # all 7 tasks + epic closed
```

The ultimate smoke test (post-pi-integration): feed an AXV2 trajectory where the agent computed Rwp without calling the Rietveld script → wrong-side gate fires → skill generator creates "use-rietveld-for-rwp" skill → routing validator confirms → GRPO export includes substrate-penalized score → Qwen 3.6 trains overnight → next run, agent calls the script.
