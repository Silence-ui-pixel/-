from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    agent,
    auth,
    health,
    inbound_orders,
    inventory,
    outbound_orders,
    skus,
)
from app.core.config import settings
from app.core.errors import (
    DomainError,
    clean_validation_errors,
    code_for_status,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Canku WMS API",
        version="1.0.0",  # 与 contracts/openapi.yaml 一致，2026-10-25 冻结
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

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """把 Starlette/FastAPI 的内置 HTTPException 也转成契约 Error 结构。

        覆盖 401（鉴权依赖）/ 403（角色不足）/ 404（资源不存在）/
        405 / 503 等所有非业务异常。

        为什么必须做：这些异常原本返回 { "detail": "..." }，前端拿不到 code，
        就只能靠 HTTP 状态码硬编码判断 —— token 过期无法自动跳登录、
        缺货无法弹明细。契约的 Error schema 是所有错误的唯一出口。
        """
        code = code_for_status(exc.status_code)
        raw = exc.detail
        message = str(raw)
        detail: dict = {}

        if isinstance(raw, dict):
            # 允许路由用 HTTPException(409, {"code": ..., "message": ...}) 传结构化信息，
            # 但仍优先保留状态码映射出的 code（避免有人随手写错码）
            message = str(raw.get("message", message))
            if isinstance(raw.get("detail"), dict):
                detail = raw["detail"]

        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": message, "detail": detail},
            # 关键：401 的 WWW-Authenticate 等响应头必须原样带出，
            # 否则客户端无法得知该用哪种认证方式
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """请求体/查询参数校验失败 -> 422 VALIDATION_ERROR。

        detail.errors 保留 Pydantic 的字段级信息（loc/msg/type），
        前端才能标红具体哪个输入框，而不是只显示「参数不合法」。
        """
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "参数不合法",
                "detail": {"errors": clean_validation_errors(exc.errors())},
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
    app.include_router(agent.router, prefix=settings.api_prefix, tags=["agent"])

    return app


app = create_app()
