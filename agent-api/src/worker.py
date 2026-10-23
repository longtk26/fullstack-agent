import asyncio
import signal
import time
from pathlib import Path

from src.configs import config, get_logger, setup_logging
from src.engines import EngineHealthStore, get_engine_registry
from src.libs.redis import get_redis

logger = get_logger("src.worker")
ENGINE_HEALTH_INTERVAL_S = 30


async def publish_engine_health(store: EngineHealthStore) -> None:
    try:
        await store.publish(await get_engine_registry().health())
    except Exception:  # health reporting must never take the worker down
        logger.exception("engine health publish failed")


async def run_worker() -> None:
    """Heartbeat + engine health reporting; Epic 4 adds the job queue consumer."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    Path(config.workspace_root).mkdir(parents=True, exist_ok=True)
    heartbeat = Path(config.worker_heartbeat_file)
    store = EngineHealthStore(get_redis())
    last_health = 0.0
    logger.info("worker started", extra={"concurrency": config.worker_concurrency})
    while not stop.is_set():
        heartbeat.touch()
        if time.monotonic() - last_health >= ENGINE_HEALTH_INTERVAL_S:
            await publish_engine_health(store)
            last_health = time.monotonic()
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.worker_heartbeat_seconds)
        except TimeoutError:
            pass
    logger.info("worker stopped")


if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_worker())
