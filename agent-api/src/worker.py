import asyncio
import signal
from pathlib import Path

from src.configs import config, get_logger, setup_logging

logger = get_logger("src.worker")


async def run_worker() -> None:
    """Idle loop that keeps a heartbeat file fresh; Epic 4 adds the job queue consumer."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    Path(config.workspace_root).mkdir(parents=True, exist_ok=True)
    heartbeat = Path(config.worker_heartbeat_file)
    logger.info("worker started", extra={"concurrency": config.worker_concurrency})
    while not stop.is_set():
        heartbeat.touch()
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.worker_heartbeat_seconds)
        except TimeoutError:
            pass
    logger.info("worker stopped")


if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_worker())
