# B 侧任务清单（前端骨架 / 工作台 / Mock / 页面）

> 成员 B · 领域：交互与智能
> 本清单区分「能单独做的」和「必须等 A 配合的」，用于 Sprint 1 排期。

## 一、B 能「今天立即单独做」的部分（不依赖 A 的契约）

| 事项 | 对应任务 | 为什么现在就能做 |
| --- | --- | --- |
| 前端工程骨架：Vite + Vue3 + TS + Element Plus | S1-10 | 纯搭框架，不碰业务接口 |
| 侧边菜单 + 路由 + 工作台布局框架 | S1-10 | 布局是静态的 |
| 登录页（假 token 存 localStorage） | S1-10 | 不连后端 |
| 从 schema.sql 反推 TS 类型 | S1-11 的前置 | 8 张表字段都写死在 `db/schema(1).sql`，可直接翻成 interface |
| 统一表格 / 表单封装组件（空壳） | S1-10 | 用假数据先跑样式 |
| Mock 数据的「形状」定义 | S1-12 的前置 | 用反推的 TS 类型当 mock 骨架 |
| PDA 页面的响应式布局骨架 | S1-14 | 布局不依赖接口 |

**关键动作**：`db/schema(1).sql` 里 8 张表字段齐全，可直接反推 TS 类型先写（临时占位）。
等 S1-08 正式契约出来后用 `npm run gen` 一键覆盖，前面写的不会白费。

## 二、必须等 A 完成后才能配合的部分

| 事项 | 卡在哪 | A 的任务 |
| --- | --- | --- |
| 正式 TS 类型 + client 生成 | 需要 openapi.yaml | S1-08（D6-D7） |
| Mock server 按契约返回假数据 | 需要契约定 response 结构 | S1-08 |
| 库存查询页「连真数据」 | 需要后端 API | S1-05 起服务 |
| PDA 扫码页「连真数据」 | 需要后端 API | S1-05 |
| 口径确认（可用 / 锁定 / 在途怎么算） | 需要 A 确认 | S1-07（接口清单） |

## 三、建议的起步顺序（有依赖，但能绕过）

1. **今天**：搭骨架 + 假登录 + 侧边菜单（S1-10）
2. **立刻反推**：从 `schema.sql` 写 `inventory / sku / location` 三个 interface
3. **催 A 一件事**：让他先把「库存查询」这一个接口的 schema 草稿发你（不用等完整契约），
   你就能提前写 mock 和页面

## 四、反推 TS 类型的关键字段提示

数据模型里三个核心表，直接对应库存查询页和 PDA 页需要的数据：

- **sku**：`sku_code` / `barcode` / `name` / `spec` / `base_uom` / `is_batch_managed`
- **location**：`location_code` / `zone_code` / `rack_code` / `level_no` / `bin_code` / `location_type`
- **inventory**：`qty_on_hand`（现有）/ `qty_allocated`（锁定）/ `qty_available`（可用 = 现有 - 锁定，生成列）

> 注意 `qty_available` 是数据库生成列（`generated always as ... stored`），
> 前端类型里应标记为只读，不能由前端反算后提交。

## 五、分工铁律（提醒自己）

- B **不允许直接读 A 的数据库表**，所有数据必须走接口或 MCP 工具。
- 交接面只有三个：`contracts/openapi.yaml`、`contracts/mcp-tools.json`、口径文档。
- 接口变更当日通知对方，改契约同步改文档。
