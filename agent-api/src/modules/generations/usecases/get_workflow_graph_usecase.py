from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends

from src.orchestrator.graph import describe_graph
from src.orchestrator.state import status_for


@lru_cache
def _graph() -> dict[str, Any]:
    graph = describe_graph()
    for node in graph["nodes"]:
        if not node["id"].startswith("__"):
            node["status"] = status_for(node["id"]).value
    return graph


class GetWorkflowGraphUsecase:
    async def execute(self) -> dict[str, Any]:
        return _graph()


GetWorkflowGraphUsecaseDep = Annotated[GetWorkflowGraphUsecase, Depends(GetWorkflowGraphUsecase)]
