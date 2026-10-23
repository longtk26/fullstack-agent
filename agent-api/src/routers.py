from src.modules.auth.presenter import auth_router, me_router
from src.modules.health.presenter import health_router

all_router = [health_router, auth_router, me_router]
