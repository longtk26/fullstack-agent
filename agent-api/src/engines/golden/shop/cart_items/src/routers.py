from src.modules.cart_items.presenter import cart_item_router
from src.modules.categories.presenter import category_router
from src.modules.health.presenter import health_router
from src.modules.products.presenter import product_router

all_router = [health_router, category_router, product_router, cart_item_router]
