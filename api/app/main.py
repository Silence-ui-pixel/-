from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import auth, health, inbound_orders, inventory, outbound_orders, skus
from app.core.config import settings
from app.core.errors import DomainError


def create_app() -> FastAPI:
    app = FastAPI(
        title="Canku WMS API",
        version="0.1.0",
        description="仓储智能管理 Agent 系统 · 领域与账务服务",
        docs_url="/docs",
        redoc_url=None,
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        """把业务异常转成契约里定义的 Error 结构。

        契约（contracts/openapi.yaml 的 Error schema）：
            { code, message, detail }
        这条处理器是「错误码体系」的落地位置 —— 没有它，库存不足会变成 500，
        前端就只能显示「服务器错误」，而不是「SKU-1001 差 12 件」。
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            },
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

    return app


app = create_app()
