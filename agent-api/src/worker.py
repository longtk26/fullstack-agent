import asyncio
import signal
from pathlib import Path

from src.configs import config, setup_logging
from src.orchestrator.bootstrap import build_worker_service


async def run_worker() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    Path(config.workspace_root).mkdir(parents=True, exist_ok=True)
    async with build_worker_service() as service:
        await service.run(stop)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_worker())
