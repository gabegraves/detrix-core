"""Example: wrapping an existing Python function with detrix.

Shows how to use the WorkflowEngine programmatically
to run a simple pipeline without YAML.
"""

from detrix.core import StepCache, WorkflowEngine, WorkflowDef, StepDef


def my_analysis(data: list, threshold: float = 0.5) -> dict:
    """A plain Python function you already have."""
    above = [x for x in data if x > threshold]
    return {
        "count_above": len(above),
        "ratio": len(above) / len(data) if data else 0,
    }


def main() -> None:
    # Create an engine with caching
    engine = WorkflowEngine(
        cache=StepCache(".detrix/cache.db"),
        output_dir=".detrix/runs",
        verbose=True,
    )

    # Register your function
    engine.register("my_analysis", my_analysis)

    # Define a minimal workflow in code
    workflow = WorkflowDef(
        name="quick-analysis",
        version="1.0",
        steps=[
            StepDef(
                id="analyze",
                name="Run Analysis",
                function="my_analysis",
                inputs={"data": "$input.data", "threshold": "$input.threshold"},
            ),
        ],
    )

    # Run it
    record = engine.run(workflow, inputs={
        "data": [0.1, 0.6, 0.3, 0.9, 0.8, 0.2],
        "threshold": 0.5,
    })

    print(f"Status: {record.status.value}")
    print(f"Result: {record.step_results[0].output_data}")


if __name__ == "__main__":
    main()
