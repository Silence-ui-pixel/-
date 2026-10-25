from fastapi import FastAPI

from app.api.v1 import auth, health, inbound_orders, inventory, outbound_orders, skus
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Canku WMS API",
        version="0.1.0",
        description="仓储智能管理 Agent 系统 · 领域与账务服务",
        docs_url="/docs",
        redoc_url=None,
    )

    app.include_router(health.router, prefix=settings.api_prefix, tags=["system"])
    app.include_router(auth.router, prefix=settings.api_prefix, tags=["auth"])
    app.include_router(skus.router, prefix=settings.api_prefix, tags=["sku", "location"])
    app.include_router(inventory.router, prefix=settings.api_prefix, tags=["inventory"])
    app.include_router(
        inbound_orders.router, prefix=settings.api_prefix, tags=["inbound"]
    )
    app.include_router(
        outbound_orders.router, prefix=settings.api_prefix, tags=["outbound"]
    )

    # 后续模块（收货/上架/分配/拣货/发运、agent）按契约逐步挂载。
    # 每个模块的路由必须与 contracts/openapi.yaml 一致，
    # 不允许先写接口后补契约。

    return app


app = create_app()
