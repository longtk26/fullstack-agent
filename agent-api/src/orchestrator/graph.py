import asyncio
from typing import Any

from langgraph.graph import END, START, StateGraph

from .context import JobCancelled, JobContext
from .nodes import NODE_FUNCTIONS
from .state import GenerationState

ATTEMPT_NODES = {"run_validation", "repair_code"}


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
        status = summary.pop("_status", "succeeded")
        await ctx.leave_node(name, run_id, status, summary)
        return {**update, "last_commit": sha}

    run.__name__ = name
    return run


def build_graph(ctx: JobContext | None) -> StateGraph:
    graph = StateGraph(GenerationState)
    for name in NODE_FUNCTIONS:
        graph.add_node(name, _node(name, ctx))
    graph.add_edge(START, "validate_spec")
    graph.add_conditional_edges("validate_spec", route_after_spec, {"valid": "plan_architecture", "invalid": END})
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


def describe_graph() -> dict[str, Any]:
    drawable = build_graph(None).compile().get_graph()
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
