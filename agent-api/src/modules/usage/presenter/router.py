from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query

from src.modules.auth.presenter import CurrentUserDep
from src.modules.usage.usecases import GetUsageUsecaseDep

usage_router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@usage_router.get("", response_model=dict[str, Any])
async def get_usage(
    user: CurrentUserDep,
    usecase: GetUsageUsecaseDep,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    scope: Annotated[str, Query(pattern="^(mine|all)$")] = "mine",
) -> dict[str, Any]:
    """Time, model calls, tokens and cost of the generations created in [from, to] (default: the last 7 days),
    with breakdowns by day, engine, mode, model, node and lane. `scope=all` (admins) covers every user."""
    return await usecase.execute(user, start, end, all_owners=scope == "all")
