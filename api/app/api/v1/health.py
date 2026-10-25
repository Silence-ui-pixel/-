from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


@router.get("/health", summary="存活探针")
async def health() -> dict:
    """不查库。用于容器 liveness，库挂了也不该重启 API。"""
    return {"status": "ok"}


@router.get("/health/db", summary="就绪探针")
async def health_db(session: AsyncSession = Depends(get_session)) -> dict:
    """真正查一次库。库不可用时返回 503，让编排层知道 API 还不能干活。"""
    try:
        await session.execute(text("select 1"))
    except Exception as exc:  # noqa: BLE001 - 这里就是要兜住任何连接异常
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unavailable: {type(exc).__name__}",
        ) from exc
    return {"status": "ok", "db": "reachable"}
