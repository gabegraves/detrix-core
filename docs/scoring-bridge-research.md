# Scoring Bridge Research: mission-control Mechanical Grading + LLM-as-Judge Architecture

**Date:** 2026-03-27  
**Status:** Research Complete (no implementation code)  
**Scope:** Understanding two-tier scoring system (mechanical deterministic + LLM semantic) for Python port to detrix-core  

---

## Executive Summary

The mission-control codebase implements a **two-tier scoring architecture** for evaluating AI coding sessions:

1. **Mechanical Grading (Deterministic)**: Per-step rule engine analyzing tool calls, file edits, test results, and error states. Outputs `ApproachGrade` symbols: `!!` (major positive), `!` (positive), `=` (neutral), `?` (negative), `??` (major negative).

2. **LLM-as-Judge (Semantic)**: Claude Haiku receives a compressed "digest" of mechanical grades + session metadata, then produces a composite score (0-100), summary bullets (what went right/wrong), and overrides where Haiku disagrees with mechanical grades.

The architecture is stateful, deterministic, and composable. Session traces flow through mechanical grading → digest compression → Haiku invocation → scorecard parsing → database persistence.

---

## Part 1: Mechanical Grading Engine

### File: `lib/daily-audit/mechanical-grader.ts` (125 lines)

#### Inputs: `ParsedPromptEvent[]`

Each prompt in a session provides:

```typescript
interface ParsedPromptEvent {
  promptNum: number;              // Sequentially numbered 1..N
  userPrompt: string | null;      // User's message (null for boundary prompts)
  toolCalls: ToolCallSummary[];   // Array of tool invocations
  filesEdited: string[];          // List of file paths modified
  testsRan: number;               // Total test count executed
  testsPassed: number;            // Passing test count
  testsFailed: number;            // Failing test count
  errorsEncountered: number;      // Non-test runtime errors
  sessionId: string;              // Unique session identifier
  isSessionBoundary: boolean;     // True if first prompt after context overflow/compaction
  isCompactionBoundary: boolean;  // True if boundary due to compaction
  boundaryReason: string;         // "context-overflow" or "compaction"
}

interface ToolCallSummary {
  name: string;                   // Tool name (e.g., "read_file", "execute_command")
  filePath: string | null;        // File being operated on (null for non-file tools)
  adds: number | null;            // Lines added (null if not a file edit)
  removes: number | null;         // Lines removed (null if not a file edit)
  exitCode: number | null;        // Exit code (null for non-command tools)
  isTestCommand: boolean;         // True if command is a test runner
}
```

#### Outputs: `MechanicalGrade[]`

One grade per input prompt:

```typescript
interface MechanicalGrade {
  promptNum: number;              // Matches input promptNum
  grade: ApproachGrade;           // "!!", "!", "=", "?", or "??"
  reason: string;                 // Human-readable explanation
  filesEdited: string[];          // Copied from input
  testsRan: number;               // Copied from input
  testsPassed: number;            // Copied from input
  errorsEncountered: number;      // Copied from input
}

type ApproachGrade = "!!" | "!" | "=" | "?" | "??";
```

#### Grading Rules (Decision Tree)

The engine applies 6-rule decision tree **in order**, returning the first match:

**Rule 1: Revert Detection (`hasRevert`) → `??` (Major Negative)**
- If any edited file shows evidence of reverting a previous change
- Detection algorithm: for each edited file, check if current `removes >= 0.7 * lastEdit.adds`
- Example: previous edit added 100 lines; current edit removes ≥70 lines → revert detected
- Reason: `"Reverted changes to {fileName}"`

**Rule 2: Consecutive Failures (`consecutiveFailures >= 2`) → `??` (Major Negative)**
- If ≥2 consecutive prompts had errors or test failures on the same file
- Counter resets when: (a) no errors/failures in current prompt, OR (b) error/failure on a different file
- Reason: `"{N} consecutive failures on {fileName}"`

