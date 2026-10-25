# contracts/ · 协作契约

**只有成员 A 可以改这个目录。B 要改先提 issue。**

原因不是权限洁癖：契约是两人并行的唯一前提。B 的 S1-11（生成 TS client）和 S1-12（mock server）都从这里长出来。谁都能改，等于没有契约。

---

## 文件规划

| 文件 | 状态 | 说明 |
|---|---|---|
| `api-list.md` | S1-07 待产出 | 接口清单：路径 / 方法 / 读或写 / 是否需要审批 |
| `openapi.yaml` | S1-08 待产出 | OpenAPI 3.1 契约，唯一真源 |
| `errors.md` | 跟契约一起 | 错误码枚举，B 用来在界面显示人话 |
| `mcp-tools.json` | W7 前 | AI Agent 可调用的工具签名（Sprint 1 只占位） |

## 约定

1. **只增字段，不改语义。** 冻结后要给新字段可以，改已有字段的含义必须两人确认。
2. **每个接口必须标「读 / 写」。** 这不是文档装饰——W7 做 Agent 时，写接口必须经过决策引擎和人工审批，读接口可以直接放行。现在不标，到时候要重新推一遍全部接口。
3. **错误码要能给人看。** 每个错误码配一句中文提示，B 直接拿去显示，不要让他猜 `ERR_STOCK_LOCKED` 是什么意思。
4. **契约先于实现。** 不要先写 controller 再反推 yaml。顺序反了整个 Sprint 都在返工。

## 生成与校验

```bash
# 契约语法校验（S1-08 的 DoD）
npx @redocly/cli lint contracts/openapi.yaml

# 从契约生成 TS 类型（B 的 S1-11）
npx openapi-typescript contracts/openapi.yaml -o web/src/api/schema.d.ts
```
