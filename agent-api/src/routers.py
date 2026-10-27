from src.modules.auth.presenter import auth_router, me_router
from src.modules.engines.presenter import engine_router
from src.modules.generations.presenter import generation_router
from src.modules.health.presenter import health_router
from src.modules.previews.presenter import preview_router, previews_router
from src.modules.specs.presenter import spec_import_router, spec_router
from src.modules.usage.presenter import usage_router

all_router = [
    health_router,
    auth_router,
    me_router,
    spec_router,
    spec_import_router,
    engine_router,
    generation_router,
    preview_router,
    previews_router,
    usage_router,
]
