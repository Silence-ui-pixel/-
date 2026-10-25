"""主数据读接口：商品 / 库位。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Location, Sku
from app.db.session import get_session
from app.schemas import Location as LocationSchema
from app.schemas import LocationListResponse, PageMeta, SkuListResponse
from app.schemas import Sku as SkuSchema

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/skus", response_model=SkuListResponse, summary="商品分页列表")
async def list_skus(
    keyword: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> SkuListResponse:
    """商品分页。keyword 对 名称/编码/条码 模糊搜。"""
    stmt = select(Sku)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            Sku.name.ilike(like) | Sku.sku_code.ilike(like) | Sku.barcode.ilike(like)
        )
    if category:
        stmt = stmt.where(Sku.category == category)

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (
        await session.execute(
            stmt.order_by(Sku.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()

    return SkuListResponse(
        items=[SkuSchema.model_validate(i) for i in items],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


@router.get("/skus/{sku_id}", response_model=SkuSchema, summary="商品详情")
async def get_sku(sku_id: int, session: AsyncSession = Depends(get_session)) -> SkuSchema:
    sku = await session.get(Sku, sku_id)
    if sku is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return SkuSchema.model_validate(sku)


@router.get("/locations", response_model=LocationListResponse, summary="库位列表")
async def list_locations(
    zone_code: str | None = None,
    location_type: str | None = None,
    status: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> LocationListResponse:
    """库位列表（无分页，库位数量有限）。"""
    stmt = select(Location)
    if zone_code:
        stmt = stmt.where(Location.zone_code == zone_code)
    if location_type:
        stmt = stmt.where(Location.location_type == location_type)
    if status is not None:
        stmt = stmt.where(Location.status == status)

    items = (await session.execute(stmt.order_by(Location.pick_seq, Location.id))).scalars().all()
    return LocationListResponse(items=[LocationSchema.model_validate(i) for i in items])
