"""商品主数据：查询 / 新建 / 修改，以及库位查询。

商品写操作的审计说明（重要，不是遗漏）：
    当前 8 张表里没有审计表，stock_txn 只记库存变动、不适合记主数据变更。
    因此这里用结构化日志记录「谁、改了什么、改前改后」，正式审计表属 Sprint 2。
    不假装有审计 —— 写日志比什么都不做诚实，比假装有审计更安全。
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound
from app.core.security import get_current_user
from app.db.models import Inventory, Location, Sku
from app.db.session import get_session
from app.schemas import (
    Location as LocationSchema,
)
from app.schemas import (
    LocationListResponse,
    PageMeta,
    SkuCreate,
    SkuListResponse,
    SkuUpdate,
)
from app.schemas import (
    Sku as SkuSchema,
)

logger = logging.getLogger(__name__)

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
        raise NotFound("商品不存在", detail={"sku_id": sku_id})
    return SkuSchema.model_validate(sku)


@router.post("/skus", response_model=SkuSchema, status_code=201, summary="新建商品")
async def create_sku(
    body: SkuCreate,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SkuSchema:
    """新建商品。

    sku_code 是业务主键（单据明细、库存维度都靠它定位货），必须唯一。
    先查再插而不是直接依赖数据库唯一约束报错，是为了返回明确的 409 +
    SKU_CODE_EXISTS，而不是把 IntegrityError 抛成 500。
    """
    exists = (
        await session.execute(select(Sku.id).where(Sku.sku_code == body.sku_code))
    ).scalar_one_or_none()
    if exists is not None:
        raise Conflict(
            code="SKU_CODE_EXISTS",
            message="商品编码已存在",
            detail={"sku_code": body.sku_code},
        )

    sku = Sku(**body.model_dump())
    session.add(sku)
    await session.commit()
    await session.refresh(sku)

    logger.info(
        "sku.created by=%s sku_id=%s sku_code=%s name=%s",
        current["username"],
        sku.id,
        sku.sku_code,
        sku.name,
    )
    return SkuSchema.model_validate(sku)


@router.put("/skus/{sku_id}", response_model=SkuSchema, summary="修改商品")
async def update_sku(
    sku_id: int,
    body: SkuUpdate,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SkuSchema:
    """修改商品。

    只更新客户端明确提供的字段（exclude_unset），所以传 null 可以清空可空字段，
    不传则保持原值 —— 这两者在业务上完全不同。

    一条业务保护：已有库存的商品不允许把 is_batch_managed 从 false 改成 true。
    因为历史库存没有批次号，改了之后「批次管理商品」的库存却没有批次，
    批次追溯会直接断链，后续发货也无从选批次。要改必须先清空库存或做数据修复。
    """
    sku = await session.get(Sku, sku_id)
    if sku is None:
        raise NotFound("商品不存在", detail={"sku_id": sku_id})

    data = body.model_dump(exclude_unset=True)

    if data.get("is_batch_managed") is True and not sku.is_batch_managed:
        on_hand = (
            await session.execute(
                select(func.coalesce(func.sum(Inventory.qty_on_hand), 0)).where(
                    Inventory.sku_id == sku_id
                )
            )
        ).scalar_one()
        if float(on_hand) > 0:
            raise Conflict(
                code="SKU_BATCH_FLAG_CONFLICT",
                message="该商品已有库存，不能改为批次管理（历史库存无批次号）",
                detail={"sku_id": sku_id, "qty_on_hand": float(on_hand)},
            )

    before = {k: getattr(sku, k) for k in data}
    for key, value in data.items():
        setattr(sku, key, value)

    await session.commit()
    await session.refresh(sku)

    logger.info(
        "sku.updated by=%s sku_id=%s fields=%s before=%s after=%s",
        current["username"],
        sku.id,
        sorted(data),
        {k: str(v) for k, v in before.items()},
        {k: str(getattr(sku, k)) for k in data},
    )
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
