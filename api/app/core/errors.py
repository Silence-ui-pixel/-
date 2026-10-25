"""业务异常。

约定：业务错误一律抛 DomainError，带机器可读的 code 和可展示的 detail。
HTTP 层捕获后转成对应的状态码（如 INVENTORY_INSUFFICIENT → 409），
code 同时用于前端判断，detail 用于前端展示给用户。

错误码命名：大写蛇形 DOMAIN_RESOURCE_ACTION，如 INVENTORY_INSUFFICIENT。
"""


class DomainError(Exception):
    """带错误码的业务异常基类。

    code:   机器可读的错误码，如 "INVENTORY_INSUFFICIENT"
    message: 面向用户的简短描述
    detail:  附加结构化信息（供前端展示或定位），可选
    """

    def __init__(self, code: str, message: str, detail: dict | None = None):
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class InventoryInsufficient(DomainError):
    """可用库存不足。

    detail 约定（与 apply-txn-cases.md TC-02、api-list 的 O4 对齐）：
        sku_code / batch_no / required / available / shortfall
    """

    def __init__(
        self,
        *,
        sku_code: str,
        batch_no: str,
        required: float,
        available: float,
    ):
        super().__init__(
            code="INVENTORY_INSUFFICIENT",
            message="可用库存不足",
            detail={
                "sku_code": sku_code,
                "batch_no": batch_no,
                "required": float(required),
                "available": float(available),
                "shortfall": float(required - available),
            },
        )
