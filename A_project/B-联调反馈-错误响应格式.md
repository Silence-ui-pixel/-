# B → A 联调反馈：错误响应格式不符合契约

> 作者：B · 日期 2026-10-25
> 背景：本地已起后端（`bash scripts/dev.sh up` + `db-init`），前端以 `VITE_USE_MOCK=false` 直连 127.0.0.1:8000 完成首轮联调。
> 结论：**正常路径全部通了；只有「非业务异常」的错误响应格式不符合契约，需要修一处。**

---

## 一、问题一句话

契约规定错误体统一为 `{ code, message, detail }`，但**只有 DomainError（业务错误）走对了**；
`HTTPException` / `RequestValidationError`（401/403/404/422）仍返回 FastAPI 默认的 `{ detail: ... }`。

---

## 二、实测证据（逐个抓的真实响应）

| # | 场景 | HTTP | 实际返回 | 契约要求 |
|---|---|---|---|---|
| 1 | 登录密码错 | 401 | `{"detail":"用户名或密码错误"}` | `{code:"UNAUTHORIZED", message, detail}` |
| 2 | 未带 token | 401 | `{"detail":"缺少认证信息"}` | `{code:"UNAUTHORIZED", ...}` |
| 3 | op01 查对账（需 MANAGER） | 403 | `{"detail":"需要仓管主管及以上权限"}` | `{code:"FORBIDDEN", ...}` |
| 4 | 单据 id 不存在 | 404 | `{"detail":"入库单不存在"}` | `{code:"NOT_FOUND", ...}` |
| 5 | 建单缺 lines | 422 | `{"detail":[{"type":"missing","loc":["body","lines"],...}]}` | `{code:"VALIDATION_ERROR", message, detail}` |
| 6 | **库存不足（对照组）** | 409 | ✅ `{"code":"INVENTORY_INSUFFICIENT","message":"可用库存不足","detail":{...}}` | 一致 |

> 第 6 行说明：**DomainError 那条链路完全正确**，`detail` 里的 `sku_code / batch_no / required / available / shortfall` 都在，甚至多带了 `order_no / line_no / note`，很好。
> 问题只出在「没被 DomainError 包住」的那几类异常。

---

## 三、影响（为什么必须修）

1. **前端拿不到 `code`**，无法按错误类型分流：`INVENTORY_INSUFFICIENT` 要弹缺货明细、`INVALID_STATUS_TRANSITION` 要提示刷新，现在只能统一显示一句话。
2. **422 的字段级错误拿不到**：`{"detail":[...]}` 是数组，前端要展示「哪个字段错了」得自己猜结构，契约里本该是 `VALIDATION_ERROR` + 结构化 detail。
3. **Token 过期无法自动跳登录**：前端靠 `code === 'UNAUTHORIZED'` 判断，现在只有 `detail` 文本，只能靠 HTTP 401 硬判（能用但脆弱）。

> 前端已做兼容（`message ?? detail字符串 ?? 错误码映射`），所以**不阻塞联调**；
> 但「结构化错误」是契约的核心价值之一，建议这轮一起修掉。

---

## 四、建议改法（`api/app/main.py` 加两个 handler，约 20 行）

你已经有 `DomainError` 的 handler，只要把 FastAPI 的两类内置异常也转过去即可：

```python
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# HTTP 状态码 → 契约错误码（与 contracts/errors.md 一致）
_STATUS_TO_CODE = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND"}

@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": _STATUS_TO_CODE.get(exc.status_code, "UNKNOWN_ERROR"),
            "message": str(exc.detail),
            "detail": None,
        },
    )

@app.exception_handler(RequestValidationError)
async def handle_validation_error(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "参数不合法",
            "detail": {"errors": exc.errors()},
        },
    )
```

改完后前端**不需要再改**（兼容逻辑会自动优先取 `message`）。

---

## 五、首轮联调已通过的部分（好消息）

| 项 | 结果 |
|---|---|
| `/health` | `{"status":"ok"}` |
| 登录 admin/admin123 | 返回 JWT，`token_type: bearer` |
| `/users/me` | `id/username/display_name/role` 全对 |
| `/inventory` | 真实数据：`SKU-1001 / WH01-A-01-01-01 / 200 BOX`，`meta.total/page/page_size` 结构正确 |
| 按 `sku_code` 筛选 | 命中正确 |
| 建出库单 → 分配 | 单号生成、状态机、409 明细全部正确 |
| 对账视图 | `recon_status = OK` |

---

## 六、另外两个小观察（不算问题，供你判断）

1. **`InventoryItem` 没有 `spec`（规格）字段**：库存查询页想显示「规格」时拿不到，只能显示 SKU 编码 + 名称。如果这轮要显示，需要在契约 `InventoryItem` 加 `spec`（只增字段，不改语义）。
2. **`db-init` 是首次启动的必需步骤**：README 已写清，我只是踩了一次坑（没跑 db-init 直接登录 → 500 `relation "app_user" does not exist`）。建议把这个放进 `dev.sh up` 的提示语里，减少新人踩坑。
3. **已知限制已收到**（不支持跨批次分配、不支持多次部分收货）：前端交互会按「请拆分该明细」提示，与你的 `note` 字段一致。

---

**一句话总结**：业务错误（409）完全符合契约；只有 401/403/404/422 四类内置异常仍是 `{detail}` 格式，建议在 `main.py` 补两个 exception_handler 统一转成 `{code, message, detail}`，前端无需再改。