**Rule 3: Errors or Test Failures → `?` (Negative)**
- If `hasErrors || testsFailed > 0` (and Rules 1-2 don't match)
- Reason: `"Test failure ({testsFailed} failed)"` or `"Error encountered ({errorsEncountered} errors)"`

**Rule 4: File Edits + Test Pass → `!!` (Major Positive)**
- If `filesEdited.length > 0 && testsPassed > 0`
- Reason: `"Edited {fileCount} file(s) with {testCount} passing test(s)"`

**Rule 5: File Edits Only → `!` (Positive)**
- If `filesEdited.length > 0` (and Rule 4 doesn't match)
- Reason: `"Edited {fileCount} file(s): {firstTwo}"`

**Rule 6: No Edits (Default) → `=` (Neutral)**
- If none of the above
- Reason: `"Exploration ({toolCount} tool calls, no file changes)"` or `"No tool calls"`

#### Stateful Tracking

The engine maintains two pieces of state across the prompt sequence:

1. **File Edit History Map**: `Map<filePath, FileEditHistory[]>`
   ```typescript
   interface FileEditHistory {
     promptNum: number;   // When this edit occurred
     adds: number;        // Lines added in this edit
     removes: number;     // Lines removed in this edit
   }
   ```
   - Updated for each prompt: all edited files get new history entries
   - Used in Rule 1: check if current removes exceed 70% of last edit's adds

2. **Consecutive Failure Counter**: `{ count, lastFailedFile }`
   - Incremented when `hasErrors || testsFailed > 0`
   - Resets to 1 when error occurs on a **different** file
   - Resets to 0 when no errors/failures in current prompt

#### Example Execution Flow

```
Prompt #1: edit file.ts, tests pass (3 passed)
  → Output: "!!" (Rule 4: edits + tests)
  → History: { "file.ts": [{ promptNum: 1, adds: 50, removes: 0 }] }
  → Failures: count=0

Prompt #2: edit file.ts again, 1 test fails
  → Output: "?" (Rule 3: test failure)
  → History: { "file.ts": [{ promptNum: 1, adds: 50, removes: 0 }, { promptNum: 2, adds: 10, removes: 5 }] }
  → Failures: count=1, lastFailedFile="file.ts"

Prompt #3: edit file.ts again, removes 40 lines (>= 0.7 * 50)
  → Rule 1 triggered: isRevert = true
  → Output: "??" (Rule 1: revert detected)
  → Failures: count=2
```

---

## Part 2: Session Digest Building

### File: `lib/daily-audit/haiku-grader.ts` (154 lines)

#### Function: `buildDigest(chain, prompts, grades) → string`

Compresses a full session into a single text block for Haiku ingestion. Output format:

```
Session Chain: "chain-uuid"
Project: {project} | Branch: {branch}
Source: {source} | Sessions: {sessionCount} | Duration: {totalMinutes}m
First prompt: "{userPrompt}"

#1 [user] {userPrompt}
   [tools] name:filePath(+adds-removes) name:filePath(+adds-removes) ...
   [delta] files:N edits:N tests:M/P pass errors:E
   [mech] !!

── context overflow (session 2/3) ──

#2 [user] {userPrompt}
   [tools] read_file:./src/component.ts execute_command:npm test(+0-0) → exit:1 (FAIL)
   [delta] files:1 edits:1 tests:5/3pass errors:0
   [mech] ?
```

**Key patterns:**
- Session boundaries marked with `── reason (session N/total) ──`
- Each prompt numbered `#N` with user prompt text (or "(no prompt)" if null)
- Tool calls formatted as `name:filePath(+adds-removes)` plus exit code and test status if applicable
- Delta line: file count, edit count, test results as `tests:ran/passed pass`, error count
- Mechanical grade on final line
- Lines joined with `\n`

**Usage:** Digest is fed to Haiku as the "user prompt" portion of the request.

---

## Part 3: LLM-as-Judge (Haiku) Integration

### File: `lib/daily-audit/haiku-grader.ts` (154 lines)

#### System Prompt (Embedded)

Haiku receives a system prompt instructing it to:

1. **Confirm or override** each mechanical grade per these symbols:
   - `!!` = Major positive (key feature landed, critical bug fixed with test)
   - `!` = Positive (progress made, files modified correctly)
   - `=` = Neutral (exploration, no meaningful change)
   - `?` = Negative (error introduced, wrong approach taken)
   - `??` = Major negative (revert needed, significant wasted effort, thrashing)

2. **Produce a JSON scorecard** with:
   - `score`: 0-100 overall session quality
   - `wentRight`: up to 5 bullets of what went well (specific, not generic)
   - `wentWrong`: up to 5 bullets of what went poorly (specific, not generic)
   - `overrides`: list of prompt numbers where Haiku disagrees with mechanical grade + reason

#### Invocation: `buildHaikuPrompt(digest) → { systemPrompt, userPrompt }`

Returns the two strings to send to Claude Haiku CLI:

```typescript
export function buildHaikuPrompt(digest: string): {
  systemPrompt: string;
  userPrompt: string;
} {
  return {
    systemPrompt: HAIKU_SYSTEM_PROMPT,  // Embedded constant
    userPrompt: digest,                  // Output from buildDigest()
  };
}
```

#### CLI Invocation (from `route.ts`)

```typescript
const { systemPrompt, userPrompt } = buildHaikuPrompt(digest);
const { stdout } = await execFileAsync(
  "claude",
  [
    "--model", "haiku",
    "--print",
    "--no-input",
    "-p", `${systemPrompt}\n\n---\n\n${userPrompt}`,
  ],
  { timeout: 60_000, maxBuffer: 1024 * 1024 }
);
```

**Key details:**
- Invoked via local `claude` CLI (not API)
- System + user prompts separated by `---` delimiter
- 60-second timeout, 1MB buffer
- Error handling: Haiku failures gracefully degrade to mechanical-only scoring

#### Response Parsing: `parseHaikuResponse(raw) → HaikuScorecard | null`

Extracts JSON from Haiku's response (handles both markdown code blocks and raw JSON):

```typescript
interface HaikuScorecard {
  score: number;                                      // 0-100
  promptGrades: Array<{ num: number; grade: ApproachGrade; reason: string }>;
  wentRight: string[];                               // Up to 5 bullets
  wentWrong: string[];                               // Up to 5 bullets
  overrides: Array<{
    num: number;
    mechanical: ApproachGrade;
    override: ApproachGrade;
    reason: string;
  }>;
  digestTokens: number;                             // Populated by caller
}
```

**Parsing logic:**
1. Try to extract JSON from markdown code block: ` ```json...``` `
2. Fall back to raw JSON: match first `{...}` in response
3. Type-coerce fields with safe defaults (missing fields → 0/"="/"")
4. Return null if no JSON found

---

## Part 4: Session Scoring Workflow (Orchestration)

### File: `app/api/daily-audit/grade-session/route.ts` (152 lines)

Complete end-to-end flow for a single session:

```
Input: { chainId, date, project }
  ↓
1. Build session chains & locate target chain
  ↓
2. Parse all sessions in chain → ParsedPromptEvent[]
  ↓
3. Mechanical grading → MechanicalGrade[]
  ↓
4. Build digest from chain + prompts + grades
  ↓
5. Estimate digest token count (length / 4)
  ↓
6. Build Haiku prompt (system + digest)
  ↓
7. Invoke Haiku CLI, parse response → HaikuScorecard | null
  ↓
8. Fallback: if Haiku fails, use mechanical grades only
  ↓
9. Merge scorecard with mechanical fallback (Haiku score preferred, mechanical as backup)
  ↓
10. Persist to database: { score, wentRight, wentWrong, promptGrades, digestTokens, haikuInputTokens, haikuOutputTokens }
  ↓
Output: { chainId, score, wentRight, wentWrong, promptGrades, digestTokens, haikuUsed }
```

**Token tracking:**
- `digestTokens`: estimated tokens for the compressed digest (used for request)
- `haikuInputTokens`: digest tokens + system prompt tokens (estimated)
- `haikuOutputTokens`: Haiku response tokens (estimated)
- `estimateTokens(text) = Math.ceil(text.length / 4)`

**Error handling:**
- If Haiku invocation fails (timeout, CLI error, JSON parse error): log warning, continue with mechanical grades
- Mechanical grades always available as fallback
- Database persistence always succeeds (stores null for Haiku fields if unavailable)

---

## Part 5: TypeScript Patterns for Python Translation

### 1. Type Unions → Python Unions

```typescript
type ApproachGrade = "!!" | "!" | "=" | "?" | "??";
type ConfidenceLevel = "high" | "medium" | "low";
type DailyAuditStatus = "draft" | "completed" | "failed" | "incomplete";
```

**Python equivalent:**
```python
from typing import Literal

ApproachGrade = Literal["!!", "!", "=", "?", "??"]
ConfidenceLevel = Literal["high", "medium", "low"]
DailyAuditStatus = Literal["draft", "completed", "failed", "incomplete"]
```

### 2. Interface → Pydantic Model

```typescript
interface MechanicalGrade {
  promptNum: number;
  grade: ApproachGrade;
  reason: string;
  filesEdited: string[];
  testsRan: number;
  testsPassed: number;
  errorsEncountered: number;
}
```

**Python equivalent:**
```python
from pydantic import BaseModel

class MechanicalGrade(BaseModel):
    promptNum: int
    grade: ApproachGrade
    reason: str
    filesEdited: list[str]
    testsRan: int
    testsPassed: int
    errorsEncountered: int
```

### 3. Map with Stateful Iteration → Dict

```typescript
const fileEditHistory = new Map<string, FileEditHistory[]>();
for (const fp of prompt.filesEdited) {
  const history = fileEditHistory.get(fp) ?? [];
  history.push(entry);
  fileEditHistory.set(fp, history);
}
```

**Python equivalent:**
```python
file_edit_history: dict[str, list[FileEditHistory]] = {}

for fp in prompt.files_edited:
    history = file_edit_history.get(fp, [])
    history.append(entry)
    file_edit_history[fp] = history
```

### 4. Array Methods → Python List Comprehensions

```typescript
const mechanicalGrades = gradePrompts(numberedPrompts);
const digest = buildDigest(chain, numberedPrompts, mechanicalGrades);
const flatMapped = parsedSessions.flatMap((p) => p.prompts);
const mapped = allPrompts.map((p, i) => ({ ...p, promptNum: i + 1 }));
```

**Python equivalent:**
```python
mechanical_grades = grade_prompts(numbered_prompts)
digest = build_digest(chain, numbered_prompts, mechanical_grades)
flat_mapped = [prompt for session in parsed_sessions if session for prompt in session.prompts]
mapped = [
    {**p, "promptNum": i + 1}
    for i, p in enumerate(all_prompts)
]
```

### 5. Async/Await → async/await (Identical in Python)

```typescript
const { stdout } = await execFileAsync("claude", [...], { timeout: 60_000 });
```

**Python equivalent:**
```python
proc = await asyncio.create_subprocess_exec(
    "claude", ...,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
```

### 6. String Interpolation → f-strings

```typescript
const reason = `Edited ${prompt.filesEdited.length} file(s) with ${prompt.testsPassed} passing test(s)`;
```

**Python equivalent:**
```python
reason = f"Edited {len(prompt.files_edited)} file(s) with {prompt.tests_passed} passing test(s)"
```

---

## Part 6: Token Estimation

### Formula: `estimateTokens(text) = Math.ceil(text.length / 4)`

Simple empirical ratio: 1 token ≈ 4 characters (rough approximation for English + code).

**Used for:**
- Estimating digest size before Haiku invocation
- Estimating system prompt + user prompt tokens for input accounting
- Estimating Haiku response tokens for output accounting

**Accuracy:** ±20% for typical digests (100-5000 tokens); more accurate for larger texts.

---

## Part 7: Type Definitions (Complete)

### From `lib/daily-audit/types.ts` (237 lines)

Key types for Python translation:

```typescript
export type ApproachGrade = "!!" | "!" | "=" | "?" | "??";
export type ConfidenceLevel = "high" | "medium" | "low";

export interface DailyIntentRecord {
  id: string;
  date: string;
  intent: string;
  why_now: string;
  success_criteria_json: string;
  expected_evidence_json: string;
  fallback_plan_json: string;
  overnight_tasks_json: string;
  created_from_audit_id: string | null;
  status: DailyIntentStatus;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface SessionGradeRecord {
  id: string;
  chain_id: string;
  date: string;
  project: string;
  source: string;
  session_ids_json: string;
  score: number | null;
  went_right_json: string | null;
  went_wrong_json: string | null;
  prompt_grades_json: string | null;
  prompt_count: number | null;
  digest_tokens: number | null;
  haiku_input_tokens: number | null;
  haiku_output_tokens: number | null;
  graded_at: string;
}

export interface HaikuPromptGrade {
  num: number;
  grade: ApproachGrade;
  reason: string;
}

export interface HaikuOverride {
  num: number;
  mechanical: ApproachGrade;
  override: ApproachGrade;
  reason: string;
}
```

---

## Part 8: Implementation Roadmap for Python Port

### Phase 1: Core Mechanical Grader (Foundation)
- [ ] Implement `MechanicalGrade` Pydantic model
- [ ] Implement `ParsedPromptEvent` Pydantic model
- [ ] Implement `ToolCallSummary` Pydantic model
- [ ] Implement `grade_prompts(prompts: list[ParsedPromptEvent]) -> list[MechanicalGrade]`
- [ ] Unit tests: revert detection (70% threshold), consecutive failure counter, all 6 rules
- [ ] Integration test: full prompt sequence → correct grades + state transitions

### Phase 2: Digest Building + Haiku Integration
- [ ] Implement `HaikuScorecard` Pydantic model
- [ ] Implement `build_digest(chain, prompts, grades) -> str`
- [ ] Implement `build_haiku_prompt(digest) -> dict[str, str]`
- [ ] Implement `parse_haiku_response(raw: str) -> HaikuScorecard | None`
- [ ] Implement `estimate_tokens(text: str) -> int`
- [ ] Haiku CLI integration: invoke via `subprocess.run()` or `asyncio`
- [ ] Error handling + fallback to mechanical grades
- [ ] Integration test: end-to-end from digest → Haiku → scorecard

### Phase 3: Segment-Level Grading (Optional, V2)
- [ ] Review `lib/daily-audit/grading-rubric.ts` (segment-level rules)
- [ ] Implement segment grading DSL (more complex, lower priority)
- [ ] Defer until Phase 1 + 2 proven in production

### Phase 4: Persistence + API Bridge
- [ ] SQLite schema for session grades (match `SessionGradeRecord`)
- [ ] Implement persistence layer: `upsert_session_grade()`
- [ ] REST API endpoint: `/api/score-session` (mirror of mission-control)
- [ ] Integration test: full orchestration pipeline

### Testing Strategy
- **Unit tests** for each rule in mechanical grading (no mocks)
- **Integration tests** for stateful sequences (file edits → reverts → consecutive failures)
- **API tests** for Haiku invocation (can mock Haiku response for CI)
- **Golden tests** comparing Python output to mission-control TypeScript for known sessions

---

## Part 9: Open Questions & Edge Cases

### Unresolved (Not in mission-control, need design)

1. **Multi-session handling**: If a chain spans multiple sessions (context overflow), how should overall session score reflect per-session grades?
   - Current: Haiku sees digest with session boundaries; treats as one combined score
   - Question: Should we pre-score each session, then aggregate? Or keep combined?

2. **Memory layer**: mission-control has no persistent memory between sessions (next session starts fresh)
   - detrix-core MVP requires memory: "append-only + KV retrieval"
   - Research needed: how to feed prior sessions' learnings into next session's grading?

3. **Domain-specific evaluators**: mission-control uses generic mechanical rules + Haiku override
   - detrix-core will have domain-specific gates (AgentXRD metrology, ParabolaHunter convergence checks)
   - Question: Where do domain evaluators fit? Pre-mechanical? Post-Haiku? Parallel?

4. **Confidence levels**: `HaikuOverride` includes implicit confidence (reason field), but no explicit confidence level
   - Should overrides include `ConfidenceLevel` (high/medium/low)?
   - How should low-confidence overrides be weighted vs. mechanical grades?

5. **Test command detection**: `isTestCommand` is hardcoded pattern matching on tool name
   - What patterns are matched? (`pytest`, `npm test`, `go test`, etc.)
   - Needs porting: see `session-parser.ts` for exact patterns

---

## Part 10: File Structure for Python Port

Suggested directory layout:

```
detrix-core/src/detrix/scoring/
├── __init__.py
├── models.py                    # Pydantic models (MechanicalGrade, HaikuScorecard, etc.)
├── mechanical.py                # grade_prompts() + stateful engine
├── digest.py                    # build_digest(), build_haiku_prompt(), estimate_tokens()
├── haiku.py                     # haiku_invoke(), parse_haiku_response()
├── orchestration.py             # grade_session() top-level endpoint
└── persistence.py               # upsert_session_grade(), database layer

detrix-core/tests/
├── test_mechanical_grader.py    # Unit + integration tests for grading rules
├── test_digest.py               # Digest building correctness
├── test_haiku_integration.py    # Haiku CLI mocking + response parsing
└── test_scoring_e2e.py          # End-to-end orchestration
```

---

## Summary

The mission-control scoring architecture is **production-proven, stateful, and deterministic**. Porting to Python requires:

1. **Faithfulness to stateful logic**: Maintain exact revert detection (70% threshold) and consecutive failure counter semantics
2. **Pydantic models**: Strict type safety for all data structures
3. **Haiku CLI integration**: Subprocess invocation with timeout + error handling
4. **Test coverage**: Golden tests comparing to mission-control for regressions
5. **Documentation**: Embed the six grading rules + state machine in docstrings

The mechanical grader is the foundation; Haiku provides semantic override capability. Both are needed for the full two-tier system.

No implementation code has been written — this document is research/design only.
