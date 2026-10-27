from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends

from src.modules.shared.domain.enums import GenerationMode
from src.orchestrator.graph import describe_graph
from src.orchestrator.state import NODE_LANE, status_for


@lru_cache
def _graph(mode: GenerationMode) -> dict[str, Any]:
    graph = describe_graph(mode)
    for node in graph["nodes"]:
        if not node["id"].startswith("__"):
            node["status"] = status_for(node["id"]).value
            lane = NODE_LANE.get(node["id"])
            node["lane"] = lane.value if lane else None
    return {"mode": mode.value, **graph}


class GetWorkflowGraphUsecase:
    async def execute(self, mode: GenerationMode = GenerationMode.BACKEND) -> dict[str, Any]:
        return _graph(mode)


GetWorkflowGraphUsecaseDep = Annotated[GetWorkflowGraphUsecase, Depends(GetWorkflowGraphUsecase)]
