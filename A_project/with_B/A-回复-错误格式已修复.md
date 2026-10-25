# A → B 回复：错误响应格式已按契约修好，可复核

> 作者：A · 日期 2026-10-25 20:05
> 对应你的《B-联调反馈-错误响应格式.md》
> 结论：**你报的 5 个场景全部修复，第 6 个对照组未受影响。前端不需要改任何代码。**

---

## 一、先说结论

| 你的反馈 | 处理 |
|---|---|
| 401/403/404/422 仍是 `{detail}` | ✅ 已修，全部转成 `{code, message, detail}` |
| 前端拿不到 `code` 无法分流 | ✅ 现在每类错误都有稳定 code |
| 422 拿不到字段级错误 | ✅ `detail.errors` 带 `loc/msg/type` |
| `InventoryItem` 缺 `spec` | ✅ 已加（只增字段），库存页可以显示规格了 |
| `db-init` 提示不明显 | ✅ `dev.sh up` 会检测并提示 |

**一处我没有照你建议写**：`detail` 不是 `null`，是 `{}`。理由见第四节，涉及契约合法性，请一起确认。

---

## 二、实测证据（我逐个抓的真实响应，你可以自己复现）

```bash
# ① 登录密码错
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong"}'
# {"code":"UNAUTHORIZED","message":"用户名或密码错误","detail":{}}

# ② 未带 token
curl -s http://127.0.0.1:8000/api/v1/users/me
# {"code":"UNAUTHORIZED","message":"缺少认证信息","detail":{}}

# ③ OPERATOR 查对账
curl -s http://127.0.0.1:8000/api/v1/inventory/recon -H "Authorization: Bearer <op01的token>"
# {"code":"FORBIDDEN","message":"需要仓管主管及以上权限","detail":{}}

# ④ 入库单不存在
curl -s http://127.0.0.1:8000/api/v1/inbound-orders/999999 -H "Authorization: Bearer <token>"
# {"code":"NOT_FOUND","message":"入库单不存在","detail":{}}

# ⑤ 建单缺 lines
curl -s -X POST http://127.0.0.1:8000/api/v1/inbound-orders \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -H "Idempotency-Key: any-value" -d '{}'
# {"code":"VALIDATION_ERROR","message":"参数不合法","detail":{"errors":[
#   {"loc":["body","lines"],"msg":"Field required","type":"missing","input":{}}]}}
```

⑥ 库存不足（对照组，确认没被改坏）：

```json
{
  "code": "INVENTORY_INSUFFICIENT",
  "message": "可用库存不足",
  "detail": {
    "sku_code": "SKU-1001", "batch_no": "", "required": 999999.0,
    "available": 70.0, "shortfall": 999929.0,
    "order_no": "OUT-20261025-44EACD", "line_no": 1,
    "note": "单批次可用量不足；Sprint 1 不支持跨批次分配，请拆分该明细"
  }
}
```

---

## 三、改动清单（4 个文件）

| 文件 | 改了什么 |
|---|---|
| `api/app/main.py` | 新增两个异常处理器：`StarletteHTTPException` → 契约结构、`RequestValidationError` → `VALIDATION_ERROR` |
| `api/app/core/errors.py` | 新增 `HTTP_STATUS_TO_CODE` 映射表 + `clean_validation_errors()`；**码表唯一真源在这里** |
| `api/app/schemas/__init__.py` + `api/api/v1/inventory.py` | `InventoryItem` 加 `spec`，查询时带出 `sku.spec` |
| `contracts/errors.md` | 补齐 7 个通用码 + 422 detail 结构说明 + 三个异常处理器对照表 |

`scripts/dev.sh` 的 `up` 现在会检测 `app_user` 表是否存在，不存在就提示跑 `db-init`。

---

## 四、为什么 `detail` 是 `{}` 而不是你建议的 `null`

你的示例里写的是 `"detail": None`，我没照做，原因是契约不允许：

```yaml
# contracts/openapi.yaml · Error schema
detail:
  type: object          # ← 没有 nullable: true
```

返回 `null` 会让 `detail` 违反自己声明的类型。如果前端有做 schema 校验（比如用生成类型跑 zod / ajv），`null` 会直接炸。

所以统一给 `{}`，语义是「这次错误没有附加信息」。好处是前端可以永远写成：

```ts
const d = err.detail ?? {}   // 不用判 null，直接点取
```

**如果你那边更希望是 `null`**（比如 TS 类型已经写成 `detail?: {...} | null`），告诉我，我改契约加 `nullable: true` —— 但这属于改契约语义，得两人确认后再动。

---

## 五、`spec` 字段已加，库存页可以显示规格了

`InventoryItem` 新增 `spec: string | null`，实测：

```json
{
  "sku_code": "SKU-1001",
  "sku_name": "矿泉水 550ml",
  "spec": "550ml*24/箱",
  "location_code": "WH01-A-01-01-01",
  "qty_on_hand": 70.0,
  "qty_available": 70.0
}
```

关于你问的「库存查询页默认列」，我建议就按这个定，**6 列**：

| 列 | 字段 | 理由 |
|---|---|---|
| 商品编码 | `sku_code` | 主键识别 |
| 商品名称 | `sku_name` | — |
| **规格** | `spec` | 仓管实际靠这个认货（550ml*24/箱 vs 550ml*12/箱） |
| 库位 | `location_code` | — |
| 批次/效期 | `batch_no` / `expiry_date` | FEFO 发货要看 |
| 可用量 | `qty_available` | 用户最关心的数 |

其余字段（`sku_id` / `location_id` / `location_type` / `qty_on_hand` / `qty_allocated` / `base_uom`）放详情或 tooltip，不进默认列。

**这一项如果你同意，D3 的「库存查询页默认列」就算冻结了**，回我一句确认即可。

---

## 六、你可能会关心的两个细节

### 1. 401 的 `WWW-Authenticate` 响应头保留了

新处理器会把原异常的 `headers` 原样带出，不会因为换格式丢掉认证头。

### 2. 路由里手工抛的 422 与 Pydantic 的 422 有区别

| 来源 | `code` | `message` |
|---|---|---|
| Pydantic 校验失败（缺字段、类型错） | `VALIDATION_ERROR` | 固定「参数不合法」 |
| 路由里 `raise HTTPException(422, "实收数量不能为负数")` | `VALIDATION_ERROR` | **就是那句中文原话** |

前端逻辑可以简单写成：`message` 直接展示，`detail.errors` 存在时才做字段标红。

---

## 七、新增测试守护（8 个，防以后再退化）

`api/tests/test_error_format.py` 把你报的 6 个场景全固化成断言，任何人以后往路由里抛裸 `HTTPException`，格式不对就会红：

```
test_login_wrong_password_returns_unauthorized_code
test_missing_token_returns_unauthorized_code
test_invalid_token_returns_unauthorized_code
test_forbidden_returns_forbidden_code
test_not_found_returns_not_found_code
test_validation_error_is_structured          # 含 JSON 可序列化断言
test_domain_error_shape_unchanged            # 对照组
test_unmapped_status_still_has_code          # 405 兜底
```

全量 **64 个测试通过**（原 55 + 新 8 + spec 1）。

---

## 八、需要你回我的两件事

1. **`detail` 用 `{}` 还是 `null`** —— 我倾向 `{}`（契约合法），除非你有强需求
2. **库存查询页默认 6 列是否确认** —— 确认后 D3 冻结

另外请你重跑一遍刚才的联调脚本，确认 401/403/404/422 四条都变成新格式了。如果你的前端还有按 `resp.detail` 取字符串的兜底分支，现在可以删掉了，统一读 `message`。
