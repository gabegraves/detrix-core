"""Regression tests for repo-local agent_memory integration."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_repo_exposes_memoria_mcp_server() -> None:
    config_path = REPO_ROOT / ".mcp.json"
    assert config_path.exists(), "detrix-core should provide a repo-local MCP config"

    config = json.loads(config_path.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})
    assert "memoria" in servers, "detrix-core should wire the memoria MCP server"

    memoria = servers["memoria"]
    assert memoria.get("command") == "python3"
    assert "../agent_memory/scripts/memoria_mcp_server.py" in memoria.get("args", [])

    target = (REPO_ROOT / memoria["args"][0]).resolve()
    if target.exists():
        return

    is_isolated_superpowers_worktree = (
        Path.home() / ".config" / "superpowers" / "worktrees"
    ) in REPO_ROOT.parents
    assert is_isolated_superpowers_worktree, (
        "repo-local memoria MCP target should resolve from the checkout root; "
        f"missing target: {target}"
    )

    canonical_repo_root = Path.home() / "Desktop" / "detrix-core"
    canonical_target = (canonical_repo_root / memoria["args"][0]).resolve()
    assert canonical_target.exists(), (
        "isolated superpowers worktrees use the canonical Desktop checkout sibling; "
        f"missing canonical target: {canonical_target}"
    )
