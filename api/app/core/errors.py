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
