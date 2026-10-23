from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.configs import config, setup_logging
from src.libs.exceptions import BaseException
from src.libs.exceptions.handlers import (
    base_exception_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from src.libs.rate_limit import limiter
from src.routers import all_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for router in all_router:
        app.include_router(router)
    yield


app = FastAPI(title=config.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(BaseException, base_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
