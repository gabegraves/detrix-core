"""Haiku judge for AI-powered scoring of agent session digests.

Sends a SessionDigest to Claude via Vercel AI Gateway (OIDC-authenticated)
and returns a structured HaikuScorecard with 0-100 score and detailed feedback.
"""

from __future__ import annotations

import http.client
import json
import os
from typing import Any, Optional

from detrix.scoring.types import (
    ApproachGrade,
    ConfidenceLevel,
    HaikuOverride,
    HaikuPromptGrade,
    HaikuScorecard,
    PromptChange,
    SessionDigest,
)


def build_digest_text(digest: SessionDigest) -> str:
    """
    Format a SessionDigest into human-readable text for the Haiku judge.

    Args:
        digest: Compressed session activity summary

    Returns:
        Formatted text description of the session
    """
    lines: list[str] = []
    lines.append(f"Session ID: {digest.session_id}")
    lines.append(f"Total Prompts: {digest.prompt_count}")
    lines.append("")

    lines.append("Mechanical Grades by Prompt:")
    for idx in range(digest.prompt_count):
        grade = digest.mechanical_grades.get(idx, ApproachGrade.NEUTRAL)
        lines.append(f"  Prompt {idx}: {grade.value}")

    if digest.reverted_prompts:
        lines.append(f"\nReverted Prompts (>70% revert ratio): {digest.reverted_prompts}")

    lines.append("\nPer-Prompt Activity:")
    for change in digest.prompt_changes:
        lines.append(f"  Prompt {change.prompt_index}:")
        lines.append(f"    Files added: {change.files_added}")
        lines.append(f"    Files modified: {change.files_modified}")
        lines.append(f"    Files deleted: {change.files_deleted}")
        lines.append(f"    Errors: {change.errors}")
        lines.append(f"    Test failures: {change.test_failures}")
        lines.append(f"    Test passes: {change.test_passes}")

    if digest.consecutive_failures:
        lines.append("\nConsecutive Test Failures:")
        for idx, count in digest.consecutive_failures.items():
            lines.append(f"  Prompt {idx}: {count} consecutive failures")

    lines.append(f"\nEstimated Tokens: {digest.estimated_tokens}")

    return "\n".join(lines)


def build_haiku_prompt(
    digest: SessionDigest,
) -> tuple[str, str]:
    """
    Build system and user prompts for Claude to score a session.

    Args:
        digest: Session activity summary

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are a rigorous AI agent evaluator. Your role is to assess agent session quality based on mechanical metrics and overall approach effectiveness.

You will receive a session digest containing:
- Mechanical grades (symbol-based: !! = major positive, ! = positive, = = neutral, ? = negative, ?? = major negative)
- Per-prompt file changes (additions, deletions, modifications)
- Test results (passes and failures)
- Error counts
- Revert detection (>70% deletion ratio)

Provide a structured JSON scorecard with:
1. A 0-100 overall score
2. Per-prompt grades with reasoning
3. Key positives (what went right)
4. Key negatives (what went wrong)
5. Optional overrides (corrections to mechanical grades)
6. Confidence level (high/medium/low)
7. Optional notes

Scoring guidance:
- 0-20: Major failures (reverts, consistent errors, no progress)
- 21-40: Problematic (many failures, few successes, poor direction)
- 41-60: Mixed (some progress, some setbacks, unclear direction)
- 61-80: Solid (good progress, minor issues, clear intent)
- 81-100: Excellent (consistent progress, test passing, thoughtful approach)

Be direct and specific. Reference actual metrics (test pass rates, file change patterns) in your reasoning."""

    digest_text = build_digest_text(digest)
    user_prompt = f"""Please score this session:

{digest_text}

Return ONLY valid JSON matching this schema:
{{
  "score": <0-100>,
  "prompt_grades": [
    {{"prompt_index": 0, "grade": "!!", "reasoning": "..."}}
  ],
  "went_right": ["..."],
  "went_wrong": ["..."],
  "overrides": [
    {{"prompt_index": 0, "grade": "??", "reason": "..."}}
  ],
  "confidence": "high|medium|low",
  "notes": "optional"
}}"""

    return system_prompt, user_prompt


