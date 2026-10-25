"""AI Agent 接口 —— Sprint 1 只占位（501），P2 实现。

为什么现在就建这个文件、而不是等 P2 再建：
    1. 契约里已经有这三条路径，前后端都已经按它生成类型、接好了调用点。
       如果后端返回 404，前端只能显示「接口不存在」，和「功能还在做」混在一起，
       排查时会浪费大量时间。501 是准确的语义。
    2. 把治理设计提前落到代码结构里，避免 P2 仓促实现时漏掉红线。

P2 实现时必须遵守的三条（写在这里作为接手者的约束）：
    1. **只读优先**：G1 自然语言查询只允许 SELECT，不允许任何写操作
    2. **建议不等于执行**：G2 只生成 PENDING 状态的建议单，不直接建单
    3. **人审批才能落地**：G3 由人触发，Agent 不能自己批自己
    这是「智能与操作权限分离」在接口层的体现 —— 见架构文档 L2 层说明。
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
