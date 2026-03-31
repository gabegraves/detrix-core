"""Mechanical grading engine for scoring prompts based on file edits and test results."""

from __future__ import annotations

from detrix.scoring.types import ApproachGrade, PromptChange, SessionDigest


class FileEditHistory:
    """Tracks file modifications across prompts."""

    def __init__(self) -> None:
        self.files: dict[str, dict[str, int]] = {}

    def record_edit(self, file_path: str, added: int, deleted: int) -> None:
        """Record a file edit."""
        if file_path not in self.files:
            self.files[file_path] = {
                "additions": 0,
                "deletions": 0,
                "edit_count": 0,
            }
        self.files[file_path]["additions"] += added
        self.files[file_path]["deletions"] += deleted
        self.files[file_path]["edit_count"] += 1

    def is_revert(self, file_path: str) -> bool:
        """Check if file removals >= 70% of previous additions (revert detection)."""
        if file_path not in self.files:
            return False
        file_data = self.files[file_path]
        additions = file_data["additions"]
        deletions = file_data["deletions"]
        if additions == 0:
            return False
        revert_ratio = deletions / additions
        return revert_ratio >= 0.7

    def reset(self) -> None:
        """Reset history for next prompt."""
        self.files.clear()


def grade_prompts(
    prompt_changes: list[PromptChange],
    consecutive_failure_threshold: int = 2,
) -> dict[int, ApproachGrade]:
    """
    Grade prompts based on file edits, test results, and error patterns.

    Algorithm:
    - If file revert detected (removals >= 70% of additions) OR consecutive failures >= threshold: "??"
    - Else if errors present OR test failures present: "?"
    - Else if edits present AND test passes present: "!!"
    - Else if edits present: "!"
    - Else: "="

    Args:
        prompt_changes: List of PromptChange records with file/test metrics per prompt
        consecutive_failure_threshold: Number of consecutive failures to trigger "??"

    Returns:
        Dict mapping prompt_index to ApproachGrade
    """
    grades: dict[int, ApproachGrade] = {}
    file_history = FileEditHistory()
    consecutive_failures: dict[int, int] = {}  # track failures per file

    for change in prompt_changes:
        prompt_idx = change.prompt_index
        has_edits = (
            change.files_added > 0
            or change.files_modified > 0
            or change.files_deleted > 0
        )
        has_errors = change.errors > 0
        has_test_fail = change.test_failures > 0
        has_test_pass = change.test_passes > 0

        # Track file edits for revert detection
        if change.files_added > 0:
            # Simplified: count as a generic file edit
            file_history.record_edit(f"prompt_{prompt_idx}", change.files_added, 0)
        if change.files_deleted > 0:
            file_history.record_edit(
                f"prompt_{prompt_idx}", 0, change.files_deleted
            )

        # Update consecutive failure tracking
        if has_test_fail:
            consecutive_failures[prompt_idx] = (
                consecutive_failures.get(prompt_idx, 0) + 1
            )
        else:
            consecutive_failures[prompt_idx] = 0

        # Determine grade
        has_revert = file_history.is_revert(f"prompt_{prompt_idx}")
        has_consecutive_failures = (
            consecutive_failures.get(prompt_idx, 0)
            >= consecutive_failure_threshold
        )

        if has_revert or has_consecutive_failures:
            grades[prompt_idx] = ApproachGrade.MAJOR_NEGATIVE
        elif has_errors or has_test_fail:
            grades[prompt_idx] = ApproachGrade.NEGATIVE
        elif has_edits and has_test_pass:
            grades[prompt_idx] = ApproachGrade.MAJOR_POSITIVE
        elif has_edits:
            grades[prompt_idx] = ApproachGrade.POSITIVE
        else:
            grades[prompt_idx] = ApproachGrade.NEUTRAL

    return grades


def build_session_digest(
    session_id: str,
    prompt_changes: list[PromptChange],
    mechanical_grades: dict[int, ApproachGrade],
) -> SessionDigest:
    """
    Build a compressed session digest for Haiku review.

    Args:
        session_id: Unique session identifier
        prompt_changes: Per-prompt activity metrics
        mechanical_grades: Mechanical grades per prompt

    Returns:
        SessionDigest with compressed activity representation
    """
    reverted_prompts = [
        idx
        for idx, grade in mechanical_grades.items()
        if grade == ApproachGrade.MAJOR_NEGATIVE
    ]
    consecutive_failures: dict[int, int] = {}

    for change in prompt_changes:
        if change.test_failures > 0:
            consecutive_failures[change.prompt_index] = (
                consecutive_failures.get(change.prompt_index, 0) + 1
            )

    # Rough token estimation (1 prompt_change ≈ 50 tokens)
    estimated_tokens = len(prompt_changes) * 50

    return SessionDigest(
        session_id=session_id,
        prompt_count=len(prompt_changes),
        prompt_changes=prompt_changes,
        mechanical_grades=mechanical_grades,
        reverted_prompts=reverted_prompts,
        consecutive_failures=consecutive_failures,
        estimated_tokens=estimated_tokens,
    )
