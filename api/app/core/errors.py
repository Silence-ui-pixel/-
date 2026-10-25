"""业务异常。

约定：业务错误一律抛 DomainError，带机器可读的 code、面向用户的中文 message、
以及结构化 detail。HTTP 层由全局异常处理器捕获，转成契约里定义的 Error 结构：
    { "code": "...", "message": "...", "detail": {...} }

错误码命名：大写蛇形 DOMAIN_RESOURCE_ACTION，如 INVENTORY_INSUFFICIENT。
错误码清单见 contracts/errors.md —— 改这里必须同步改那份文档。
"""


class DomainError(Exception):
    """带错误码的业务异常基类。

    code:        机器可读的错误码，如 "INVENTORY_INSUFFICIENT"
    message:     面向用户的简短描述
    detail:      附加结构化信息（供前端展示或定位），可选
    status_code: 对应的 HTTP 状态码，默认 400
    """

    status_code: int = 400

    def __init__(self, code: str, message: str, detail: dict | None = None):
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class NotFound(DomainError):
    """资源不存在。"""

    status_code = 404

    def __init__(self, message: str = "数据不存在", detail: dict | None = None):
        super().__init__(code="NOT_FOUND", message=message, detail=detail)


class Conflict(DomainError):
    """业务冲突（唯一键重复、状态互斥等）。"""

    status_code = 409

    def __init__(self, code: str, message: str, detail: dict | None = None):
        super().__init__(code=code, message=message, detail=detail)


class NotImplementedYet(DomainError):
    """接口已定义但本阶段未实现（契约占位，返回 501）。

    用 501 而不是 404：明确告诉调用方「这个接口存在，只是还没做」，
    前端可以据此显示「功能开发中」而不是「接口不存在」。
    """

    status_code = 501

    def __init__(self, message: str = "该功能将在 P2 阶段实现", detail: dict | None = None):
        super().__init__(code="NOT_IMPLEMENTED", message=message, detail=detail)


class InvalidStatusTransition(DomainError):
    """单据状态机不允许的流转（如 DONE 之后再收货）。

    detail 约定：order_no / current_status / action / allowed_statuses
    """

    status_code = 409

    def __init__(
        self,
        *,
        order_no: str,
        current_status: str,
        action: str,
        allowed_statuses: list[str],
    ):
        super().__init__(
            code="INVALID_STATUS_TRANSITION",
            message=f"当前状态（{current_status}）不能执行「{action}」",
            detail={
                "order_no": order_no,
                "current_status": current_status,
                "action": action,
                "allowed_statuses": allowed_statuses,
            },
        )


class InventoryInsufficient(DomainError):
    """可用库存不足。

    detail 约定（与 apply-txn-cases.md TC-02、api-list 的 O4 对齐）：
        sku_code / batch_no / required / available / shortfall
    """

    status_code = 409

    def __init__(
        self,
        *,
        sku_code: str,
        batch_no: str,
        required: float,
        available: float,
        extra: dict | None = None,
    ):
        detail = {
            "sku_code": sku_code,
            "batch_no": batch_no,
            "required": float(required),
            "available": float(available),
            "shortfall": float(required - available),
        }
        if extra:
            detail.update(extra)
        super().__init__(
            code="INVENTORY_INSUFFICIENT",
            message="可用库存不足",
            detail=detail,
        )


# ---------------------------------------------------------------------------
# 非业务异常的错误码映射
# ---------------------------------------------------------------------------
# 为什么需要这段：业务错误抛 DomainError 能带上 code，但路由里还有大量
# `raise HTTPException(404, "入库单不存在")`，以及 FastAPI 自己的
# 401/403/404/422（鉴权依赖、路径校验、Pydantic 请求体校验）。
# 这些原本返回 { "detail": "..." }，前端拿不到 code，无法按错误类型分流。
#
# 映射表放在这里而不是 main.py：错误码体系的唯一真源在 errors.py，
# 改码表必须同步改 contracts/errors.md。main.py 只负责装配。

HTTP_STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_ERROR",
    501: "NOT_IMPLEMENTED",
    503: "SERVICE_UNAVAILABLE",
}

# 未收录的状态码用这个兜底，保证前端永远能拿到 code（不必自己判 HTTP）
FALLBACK_CODE = "HTTP_ERROR"


def code_for_status(status_code: int) -> str:
    """HTTP 状态码 -> 契约错误码。"""
    return HTTP_STATUS_TO_CODE.get(status_code, FALLBACK_CODE)


# Pydantic 报错里 ctx 可能塞着 Exception 对象（如 ValueError），input 可能是
# bytes —— 直接 JSONResponse 会抛 "not JSON serializable" 变成 500，
# 把「参数错了」误导成「服务器崩了」。这里统一洗成可序列化的原始类型。
_JSON_SCALARS = (str, int, float, bool, type(None))


def _jsonable(value):
    if isinstance(value, _JSON_SCALARS):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)


def clean_validation_errors(raw: list[dict]) -> list[dict]:
    """把 Pydantic 的 errors() 洗成前端可直接消费、且一定可 JSON 序列化的结构。

    保留 loc / msg / type / ctx / input 五个字段：
      loc  -> 前端据此定位到具体字段（如 ["body", "lines"]）
      msg  -> 开发排查用（英文原文）
      type -> 判断错误类别（missing / greater_than 等）
    """
    cleaned: list[dict] = []
    for err in raw:
        item = {
            "loc": list(err.get("loc", ())),
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        }
        if "ctx" in err and err["ctx"]:
            item["ctx"] = _jsonable(err["ctx"])
        if "input" in err:
            item["input"] = _jsonable(err["input"])
        cleaned.append(item)
    return cleaned
