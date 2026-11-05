from slowapi import Limiter
from slowapi.util import get_remote_address

from src.configs import config

# Applied to every route by SlowAPIMiddleware (src/main.py); use @limiter.limit("5/minute") for stricter routes.
limiter = Limiter(key_func=get_remote_address, default_limits=[config.rate_limit_default])