def parse_haiku_response(response_text: str) -> HaikuScorecard:
    """
    Parse Claude's JSON response into a HaikuScorecard.

    Args:
        response_text: Raw JSON response from Claude

    Returns:
        Parsed HaikuScorecard

    Raises:
        ValueError: If response is not valid JSON or missing required fields
    """
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from Claude: {e}")

    score: int = data.get("score", 50)
    if not isinstance(score, int) or score < 0 or score > 100:
        score = 50

    prompt_grades: list[HaikuPromptGrade] = []
    for pg in data.get("prompt_grades", []):
        try:
            grade_val = pg.get("grade", "=")
            grade = ApproachGrade(grade_val)
            prompt_grades.append(
                HaikuPromptGrade(
                    prompt_index=pg.get("prompt_index", 0),
                    grade=grade,
                    reasoning=pg.get("reasoning", ""),
                    file_references=pg.get("file_references", []),
                )
            )
        except (ValueError, KeyError):
            pass

    went_right: list[str] = data.get("went_right", [])
    went_wrong: list[str] = data.get("went_wrong", [])

    overrides: list[HaikuOverride] = []
    for ov in data.get("overrides", []):
        try:
            override_grade = ApproachGrade(ov.get("grade", "="))
            overrides.append(
                HaikuOverride(
                    prompt_index=ov.get("prompt_index", 0),
                    grade=override_grade,
                    reason=ov.get("reason", ""),
                )
            )
        except ValueError:
            pass

    confidence_str = data.get("confidence", "medium").lower()
    try:
        confidence = ConfidenceLevel(confidence_str)
    except ValueError:
        confidence = ConfidenceLevel.MEDIUM

    notes = data.get("notes")

    return HaikuScorecard(
        score=score,
        prompt_grades=prompt_grades,
        went_right=went_right,
        went_wrong=went_wrong,
        overrides=overrides,
        confidence=confidence,
        notes=notes,
    )


def score_session(
    digest: SessionDigest,
    api_key: Optional[str] = None,
) -> HaikuScorecard:
    """
    Score a session using Claude via Vercel AI Gateway.

    Uses OIDC authentication (VERCEL_OIDC_TOKEN from environment) by default.
    Falls back to AI_GATEWAY_API_KEY if VERCEL_OIDC_TOKEN not available.

    Args:
        digest: Session activity summary to score
        api_key: Optional API key override (for testing). If not provided,
                 uses VERCEL_OIDC_TOKEN or AI_GATEWAY_API_KEY from environment.

    Returns:
        HaikuScorecard with 0-100 score and detailed feedback

    Raises:
        ValueError: If no authentication method is available
        RuntimeError: If API call fails
    """
    # Determine authentication
    auth_token = api_key
    if not auth_token:
        auth_token = os.environ.get("VERCEL_OIDC_TOKEN")
    if not auth_token:
        auth_token = os.environ.get("AI_GATEWAY_API_KEY")
    if not auth_token:
        raise ValueError(
            "No authentication token found. "
            "Set VERCEL_OIDC_TOKEN or AI_GATEWAY_API_KEY environment variable."
        )

    system_prompt, user_prompt = build_haiku_prompt(digest)

    # Build API request payload
    payload: dict[str, Any] = {
        "model": "anthropic/claude-sonnet-4.6",
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        "system": system_prompt,
        "temperature": 1.0,
        "max_tokens": 2000,
    }

    # Call Vercel AI Gateway
    conn = http.client.HTTPSConnection("api.vercel.com")
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    try:
        conn.request(
            "POST",
            "/v1/chat/completions",
            json.dumps(payload),
            headers,
        )
        response = conn.getresponse()
        response_data = json.loads(response.read().decode())

        if response.status != 200:
            raise RuntimeError(
                f"AI Gateway API error {response.status}: "
                f"{response_data.get('error', {}).get('message', 'Unknown error')}"
            )

        # Extract response text
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("No content in API response")

        # Parse and return scorecard
        scorecard = parse_haiku_response(content)
        return scorecard

    finally:
        conn.close()
