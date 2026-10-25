"""AI Agent 接口 —— Sprint 1 只占位（501），P2 实现。

为什么现在就建这个文件、而不是等 P2 再建：
    1. 契约里已经有这三条路径，前后端都已经按它生成类型、接好了调用点。
       如果后端返回 404，前端只能显示「接口不存在」，和「功能还在做」混在一起，
       排查时会浪费大量时间。501 是准确的语义。
    2. 把治理设计提前落到代码结构里，避免 P2 仓促实现时漏掉红线。

=====================================================================
P2 实现必须遵守的五条红线（每条都标了「强制点」= 哪一层真的拦得住）
=====================================================================

约束写在注释里等于没有约束 —— 谁都可以不遵守，而且不会报错。
所以下面每一条都对应一个物理强制点，接手者若想绕过，得先改掉那处。

1. **AI 永不直接写库存**
   强制点：`stock_service.apply_txn` 是唯一写入口，本模块不 import 它；
           且 AI 使用只读 DB 角色（GRANT SELECT only），写操作在数据库层报错。

2. **AI 的产出只能是「建议」，不是「单据」**
   强制点：AI 只能写 `agent_suggestion` 表，`status` 默认 PENDING；
           没有任何代码路径能从本模块创建 inbound_order/outbound_order。

3. **审批必须由人触发，且能证明是人**
   强制点：approve 请求若带 `X-Agent-Run-Id` → 403 AGENT_WRITE_FORBIDDEN；
           只有 MANAGER/ADMIN 可审批；`approved_by` 数据库层 not null。

4. **每次 AI 调用必须完整留痕，能回放**
   强制点：`agent_run` 表记录 prompt/模型/工具调用/token；
           库存变动通过 `stock_txn.agent_run_id` 与本次会话串起来
           （该字段 Sprint 1 已预留，P2 不需要改 stock_txn）。

5. **AI 生成的 SQL 必须过白名单，绝不直接执行**
   强制点：sqlglot 解析 → 只允许单条 SELECT + 表白名单 + 强制 LIMIT；
           再由只读 DB 角色兜底（详见设计文档第五节的三层防护）。

这是「智能与操作权限分离」在接口层的体现 —— 见架构文档 L2 层说明。

完整设计（含 2 张新表 DDL、SQL 白名单实现、9 条攻击用例、验收标准）：
    A_project/drafts/P2-AI治理设计与启动准备.md
施工前必须先确认的 3 件事也在那份文档第八节（模型选型 / 表白名单 / 审批人角色）。
"""

from fastapi import APIRouter, Depends, Header

from app.core.errors import NotImplementedYet
from app.core.security import get_current_user
from app.schemas import AgentQueryRequest, AgentQueryResponse, AgentSuggestion

router = APIRouter(prefix="/agent", dependencies=[Depends(get_current_user)])


@router.post(
    "/queries",
    response_model=AgentQueryResponse,
    summary="自然语言查库存（只读，P2 实现）",
    responses={501: {"description": "Sprint 1 未实现"}},
)
async def agent_query(body: AgentQueryRequest) -> AgentQueryResponse:
    """自然语言查库存：把「3 号库 A 区还有多少矿泉水」翻成 SQL 并回答。

    P2 实现要点：只允许生成 SELECT；SQL 必须经白名单校验后才执行；
    返回的 sql_summary 要落库，用户看到答案的同时能看到数据来源。
    """
    raise NotImplementedYet(
        message="自然语言查询将在 P2 阶段实现",
        detail={"query": body.query, "planned": "P2 · W7-W8"},
    )


@router.post(
    "/suggestions",
    response_model=AgentSuggestion,
    status_code=201,
    summary="AI 补货/调拨建议（写，生成待审批单，P2 实现）",
    responses={501: {"description": "Sprint 1 未实现"}},
)
async def agent_create_suggestion(
    agent_run_id: str | None = Header(default=None, alias="X-Agent-Run-Id"),
) -> AgentSuggestion:
    """生成补货/调拨建议，落库为 PENDING 状态，等人审批。

    关键：这里只产生「建议」，不产生任何库存变动、也不建正式单据。
    Agent 的输出永远是待审的建议，不是已执行的动作。
    """
    raise NotImplementedYet(
        message="补货建议将在 P2 阶段实现",
        detail={"agent_run_id": agent_run_id, "planned": "P2 · W8-W9"},
    )


@router.post(
    "/suggestions/{suggestion_id}/approve",
    response_model=AgentSuggestion,
    summary="人工审批建议（转正式单据，P2 实现）",
    responses={501: {"description": "Sprint 1 未实现"}},
)
async def agent_approve_suggestion(suggestion_id: int) -> AgentSuggestion:
    """人工审批：把 PENDING 建议转成正式单据（入库单/调拨单）。

    这是整条 AI 链路上唯一有「写权限」的一步，且必须由人触发。
    Agent 不能调用这个接口 —— 这是治理红线，P2 实现时要在鉴权层强制。
    """
    raise NotImplementedYet(
        message="建议审批将在 P2 阶段实现",
        detail={"suggestion_id": suggestion_id, "planned": "P2 · W9"},
    )
