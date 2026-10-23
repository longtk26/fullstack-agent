from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.configs import config, get_logger, setup_logging
from src.libs.exceptions import register_exception_handlers
from src.libs.rate_limit import limiter
from src.modules.auth.bootstrap import seed_users
from src.routers import all_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for router in all_router:
        app.include_router(router)
    await seed_users(config.seed_users)
    logger.info("agent api started", extra={"app": config.app_name})
    yield


app = FastAPI(title=config.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
