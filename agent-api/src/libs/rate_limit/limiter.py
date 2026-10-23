from slowapi import Limiter
from slowapi.util import get_remote_address

from src.configs import config

limiter = Limiter(key_func=get_remote_address, storage_uri=config.rate_limit_storage_uri)
