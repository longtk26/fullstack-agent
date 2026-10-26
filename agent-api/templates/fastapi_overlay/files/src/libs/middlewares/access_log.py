import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.configs import get_logger

logger = get_logger("access")
SKIP_PATHS = {"/health"}


class AccessLogMiddleware:
    """One structured line per HTTP request: method, path, matched route and operationId, status, duration.
    Query strings and bodies are never logged."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in SKIP_PATHS:
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get("route")
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "route": getattr(route, "path", None),
                    "operationId": getattr(route, "operation_id", None),
                    "status": status,
                    "durationMs": round((time.perf_counter() - started) * 1000, 1),
                },
            )
