"""The rate limiter as a plugin (Story 10.1's proof): SlowAPI on every route, as the overlay had it since 5.4."""

from typing import Any

from .base import AppStartup, Plugin, Setting


class RateLimitPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__(name="rate-limit", always=True)

    def settings(self, plan: dict[str, Any] | None) -> list[Setting]:
        return [Setting("rate_limit_default", "str", '"120/minute"', test_value="100000/minute")]

    def app_startup(self, plan: dict[str, Any] | None) -> AppStartup:
        return AppStartup(
            imports=(
                ("slowapi.errors", ("RateLimitExceeded",)),
                ("slowapi.middleware", ("SlowAPIMiddleware",)),
                ("src.libs.rate_limit", ("limiter", "rate_limit_exception_handler")),
            ),
            setup=("app.state.limiter = limiter", "app.add_middleware(SlowAPIMiddleware)"),
            handlers=(("RateLimitExceeded", "rate_limit_exception_handler"),),
        )

    def engine_note(self, plan: dict[str, Any]) -> str:
        return (
            "Rate limiting (`src/libs/rate_limit`): every route is limited per client by SlowAPI middleware; for a "
            'stricter route add `@limiter.limit("5/minute")` (`from src.libs.rate_limit import limiter`) and a '
            "`request: Request` parameter."
        )
