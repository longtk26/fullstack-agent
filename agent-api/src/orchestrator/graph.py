import asyncio
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.modules.shared.domain.enums import GenerationMode

from . import tracing
from .context import JobCancelled, JobContext
from .nodes import NODE_FUNCTIONS
from .state import MODE_NODES, GenerationState

ATTEMPT_NODES = {"run_validation", "repair_code"}
# State that goes into a node span: identifiers and refs only (Story 8.1); files stay in the workspace.
TRACED_STATE = (
    "spec_ref",
    "frontend_ref",
    "contract_ref",
    "plan_ref",
    "repair_attempts",
    "failed_checks",
    "implicated_files",
    "validation",
)


def route_after_spec(state: GenerationState) -> str:
    return "valid" if state.get("spec_valid") else "invalid"


def route_after_validation(state: GenerationState) -> str:
    if not state.get("failed_checks"):
        return "passed"
    if state.get("repair_attempts", 0) < state["max_repair_attempts"]:
        return "failed"
    return "repair limit reached"


def _node(name: str, ctx: JobContext | None):
    fn = NODE_FUNCTIONS[name]

    async def run(state: GenerationState) -> dict[str, Any]:
        attempt = state.get("repair_attempts", 0) + 1 if name in ATTEMPT_NODES else 1
        span_name = f"{name}#{attempt}" if name in ATTEMPT_NODES else name
        refs = {key: state.get(key) for key in TRACED_STATE if state.get(key) is not None}
        with tracing.span(
            span_name, inputs={"attempt": attempt, **refs}, metadata={"node": name, "attempt": attempt}
        ) as span:
            run_id = await ctx.enter_node(name, attempt)
            try:
                update, summary = await fn(state, ctx)
            except JobCancelled:
                await ctx.leave_node(name, run_id, "cancelled", {})
                raise
            except asyncio.CancelledError:
                if ctx.cancel_requested.is_set():
                    await asyncio.shield(ctx.leave_node(name, run_id, "cancelled", {}))
                raise
            except Exception as exc:
                await ctx.leave_node(name, run_id, "failed", {"error": str(exc)[:500]})
                raise
            # The commit is the recovery point: a resumed job resets the project to it.
            sha = ctx.workspaces.commit(ctx.workspace, f"node:{name} attempt:{attempt}")
            ctx.workspaces.check_size(ctx.workspace)
            if name == "repair_code":
                summary["diffStats"] = ctx.workspaces.head_stats(ctx.workspace)
            status = summary.pop("_status", "succeeded")
            await ctx.leave_node(name, run_id, status, summary)
            span.end(outputs={"status": status, **summary}, error=f"{name} {status}" if status == "failed" else None)
            return {**update, "last_commit": sha}

    run.__name__ = name
    return run


def build_graph(ctx: JobContext | None, mode: GenerationMode = GenerationMode.BACKEND) -> StateGraph:
    """backend: today's graph. dynamic: both specs + consistency (validate_inputs) → contract → the backend lane.
    static: validate_inputs → package (the frontend lane arrives with Epic 13). Story 14.1 runs the lanes in
    parallel."""
    graph = StateGraph(GenerationState)
    for name in MODE_NODES[mode]:
        graph.add_node(name, _node(name, ctx))
    if mode == GenerationMode.BACKEND:
        graph.add_edge(START, "validate_spec")
        graph.add_conditional_edges("validate_spec", route_after_spec, {"valid": "plan_architecture", "invalid": END})
    else:
        graph.add_edge(START, "validate_inputs")
        after_inputs = "build_contract" if mode == GenerationMode.DYNAMIC else "package_artifacts"
        graph.add_conditional_edges("validate_inputs", route_after_spec, {"valid": after_inputs, "invalid": END})
    if mode == GenerationMode.STATIC:
        graph.add_edge("package_artifacts", END)
        return graph
    if mode == GenerationMode.DYNAMIC:
        graph.add_edge("build_contract", "plan_architecture")
    graph.add_edge("plan_architecture", "generate_database")
    graph.add_edge("generate_database", "generate_backend")
    graph.add_edge("generate_backend", "generate_tests")
    graph.add_edge("generate_tests", "run_validation")
    graph.add_conditional_edges(
        "run_validation",
        route_after_validation,
        {"passed": "package_artifacts", "failed": "repair_code", "repair limit reached": END},
    )
    graph.add_edge("repair_code", "run_validation")
    graph.add_edge("package_artifacts", END)
    return graph


def describe_graph(mode: GenerationMode = GenerationMode.BACKEND) -> dict[str, Any]:
    drawable = build_graph(None, mode).compile().get_graph()
    nodes = [{"id": node_id, "label": node_id.strip("_")} for node_id in drawable.nodes]
    edges = [
        {
            "source": edge.source,
            "target": edge.target,
            "conditional": edge.conditional,
            "label": edge.data if isinstance(edge.data, str) else None,
        }
        for edge in drawable.edges
    ]
    return {"nodes": nodes, "edges": edges}
