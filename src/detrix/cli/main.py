"""CLI entry point for the Detrix workflow engine.

Usage:
    detrix run pipeline.yaml --output-dir /tmp/test --verbose
    detrix history
    detrix inspect <run-id>
    detrix diff <run-a> <run-b>
    detrix export <run-id> -o artifact.json
    detrix export --format sft --domain xrd -o training.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal, cast

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


@cli.command("show-run")
@click.argument("run_id")
@click.option("--db", default=None, help="Path to evidence.db (default: DATA_DIR/evidence.db)")
@click.pass_context
def show_run(ctx: click.Context, run_id: str, db: str | None) -> None:
    """Show a governed run with gate verdicts and training eligibility."""
    data_dir = ctx.obj["data_dir"]
    audit = AuditLog(str(data_dir / "audit.db"))
    run_data = audit.get_run(run_id)
    if not run_data:
        click.echo(f"Run '{run_id}' not found.")
        sys.exit(1)

    from detrix.runtime.trajectory_store import TrajectoryStore

    evidence_db = db or str(data_dir / "evidence.db")
    trajectories = TrajectoryStore(evidence_db).list_by_run(run_id)
    _print_governed_run(run_data, trajectories)


@cli.command("demo-yc")
@click.option("--output-dir", "-o", default=None, help="Directory for demo artifacts")
@click.option("--domain", default="support_triage", help="Demo trajectory domain")
@click.option(
    "--mode",
    type=click.Choice(["sampled", "deterministic"]),
    default="sampled",
    show_default=True,
    help="Agent output mode. sampled varies support responses; deterministic is for tests.",
)
@click.option("--seed", type=int, default=None, help="Seed sampled mode for a repeatable demo run")
@click.option("--sample-count", type=int, default=8, show_default=True, help="Number of sampled agent outputs")
@click.pass_context
def demo_yc(
    ctx: click.Context,
    output_dir: str | None,
    domain: str,
    mode: Literal["sampled", "deterministic"],
    seed: int | None,
    sample_count: int,
) -> None:
    """Run the YC governance demo end-to-end."""
    from detrix.adapters.axv2 import project_to_audit_log, run_artifact_to_trajectories
    from detrix.demo.support_triage import build_demo_artifact
    from detrix.improvement.exporter import TrainingExporter
    from detrix.runtime.trajectory_store import TrajectoryStore

    data_dir = ctx.obj["data_dir"]
    data_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = Path(output_dir) if output_dir else data_dir / "demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    artifact = build_demo_artifact(mode=mode, seed=seed, sample_count=sample_count)
    run_id = str(artifact["run_id"])
    audit = AuditLog(str(data_dir / "audit.db"))
    store = TrajectoryStore(str(data_dir / "evidence.db"))

    project_to_audit_log(artifact, audit)
    trajectories = run_artifact_to_trajectories(artifact, domain=domain)
    for trajectory in trajectories:
        store.append(trajectory)

    artifact_path = artifact_dir / f"{run_id}.governance.json"
    artifact_path.write_text(json.dumps(artifact, indent=2, default=str) + "\n", encoding="utf-8")

    exporter = TrainingExporter(store)
    sft_path = exporter.export_sft(str(artifact_dir / f"{run_id}.sft.jsonl"), domain=domain)
    dpo_path = exporter.export_dpo(str(artifact_dir / f"{run_id}.dpo.jsonl"), domain=domain)
    grpo_path = exporter.export_grpo(str(artifact_dir / f"{run_id}.grpo.jsonl"), domain=domain)

    click.echo("Detrix YC demo: autonomous agent output -> post-hoc gates -> training signal")
    click.echo(f"Run ID: {run_id}")
    click.echo(f"Agent mode: {artifact.get('agent_mode', mode)}")
    click.echo(f"Artifact: {artifact_path}")
    click.echo(f"SFT export: {sft_path} ({_line_count(sft_path)} rows)")
    click.echo(f"DPO export: {dpo_path} ({_line_count(dpo_path)} rows)")
    click.echo(f"GRPO export: {grpo_path} ({_line_count(grpo_path)} rows)")
    click.echo()

    run_data = audit.get_run(run_id)
    if run_data is None:
        raise click.ClickException(f"Run '{run_id}' was not persisted")
    _print_governed_run(run_data, trajectories)

    rejected = [trajectory for trajectory in trajectories if trajectory.rejection_type is not None]
    if rejected:
        click.echo()
        click.echo("SFT guard:")
        for trajectory in rejected:
            try:
                trajectory.to_sft_row()
            except ValueError as exc:
                click.echo(f"  blocked {trajectory.trajectory_id}: {exc}")


@cli.group("agentxrd")
def agentxrd() -> None:
    """AgentXRD-specific governance harness commands."""


@agentxrd.command("build-harness-evidence")
@click.option("--binary20-artifact", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--row-packets", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--trace-packet-map", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--router-decisions", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--router-summary", type=click.Path(exists=True, path_type=Path), required=True)
@click.option(
    "--mission-control-db",
    type=click.Path(exists=True, path_type=Path),
    default=Path("/home/gabriel/.mission-control/data.db"),
    show_default=True,
)
@click.option("--langfuse-project", default="AgentXRD_v2", show_default=True)
@click.option("--output-dir", type=click.Path(path_type=Path), required=True)
def agentxrd_build_harness_evidence(
    binary20_artifact: Path,
    row_packets: Path,
    trace_packet_map: Path,
    router_decisions: Path,
    router_summary: Path,
    mission_control_db: Path,
    langfuse_project: str,
    output_dir: Path,
) -> None:
    """Build AgentXRD failure-governance harness evidence artifacts."""
    summary = _build_agentxrd_harness_evidence(
        binary20_artifact=binary20_artifact,
        row_packets=row_packets,
        trace_packet_map=trace_packet_map,
        router_decisions=router_decisions,
        router_summary=router_summary,
        mission_control_db=mission_control_db,
        langfuse_project=langfuse_project,
        output_dir=output_dir,
    )
    click.echo(f"Wrote AgentXRD harness evidence to {output_dir}")
    click.echo(
        "Rows: "
        f"{summary['row_count']}; "
        f"Langfuse observations: {summary['langfuse_observation_count']}; "
        f"promotion: {summary['promotion_packet']['promote']}"
    )


def _build_agentxrd_harness_evidence(
    *,
    binary20_artifact: Path,
    row_packets: Path,
    trace_packet_map: Path,
    router_decisions: Path,
    router_summary: Path,
    mission_control_db: Path,
    langfuse_project: str,
    output_dir: Path,
) -> dict[str, Any]:
    from detrix.agentxrd.drift_replay import run_drift_replay
    from detrix.agentxrd.failure_patterns import build_failure_pattern_corpus
    from detrix.agentxrd.langfuse_importer import (
        MissionControlLangfuseSource,
        import_agentxrd_langfuse_traces,
    )
    from detrix.agentxrd.next_actions import build_governed_next_actions
    from detrix.agentxrd.promotion_packet import (
        AgentXRDPromotionMetrics,
        build_promotion_packet,
    )
    from detrix.agentxrd.provenance import build_agentxrd_provenance_dag

    output_dir.mkdir(parents=True, exist_ok=True)
    import_agentxrd_langfuse_traces(
        source=MissionControlLangfuseSource(
            db_path=mission_control_db,
            live_enabled=False,
        ),
        project=langfuse_project,
        output_dir=output_dir,
    )
    summary = build_failure_pattern_corpus(
        binary20_artifact=binary20_artifact,
        row_packets=row_packets,
        trace_packet_map=trace_packet_map,
        router_decisions=router_decisions,
        router_summary=router_summary,
        normalized_observations=output_dir / "normalized_observations.jsonl",
        output_dir=output_dir,
    )
    (output_dir / "trace_to_agentxrd_packet_map.jsonl").write_text(
        trace_packet_map.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    build_governed_next_actions(
        output_dir / "failure_patterns.jsonl",
        output_dir / "governed_next_actions.jsonl",
    )
    build_agentxrd_provenance_dag(
        detrix_artifact=binary20_artifact,
        trace_packet_map=trace_packet_map,
        row_packets=row_packets,
        output_path=output_dir / "provenance_dag.jsonl",
    )
    router = json.loads(router_summary.read_text(encoding="utf-8"))
    pattern_rows = [
        json.loads(line)
        for line in (output_dir / "failure_patterns.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    packet = build_promotion_packet(
        AgentXRDPromotionMetrics(
            row_count=summary.row_count,
            wrong_accept_count=int(router.get("wrong_accept_count", 0)),
            support_only_accept_violation_count=int(
                router.get("support_only_accept_violation_count", 0)
            ),
            accept_ineligible_accept_violation_count=int(
                router.get("accept_ineligible_accept_violation_count", 0)
            ),
            truth_blocked_positive_count=sum(
                1
                for row in pattern_rows
                if row.get("deterministic_export_label") == "sft_positive"
                and row.get("truth_flags", {}).get("truth_blocked") is True
            ),
            provisional_positive_count=sum(
                1
                for row in pattern_rows
                if row.get("deterministic_export_label") == "sft_positive"
                and row.get("truth_flags", {}).get("provisional") is True
            ),
            sft_positive_count=summary.sft_positive_count,
        )
    )
    (output_dir / "promotion_packet.json").write_text(
        packet.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    drift = run_drift_replay(
        binary20_artifact=binary20_artifact,
        router_summary=router_summary,
        output_path=output_dir / "drift_replay_report.json",
        proposed_metrics={"sft_positive_count": summary.sft_positive_count},
    )
    return {
        **summary.model_dump(),
        "promotion_packet": packet.model_dump(),
        "drift_replay": drift.model_dump(),
    }


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
@click.argument("run_id", required=False)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["sft", "grpo", "dpo"]),
    default=None,
    help="Training export format.",
)
@click.option("--domain", default=None, help="Filter training export by domain.")
@click.option("--min-score", default=None, type=float, help="Minimum governance score.")
@click.option("--db", default=".detrix/evidence.db", help="Path to evidence.db")
@click.option("--output", "-o", required=True, help="Output file path")
@click.pass_context
def export_artifact(
    ctx: click.Context,
    run_id: str | None,
    fmt: str | None,
    domain: str | None,
    min_score: float | None,
    db: str,
    output: str,
) -> None:
    """Export a run artifact or governed trajectories as training data."""
    if fmt is not None:
        from detrix.improvement.exporter import TrainingExporter
        from detrix.runtime.trajectory_store import TrajectoryStore

        store = TrajectoryStore(db)
        exporter = TrainingExporter(store)

        if fmt == "sft":
            path = exporter.export_sft(output, domain=domain, min_score=min_score)
        elif fmt == "grpo":
            path = exporter.export_grpo(output, domain=domain, min_score=min_score)
        elif fmt == "dpo":
            path = exporter.export_dpo(output, domain=domain)
        else:
            raise click.BadParameter(f"Unknown format: {fmt}")

        with open(path, encoding="utf-8") as file:
            count = sum(1 for _ in file)
        click.echo(f"Exported {count} rows to {path}")
        return

    if run_id is None:
        raise click.UsageError("Missing argument 'RUN_ID' unless --format is provided.")

    data_dir = ctx.obj["data_dir"]
    artifact_path = data_dir / "artifacts" / f"{run_id}.json"

    if not artifact_path.exists():
        click.echo(f"Artifact for run '{run_id}' not found.")
        sys.exit(1)

    artifact = RunArtifact.load(artifact_path)
    out_path = artifact.save(output)
    click.echo(f"Exported to {out_path}")


def _print_governed_run(run_data: dict[str, Any], trajectories: list[Any]) -> None:
    click.echo(f"Workflow: {run_data['workflow_name']} v{run_data['workflow_version']}")
    click.echo(f"Status:   {str(run_data['status']).upper()}")
    click.echo("Gate verdicts:")
    for step in run_data.get("steps", []):
        if step.get("gate_decision") is None:
            continue
        verdict = json.loads(step["gate_verdict_json"])
        reasons = ",".join(verdict.get("reason_codes", [])) or "-"
        evidence = verdict.get("evidence", {})
        click.echo(
            f"  {step['gate_id']:<22s} {step['gate_decision']:<18s} "
            f"reasons={reasons} evidence={json.dumps(evidence, sort_keys=True)}"
        )

    click.echo("Terminal routes:")
    for trajectory in trajectories:
        completion = json.loads(trajectory.completion)
        terminal = completion.get("terminal") or {}
        route = terminal.get("verdict", "ACCEPT")
        eligibility = terminal.get("training_eligibility", {})
        click.echo(
            f"  {trajectory.trajectory_id:<24s} route={route:<17s} "
            f"rejection_type={trajectory.rejection_type or '-':<14s} "
            f"training={json.dumps(eligibility, sort_keys=True)}"
        )


def _line_count(path: str) -> int:
    with open(path, encoding="utf-8") as file:
        return sum(1 for _ in file)


@cli.command("train")
@click.option("--backend", type=click.Choice(["sft", "grpo"]), default="sft", help="Training backend")
@click.option("--model", "model_name", required=True, help="Model name or local path")
@click.option("--domain", default=None, help="Filter trajectories by domain")
@click.option("--min-score", default=None, type=float, help="Minimum governance score")
@click.option("--limit", default=None, type=int, help="Maximum trajectories to load (default: all)")
@click.option("--max-steps", default=100, type=int, help="Max training steps")
@click.option("--lora-r", default=16, type=int, help="LoRA rank")
@click.option("--learning-rate", default=2e-4, type=float, help="Learning rate")
@click.option("--load-in-4bit", is_flag=True, help="Use 4-bit quantization")
@click.option("--cuda-devices", default=None, help="CUDA_VISIBLE_DEVICES override")
@click.option("--output-dir", default=".detrix/adapters", help="Adapter output directory")
@click.option("--db", default=".detrix/evidence.db", help="Path to evidence.db")
def train(
    backend: str,
    model_name: str,
    domain: str | None,
    min_score: float | None,
    limit: int | None,
    max_steps: int,
    lora_r: int,
    learning_rate: float,
    load_in_4bit: bool,
    cuda_devices: str | None,
    output_dir: str,
    db: str,
) -> None:
    """Train a LoRA adapter from governed trajectories."""
    from detrix.improvement.training_config import TrainingConfig

    config = TrainingConfig(
        model_name=model_name,
        backend=cast(Literal["sft", "grpo"], backend),
        evidence_db=db,
        domain=domain,
        min_score=min_score,
        limit=limit,
        max_steps=max_steps,
        lora_r=lora_r,
        learning_rate=learning_rate,
        load_in_4bit=load_in_4bit,
        cuda_devices=cuda_devices,
        output_dir=output_dir,
    )

    click.echo("Training config:")
    click.echo(f"  Backend:  {config.backend}")
    click.echo(f"  Model:    {config.model_name}")
    click.echo(f"  Domain:   {config.domain or 'all'}")
    click.echo(f"  Limit:    {config.limit or 'all'}")
    click.echo(f"  Steps:    {config.max_steps}")
    click.echo(f"  LoRA r:   {config.lora_r}")
    click.echo(f"  GPU:      {config.cuda_devices or 'auto'}")
    click.echo()

    if backend == "sft":
        from detrix.improvement.sft_trainer import DetrixSFTTrainer

        trainer = DetrixSFTTrainer(config)
        dataset = trainer.load_dataset()
        click.echo(f"Loaded {len(dataset)} training examples")
        result = trainer.train()
    else:
        from detrix.improvement.grpo_trainer import DetrixGRPOTrainer

        trainer_grpo = DetrixGRPOTrainer(config)
        groups = trainer_grpo.load_trajectory_groups()
        click.echo(f"Loaded {len(groups)} trajectory groups")
        result = trainer_grpo.train()

    click.echo(f"\n{'=' * 60}")
    click.echo(f"Training complete ({result.backend})")
    click.echo(f"  Adapter:  {result.adapter_path}")
    click.echo(f"  Examples: {result.num_examples}")
    click.echo(f"  Steps:    {result.num_steps}")
    click.echo(f"  Loss:     {result.final_loss:.4f}")
    click.echo(f"{'=' * 60}")


@cli.command("autoresearch")
@click.option("--backend", type=click.Choice(["sft", "grpo"]), default="sft")
@click.option("--model", "model_name", required=True, help="Model name or local path")
@click.option("--domain", default=None, help="Filter trajectories by domain")
@click.option("--limit", default=None, type=int, help="Maximum trajectories to load (default: all)")
@click.option("--max-experiments", default=50, type=int, help="Number of experiments")
@click.option("--max-steps", default=50, type=int, help="Training steps per experiment")
@click.option("--cuda-devices", default=None, help="CUDA_VISIBLE_DEVICES")
@click.option("--db", default=".detrix/evidence.db", help="Path to evidence.db")
@click.option("--seed", default=42, type=int, help="Random seed")
def autoresearch(
    backend: str,
    model_name: str,
    domain: str | None,
    limit: int | None,
    max_experiments: int,
    max_steps: int,
    cuda_devices: str | None,
    db: str,
    seed: int,
) -> None:
    """Run hyperparameter autoresearch: vary, train, keep best adapter."""
    from detrix.improvement.autoresearch import AutoresearchLoop
    from detrix.improvement.training_config import TrainingConfig

    config = TrainingConfig(
        model_name=model_name,
        backend=cast(Literal["sft", "grpo"], backend),
        evidence_db=db,
        domain=domain,
        limit=limit,
        max_steps=max_steps,
        cuda_devices=cuda_devices,
    )
    click.echo(f"Autoresearch: {max_experiments} experiments, {max_steps} steps each")
    click.echo(f"  Model: {model_name}")
    click.echo(f"  Backend: {backend}")
    click.echo(f"  Limit: {limit or 'all'}")
    click.echo(f"  GPU: {cuda_devices or 'auto'}")
    click.echo()

    loop = AutoresearchLoop(config, max_experiments=max_experiments, seed=seed)
    best = loop.run()
    click.echo(f"\nBest: experiment {best.experiment_num}, metric={best.metric:.4f}")
    click.echo(f"Adapter: {best.adapter_path}")
    click.echo(f"Report: {config.output_dir}/autoresearch_report.json")


@cli.command("triage")
@click.argument("traces_path", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output markdown file path")
@click.option("--title", default="Detrix Trace Triage Report", help="Report title")
@click.option("--min-confidence", default=0.75, type=float, help="Confidence threshold")
def triage(traces_path: str, output: str | None, title: str, min_confidence: float) -> None:
    """Score traces and generate a Trace Triage Report.

    Reads JSONL traces, runs governance gates, classifies each trace
    by deployment reliability and training eligibility, and produces
    a markdown report.
    """
    from detrix.triage.report import run_triage

    config = {"min_confidence": min_confidence}
    out_path = Path(output) if output else None

    report = run_triage(
        traces_path=Path(traces_path),
        output_path=out_path,
        config=config,
        title=title,
    )

    if out_path:
        click.echo(f"Report written to {out_path}")
    else:
        click.echo(report)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
