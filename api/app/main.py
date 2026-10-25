from fastapi import FastAPI

from app.api.v1 import health
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

    # 业务路由按模块挂载（Sprint 1 后续），示例：
    #   app.include_router(sku.router, prefix=f"{settings.api_prefix}/skus")
    #   app.include_router(
    #       inventory.router, prefix=f"{settings.api_prefix}/inventory"
    #   )
    # 每个模块的路由必须与 contracts/openapi.yaml 一致，
    # 不允许先写接口后补契约。

    return app


app = create_app()
