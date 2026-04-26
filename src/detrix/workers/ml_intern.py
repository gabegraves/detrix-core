"""Privacy-safe subprocess boundary for Hugging Face ml-intern.

ml-intern is treated only as a training worker. This module never writes Detrix
trajectory evidence, never evaluates domain quality, and never promotes models.
Detrix callers must run post-hoc governance/evaluation on any artifact returned
from this worker before using it for a challenger or deployment decision.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

RedactionStatus = Literal["clean", "redacted", "blocked"]

_REQUIRED_PRIVACY_VALUES: dict[str, object] = {
    "save_sessions": False,
    "auto_file_upload": False,
    "yolo_mode": False,
    "confirm_cpu_jobs": True,
}
_DEFAULT_ALLOWED_ARTIFACTS = (
    "stdout.log",
    "stderr.log",
    "mlintern_result.json",
    "training_result.json",
    "adapter/*.safetensors",
    "adapter/**/*.safetensors",
    "adapter/adapter_config.json",
    "adapter/**/adapter_config.json",
    "adapter/tokenizer.json",
    "adapter/**/tokenizer.json",
    "adapter/tokenizer_config.json",
    "adapter/**/tokenizer_config.json",
    "adapter/special_tokens_map.json",
    "adapter/**/special_tokens_map.json",
    "reports/*.json",
    "reports/**/*.json",
    "reports/*.md",
    "reports/**/*.md",
)
_FORBIDDEN_NAME_FRAGMENTS = (
    ".env",
    "token",
    "secret",
    "credential",
    "password",
    "passwd",
    "apikey",
    "api_key",
    "hf_home",
)
_SOURCE_IGNORE_NAMES = {
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


class MLInternPrivacyError(RuntimeError):
    """Raised when the worker cannot enforce fail-closed privacy controls."""


class MLInternArtifact(BaseModel):
    """Single artifact discovered in the declared ml-intern output directory."""

    relative_path: str
    sha256: str
    byte_size: int
    media_type: str
    redaction_status: RedactionStatus = "clean"


class MLInternResult(BaseModel):
    """Structured result returned by the ml-intern subprocess boundary."""

    command: list[str]
    prompt_hash: str
    cwd: str
    timeout_seconds: int
    exit_code: int | None
    stdout_path: str
    stderr_path: str
    artifact_manifest: list[MLInternArtifact]
    started_at: datetime
    finished_at: datetime
    redaction_status: RedactionStatus
    privacy_config_path: str
    timed_out: bool = False

    @property
    def promotion_allowed(self) -> bool:
        """Whether this result may proceed to Detrix post-hoc evaluation.

        This is only a privacy/artifact gate. It does not mean the challenger is
        good, governed, or promotable; Detrix evaluation still owns that verdict.
        """
        return self.redaction_status != "blocked"


class MLInternWorkerConfig(BaseModel):
    """Configuration for source-checkout ml-intern execution."""

    ml_intern_source_dir: Path
    run_root: Path = Path(".detrix/ml-intern-runs")
    model_name: str
    timeout_seconds: int = 1800
    max_iterations: int = 3
    allowed_artifact_globs: tuple[str, ...] = _DEFAULT_ALLOWED_ARTIFACTS
    max_artifact_bytes: int = 512 * 1024 * 1024
    mcp_servers: dict[str, object] = Field(default_factory=dict)
    extra_privacy_config: dict[str, object] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("timeout_seconds", "max_iterations", "max_artifact_bytes")
    @classmethod
    def _must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be positive")
        return value


Runner = Callable[..., subprocess.CompletedProcess[str]]


class MLInternWorker:
    """Run ml-intern from a sanitized source checkout and capture artifacts.

    The wrapper deliberately forbids global-binary mode. Governed use requires a
    local source checkout so Detrix can rewrite and read back the copied
    `configs/cli_agent_config.json` before execution.
    """

    def __init__(
        self,
        config: MLInternWorkerConfig,
        *,
        runner: Runner | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self._runner = runner or subprocess.run
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(self, prompt: str) -> MLInternResult:
        """Execute ml-intern with a bounded prompt and fail-closed privacy setup."""
        source_dir = self.config.ml_intern_source_dir.expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise MLInternPrivacyError(
                f"ml-intern source checkout is required and was not found: {source_dir}"
            )

        run_dir = self._new_run_dir(prompt)
        safe_source = run_dir / "ml-intern-src"
        output_dir = run_dir / "outputs"
        cache_dir = run_dir / "cache"
        home_dir = run_dir / "home"
        output_dir.mkdir(parents=True, exist_ok=False)
        cache_dir.mkdir(parents=True, exist_ok=True)
        home_dir.mkdir(parents=True, exist_ok=True)

        self._copy_source_checkout(source_dir, safe_source)
        privacy_config_path = self._write_and_verify_privacy_config(safe_source)

        stdout_path = output_dir / "stdout.log"
        stderr_path = output_dir / "stderr.log"
        command = self._build_command(safe_source, output_dir, prompt)
        baseline_source_files = self._snapshot_source_files(safe_source)
        env = self._build_env(cache_dir=cache_dir, home_dir=home_dir, output_dir=output_dir)
        started_at = self._clock()
        exit_code: int | None
        timed_out = False

        try:
            completed = self._runner(
                command,
                cwd=str(safe_source),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )
            exit_code = completed.returncode
            unsafe_output_dir = _prepare_output_dir_for_metadata(output_dir)
            _write_text_no_symlink(stdout_path, completed.stdout or "")
            _write_text_no_symlink(stderr_path, completed.stderr or "")
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = None
            unsafe_output_dir = _prepare_output_dir_for_metadata(output_dir)
            _write_text_no_symlink(stdout_path, _decode_timeout_stream(exc.stdout))
            _write_text_no_symlink(stderr_path, _decode_timeout_stream(exc.stderr))

        finished_at = self._clock()
        manifest = self.scan_artifacts(
            run_dir, output_dir=output_dir, baseline_source_files=baseline_source_files
        )
        if unsafe_output_dir:
            manifest.append(_blocked_output_dir_artifact())
        redaction_status = self._aggregate_redaction(manifest)

        return MLInternResult(
            command=command,
            prompt_hash=self.prompt_hash(prompt),
            cwd=str(safe_source),
            timeout_seconds=self.config.timeout_seconds,
            exit_code=exit_code,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            artifact_manifest=manifest,
            started_at=started_at,
            finished_at=finished_at,
            redaction_status=redaction_status,
            privacy_config_path=str(privacy_config_path),
            timed_out=timed_out,
        )

    @staticmethod
    def prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def scan_artifacts(
        self,
        run_dir: Path,
        *,
        output_dir: Path | None = None,
        baseline_source_files: dict[str, str] | None = None,
    ) -> list[MLInternArtifact]:
        """Scan the entire run directory and enforce output-dir-only artifacts.

        Allowed artifacts are reported relative to the declared output directory.
        Any file created elsewhere in the copied checkout/run directory is blocked
        so ml-intern cannot hide raw datasets, tokens, or arbitrary workspace files
        outside the allowlisted output tree.
        """
        run_dir = run_dir.resolve()
        output_dir = (output_dir or run_dir / "outputs").resolve()
        if not run_dir.exists():
            return []
        safe_source = run_dir / "ml-intern-src"
        baseline_source_files = baseline_source_files or self._snapshot_source_files(safe_source)

        artifacts: list[MLInternArtifact] = []
        for path in sorted(
            candidate
            for candidate in run_dir.rglob("*")
            if candidate.is_file() or candidate.is_symlink()
        ):
            if self._is_baseline_run_file(path, run_dir=run_dir, output_dir=output_dir):
                continue
            try:
                source_relative = path.relative_to(safe_source).as_posix()
                if (
                    not path.is_symlink()
                    and baseline_source_files.get(source_relative) == _sha256_file(path)
                ):
                    continue
            except ValueError:
                pass
            try:
                relative_to_output = path.relative_to(output_dir).as_posix()
                relative_path = relative_to_output
                outside_output = False
            except ValueError:
                relative_path = path.relative_to(run_dir).as_posix()
                outside_output = True
            status: RedactionStatus = (
                "blocked"
                if path.is_symlink()
                or outside_output
                or self._is_forbidden_artifact(relative_path, path)
                else "clean"
            )
            artifacts.append(
                MLInternArtifact(
                    relative_path=relative_path,
                    sha256=_sha256_artifact(path),
                    byte_size=path.lstat().st_size if path.is_symlink() else path.stat().st_size,
                    media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                    redaction_status=status,
                )
            )
        return artifacts

    def _new_run_dir(self, prompt: str) -> Path:
        prompt_prefix = self.prompt_hash(prompt)[:12]
        timestamp = self._clock().strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.config.run_root / f"mlintern-{timestamp}-{prompt_prefix}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir.resolve()

    @staticmethod
    def _copy_source_checkout(source_dir: Path, safe_source: Path) -> None:
        def ignore(_dir: str, names: Sequence[str]) -> set[str]:
            ignored: set[str] = set()
            for name in names:
                if name in _SOURCE_IGNORE_NAMES or name.startswith("."):
                    ignored.add(name)
            return ignored

        shutil.copytree(source_dir, safe_source, ignore=ignore)

    def _write_and_verify_privacy_config(self, safe_source: Path) -> Path:
        config_dir = safe_source / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "cli_agent_config.json"
        payload = {
            **self.config.extra_privacy_config,
            **_REQUIRED_PRIVACY_VALUES,
            "mcpServers": dict(self.config.mcp_servers),
            "model_name": self.config.model_name,
            "auto_save_interval": 0,
            "heartbeat_interval_s": 0,
        }
        config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        try:
            read_back = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MLInternPrivacyError("could not read back ml-intern privacy config") from exc

        for key, expected in _REQUIRED_PRIVACY_VALUES.items():
            if read_back.get(key) != expected:
                raise MLInternPrivacyError(
                    f"unsafe ml-intern privacy config: {key}={read_back.get(key)!r}"
                )
        if read_back.get("mcpServers") != dict(self.config.mcp_servers):
            raise MLInternPrivacyError("unsafe ml-intern privacy config: unexpected MCP servers")
        if not read_back.get("model_name"):
            raise MLInternPrivacyError("unsafe ml-intern privacy config: model_name missing")
        return config_path

    def _build_command(self, safe_source: Path, output_dir: Path, prompt: str) -> list[str]:
        prompt_path = safe_source.parent / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        shim_path = self._write_safe_headless_shim(safe_source)
        return [
            "uv",
            "run",
            "--project",
            str(safe_source),
            "python",
            str(shim_path),
            "--prompt-file",
            str(prompt_path),
            "--output-dir",
            str(output_dir),
            "--model",
            self.config.model_name,
            "--max-iterations",
            str(self.config.max_iterations),
        ]

    @staticmethod
    def _write_safe_headless_shim(safe_source: Path) -> Path:
        shim_path = safe_source / "detrix_safe_headless.py"
        shim_path.write_text(_SAFE_HEADLESS_SHIM, encoding="utf-8")
        return shim_path

    def _build_env(self, *, cache_dir: Path, home_dir: Path, output_dir: Path) -> dict[str, str]:
        protected_keys = {
            "HOME",
            "HF_HOME",
            "TRANSFORMERS_CACHE",
            "HF_HUB_DISABLE_TELEMETRY",
            "PYTHONNOUSERSITE",
            "DETRIX_MLINTERN_OUTPUT_DIR",
        }
        forbidden = protected_keys & self.config.env.keys()
        if forbidden:
            raise MLInternPrivacyError(
                "caller env cannot override privacy isolation keys: "
                + ", ".join(sorted(forbidden))
            )
        env: dict[str, str] = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(home_dir),
            "HF_HOME": str(cache_dir / "hf"),
            "TRANSFORMERS_CACHE": str(cache_dir / "transformers"),
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "PYTHONNOUSERSITE": "1",
            "DETRIX_MLINTERN_OUTPUT_DIR": str(output_dir),
        }
        env.update(self.config.env)
        return env

    @staticmethod
    def _is_baseline_run_file(path: Path, *, run_dir: Path, output_dir: Path) -> bool:
        if path.is_symlink():
            return False
        baseline_files = {
            run_dir / "prompt.txt",
            output_dir / "stdout.log",
            output_dir / "stderr.log",
        }
        return path in baseline_files

    @staticmethod
    def _snapshot_source_files(safe_source: Path) -> dict[str, str]:
        return {
            path.relative_to(safe_source).as_posix(): _sha256_file(path)
            for path in safe_source.rglob("*")
            if path.is_file() and not path.is_symlink()
        }

    def _is_forbidden_artifact(self, relative_path: str, path: Path) -> bool:
        parts = Path(relative_path).parts
        if any(part.startswith(".") for part in parts):
            return True
        lowered = relative_path.lower()
        if any(fragment in lowered for fragment in _FORBIDDEN_NAME_FRAGMENTS):
            return True
        if path.stat().st_size > self.config.max_artifact_bytes:
            return True
        return not any(
            fnmatch.fnmatch(relative_path, pattern)
            or fnmatch.fnmatch(path.name, pattern)
            for pattern in self.config.allowed_artifact_globs
        )

    @staticmethod
    def _aggregate_redaction(manifest: Sequence[MLInternArtifact]) -> RedactionStatus:
        if any(artifact.redaction_status == "blocked" for artifact in manifest):
            return "blocked"
        if any(artifact.redaction_status == "redacted" for artifact in manifest):
            return "redacted"
        return "clean"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text_no_symlink(path: Path, text: str) -> None:
    if path.is_symlink() or path.exists():
        path.unlink()
    path.write_text(text, encoding="utf-8")


def _prepare_output_dir_for_metadata(output_dir: Path) -> bool:
    """Ensure captured subprocess logs are written only into the real output dir."""
    if output_dir.is_symlink() or output_dir.is_file():
        output_dir.unlink()
        output_dir.mkdir(parents=True, exist_ok=False)
        return True
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=False)
        return True
    if not output_dir.is_dir():
        output_dir.unlink()
        output_dir.mkdir(parents=True, exist_ok=False)
        return True
    return False


def _blocked_output_dir_artifact() -> MLInternArtifact:
    return MLInternArtifact(
        relative_path="outputs",
        sha256=hashlib.sha256(b"unsafe-output-dir-recreated").hexdigest(),
        byte_size=0,
        media_type="inode/directory",
        redaction_status="blocked",
    )


def _sha256_artifact(path: Path) -> str:
    if path.is_symlink():
        return hashlib.sha256(f"symlink:{os.readlink(path)}".encode()).hexdigest()
    return _sha256_file(path)


def _decode_timeout_stream(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def assert_ml_intern_result_can_enter_governance(result: MLInternResult) -> None:
    """Fail closed before any demo/promotion code consumes worker artifacts."""
    if not result.promotion_allowed:
        blocked = [
            artifact.relative_path
            for artifact in result.artifact_manifest
            if artifact.redaction_status == "blocked"
        ]
        raise MLInternPrivacyError(
            "ml-intern result contains blocked artifacts and cannot enter governance: "
            + ", ".join(blocked)
        )

_SAFE_HEADLESS_SHIM = r'''
"""Detrix-generated safe headless entrypoint for ml-intern source checkouts.

