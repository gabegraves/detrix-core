"""CLI entry point for the Detrix workflow engine.

Usage:
    detrix run pipeline.yaml --output-dir /tmp/test --verbose
    detrix history
    detrix inspect <run-id>
    detrix diff <run-a> <run-b>
    detrix export <run-id> -o artifact.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from detrix.core.cache import StepCache
from detrix.core.pipeline import WorkflowEngine, parse_workflow
from detrix.runtime.artifact import RunArtifact
from detrix.runtime.audit import AuditLog
from detrix.runtime.diff import diff_runs


def _default_detrix_dir() -> Path:
    """Return .detrix/ in the current working directory."""
    return Path.cwd() / ".detrix"


@click.group()
@click.option(
    "--data-dir",
    type=click.Path(),
    default=None,
    help="Detrix data directory (default: .detrix/ in cwd)",
)
@click.pass_context
def cli(ctx: click.Context, data_dir: str | None) -> None:
    """Detrix — reproducible, governed AI agent pipelines."""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = Path(data_dir) if data_dir else _default_detrix_dir()


@cli.command()
@click.argument("yaml_path", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default=None, help="Output directory for run artifacts")
@click.option("--no-cache", is_flag=True, help="Disable step caching")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def run(ctx: click.Context, yaml_path: str, output_dir: str | None, no_cache: bool, verbose: bool) -> None:
    """Execute a workflow from a YAML file."""
    data_dir = ctx.obj["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)

    cache = StepCache(str(data_dir / "cache.db")) if not no_cache else None
    audit = AuditLog(str(data_dir / "audit.db"))

    out = Path(output_dir) if output_dir else data_dir / "runs"

    engine = WorkflowEngine(
        cache=cache,
        audit=audit,
        output_dir=str(out),
        verbose=verbose,
    )

    workflow = parse_workflow(yaml_path)

    # Parse any inputs from the YAML metadata or pass empty
    record = engine.run(workflow, inputs={})

    # Summary
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Workflow:  {record.workflow_name} v{record.workflow_version}")
    click.echo(f"Run ID:   {record.run_id}")
    click.echo(f"Status:   {record.status.value.upper()}")
    click.echo(f"Duration: {record.duration_ms:.0f}ms")
    click.echo(f"{'=' * 60}")

    for sr in record.step_results:
        flag = "CACHED" if sr.cached else sr.status.value.upper()
        click.echo(f"  [{flag:8s}] {sr.step_id:20s} {sr.duration_ms:8.0f}ms")
        if sr.error:
            click.echo(f"             ERROR: {sr.error}")

    click.echo()

    # Save artifact
    artifact = RunArtifact.from_run_record(record)
    artifact_dir = data_dir / "artifacts"
    artifact.save(artifact_dir / f"{record.run_id}.json")

    if record.status.value == "failed":
        sys.exit(1)


@cli.command()
@click.option("--limit", "-n", type=int, default=20, help="Number of runs to show")
@click.pass_context
def history(ctx: click.Context, limit: int) -> None:
    """List recent workflow runs."""
    data_dir = ctx.obj["data_dir"]
    audit_path = data_dir / "audit.db"
    if not audit_path.exists():
        click.echo("No audit log found. Run a workflow first.")
        return

    audit = AuditLog(str(audit_path))
    runs = audit.list_runs(limit=limit)

    if not runs:
        click.echo("No runs recorded.")
        return

    click.echo(f"{'RUN ID':<14s} {'WORKFLOW':<20s} {'STATUS':<10s} {'STARTED'}")
    click.echo("-" * 65)
    for r in runs:
        click.echo(
            f"{r['run_id']:<14s} {r['workflow_name']:<20s} "
            f"{r['status']:<10s} {r['started_at']}"
        )


@cli.command()
@click.argument("run_id")
@click.pass_context
def inspect(ctx: click.Context, run_id: str) -> None:
    """Show details for a specific run."""
    data_dir = ctx.obj["data_dir"]

    # Try loading artifact first
    artifact_path = data_dir / "artifacts" / f"{run_id}.json"
    if artifact_path.exists():
        artifact = RunArtifact.load(artifact_path)
        click.echo(artifact.model_dump_json(indent=2))
        return

    # Fall back to audit log
    audit = AuditLog(str(data_dir / "audit.db"))
    run_data = audit.get_run(run_id)
    if not run_data:
        click.echo(f"Run '{run_id}' not found.")
        sys.exit(1)
    click.echo(json.dumps(run_data, indent=2, default=str))


@cli.command()
@click.argument("run_a")
@click.argument("run_b")
@click.pass_context
def diff(ctx: click.Context, run_a: str, run_b: str) -> None:
    """Compare two runs and show what changed."""
    data_dir = ctx.obj["data_dir"]
    artifact_dir = data_dir / "artifacts"

    path_a = artifact_dir / f"{run_a}.json"
    path_b = artifact_dir / f"{run_b}.json"

    if not path_a.exists():
        click.echo(f"Artifact for run '{run_a}' not found at {path_a}")
        sys.exit(1)
    if not path_b.exists():
        click.echo(f"Artifact for run '{run_b}' not found at {path_b}")
        sys.exit(1)

    artifact_a = RunArtifact.load(path_a)
    artifact_b = RunArtifact.load(path_b)

    report = diff_runs(artifact_a, artifact_b)
    click.echo(report.format_text())


@cli.command("export")
@click.argument("run_id")
@click.option("--output", "-o", required=True, help="Output file path")
@click.pass_context
def export_artifact(ctx: click.Context, run_id: str, output: str) -> None:
    """Export a run artifact as portable JSON."""
    data_dir = ctx.obj["data_dir"]
    artifact_path = data_dir / "artifacts" / f"{run_id}.json"

    if not artifact_path.exists():
        click.echo(f"Artifact for run '{run_id}' not found.")
        sys.exit(1)

    artifact = RunArtifact.load(artifact_path)
    out_path = artifact.save(output)
    click.echo(f"Exported to {out_path}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
