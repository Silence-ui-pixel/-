"""分配策略：按 FEFO（先到期先出）为一条出库明细挑库存维度。

为什么 FEFO 而不是 FIFO：
    仓库里最贵的成本是「过期货」。按效期先后出，能最大限度把临期货先消耗掉。
    不按入库先后 —— 那样会让早入库的常规货一直压着，临期货反而烂在库里。

Sprint 1 的明确简化（必须知道，否则会误解系统行为）：
    一条出库明细只分配一个批次 + 一个库位。
    原因是 order_line 只有一组 (from_location_id, batch_no, expiry_date)，
    表达不了「跨批次分配」。跨批次需要独立的分货明细表（allocation），
    属 Sprint 2 范围。
    所以：单批次不够时明确报 409，而不是静默少分配一半 ——
    静默少分配会让订单看起来成功了，实际发不出货，是更坏的失败方式。
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Inventory, Location


@dataclass
class FefoResult:
    """FEFO 查找结果。

    inv/location 为 None 表示「单批次可用量不足」，此时 max_available 给出
    全仓单批次最大可用量，供上层拼 409 的 detail（前端可据此提示拆单）。
    """

    inv: Inventory | None
    location: Location | None
    max_available: float

    @property
    def ok(self) -> bool:
        return self.inv is not None


async def find_fefo_allocation(
    session: AsyncSession, *, sku_id: int, qty_required: float
) -> FefoResult:
    """按 FEFO 找一条能覆盖 qty_required 的库存维度。

    只看 STORAGE 位的货 —— RECEIVING（待上架）和 STAGING（待发运）的货
    不能被新订单分配走，否则会把已经属于别的单的货重复占掉。

    FEFO 之外还有一条硬约束：**过期批次不参与分配**。
    FEFO 的目标是「减少过期损失」，若把已过期的批次也发出去，就完全背离了
    设计意图，还会让客户收到过期商品。所以这里用 `expiry_date >= current_date`
    排除过期批次（哨兵 9999-12-30 永远满足，非批次商品不受影响）。
    """
    stmt = (
        select(Inventory, Location)
        .join(Location, Inventory.location_id == Location.id)
        .where(
            Inventory.sku_id == sku_id,
            Inventory.qty_available > 0,
            Inventory.expiry_date >= func.current_date(),
            Location.location_type == "STORAGE",
            Location.status == 1,
        )
        # FEFO：效期早的先出。哨兵 9999-12-30 是最大值，自然排在最后
        .order_by(
            Inventory.expiry_date.asc(),
            Location.pick_seq.asc().nulls_last(),
            Inventory.id.asc(),
        )
    )
    rows = (await session.execute(stmt)).all()

    if not rows:
        return FefoResult(inv=None, location=None, max_available=0.0)

    for inv, loc in rows:
        if float(inv.qty_available) >= qty_required:
            return FefoResult(
                inv=inv, location=loc, max_available=float(inv.qty_available)
            )

    # 没有单条能满足：返回最大可用量，让上层报 409 并提示拆分
    best_inv, _best_loc = max(rows, key=lambda r: float(r[0].qty_available))
    return FefoResult(
        inv=None, location=None, max_available=float(best_inv.qty_available)
    )