This intentionally does not call agent.main.headless_main because upstream
headless mode forces yolo_mode=True and auto-approves approval_required events.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from agent.config import load_config
from agent.core.agent_loop import submission_loop
from agent.core.session import OpType
from agent.core.tools import ToolRouter
from agent.main import (
    CLI_CONFIG_PATH,
    Operation,
    Submission,
    _StreamBuffer,
    _configure_runtime_logging,
    _create_rich_console,
    _get_hf_token,
    print_error,
    print_markdown,
    print_tool_call,
    print_tool_log,
    print_tool_output,
)


async def detrix_safe_headless(prompt: str, model: str, max_iterations: int) -> int:
    logging.basicConfig(level=logging.WARNING)
    _configure_runtime_logging()
    hf_token = _get_hf_token()
    if not hf_token:
        print("ERROR: No HF token found. Set HF_TOKEN explicitly for the Detrix worker.", file=sys.stderr)
        return 1

    config = load_config(CLI_CONFIG_PATH)
    config.yolo_mode = False
    config.model_name = model
    config.max_iterations = max_iterations
    if config.save_sessions or config.auto_file_upload or config.yolo_mode or config.mcpServers:
        print("ERROR: unsafe ml-intern config after load", file=sys.stderr)
        return 2

    submission_queue: asyncio.Queue = asyncio.Queue()
    event_queue: asyncio.Queue = asyncio.Queue()
    tool_router = ToolRouter(config.mcpServers, hf_token=hf_token, local_mode=True)
    session_holder: list = [None]
    agent_task = asyncio.create_task(
        submission_loop(
            submission_queue,
            event_queue,
            config=config,
            tool_router=tool_router,
            session_holder=session_holder,
            hf_token=hf_token,
            local_mode=True,
            stream=False,
        )
    )

    try:
        while True:
            event = await event_queue.get()
            if event.event_type == "ready":
                break
            if event.event_type == "error":
                print_error(event.data.get("error", "Unknown error") if event.data else "Unknown error")
                return 3

        await submission_queue.put(
            Submission(id="detrix_sub_1", operation=Operation(op_type=OpType.USER_INPUT, data={"text": prompt}))
        )
        console = _create_rich_console()
        stream_buf = _StreamBuffer(console)
        last_tool = [None]
        rejection_id = 1

        while True:
            event = await event_queue.get()
            if event.event_type == "assistant_chunk":
                content = event.data.get("content", "") if event.data else ""
                if content:
                    stream_buf.add_chunk(content)
                    await stream_buf.flush_ready(instant=True)
            elif event.event_type == "assistant_stream_end":
                await stream_buf.finish(instant=True)
            elif event.event_type == "assistant_message":
                content = event.data.get("content", "") if event.data else ""
                if content:
                    await print_markdown(content, instant=True)
            elif event.event_type == "tool_call":
                stream_buf.discard()
                tool_name = event.data.get("tool", "") if event.data else ""
                arguments = event.data.get("arguments", {}) if event.data else {}
                if tool_name:
                    last_tool[0] = tool_name
                    print_tool_call(tool_name, json.dumps(arguments)[:80])
            elif event.event_type == "tool_output":
                output = event.data.get("output", "") if event.data else ""
                success = event.data.get("success", False) if event.data else False
                if last_tool[0] == "plan_tool" and output:
                    print_tool_output(output, success, truncate=False)
            elif event.event_type == "tool_log":
                tool = event.data.get("tool", "") if event.data else ""
                log = event.data.get("log", "") if event.data else ""
                if log:
                    print_tool_log(tool, log)
            elif event.event_type == "approval_required":
                tools_data = event.data.get("tools", []) if event.data else []
                approvals = [
                    {
                        "tool_call_id": tool.get("tool_call_id", ""),
                        "approved": False,
                        "feedback": "Detrix MLInternWorker rejects interactive approvals in privacy-safe mode.",
                    }
                    for tool in tools_data
                ]
                rejection_id += 1
                await submission_queue.put(
                    Submission(
                        id=f"detrix_reject_{rejection_id}",
                        operation=Operation(op_type=OpType.EXEC_APPROVAL, data={"approvals": approvals}),
                    )
                )
            elif event.event_type == "error":
                stream_buf.discard()
                print_error(event.data.get("error", "Unknown error") if event.data else "Unknown error")
                return 4
            elif event.event_type in {"turn_complete", "interrupted"}:
                stream_buf.discard()
                print(f"\n--- Agent {event.event_type} ---", file=sys.stderr)
                break

        return 0
    finally:
        await submission_queue.put(Submission(id="detrix_shutdown", operation=Operation(op_type=OpType.SHUTDOWN)))
        try:
            await asyncio.wait_for(agent_task, timeout=10.0)
        except asyncio.TimeoutError:
            agent_task.cancel()
            await tool_router.__aexit__(None, None, None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detrix safe ml-intern headless shim")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-iterations", type=int, required=True)
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    raise SystemExit(asyncio.run(detrix_safe_headless(prompt, args.model, args.max_iterations)))


if __name__ == "__main__":
    main()
'''
