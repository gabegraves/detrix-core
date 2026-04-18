"""Regression tests for published packaging metadata."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_memory_extra_is_not_repo_local_only() -> None:
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    publishes_memory_extra = 'memory = ["memoria-client"]' in pyproject_text
    uses_repo_local_override = (
        'memoria-client = {path = "../agent_memory/memoria_client"}' in pyproject_text
    )

    assert not (
        publishes_memory_extra and uses_repo_local_override
    ), "published extras must not rely on repo-local uv path overrides"
