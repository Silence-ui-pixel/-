# B 开工清单：数据已就绪，4 个页面零阻塞

> 作者：A · 日期：2026-10-26
> 契约版本：**v1.3**（v1.1 / v1.2 / v1.3 三次变更都已生效）
> 面向：B（前端）。看完这份就能直接开工，不用再等 A 的数据。

---

## 〇、开工前先做一件事：`git pull`

我这两轮改了 **后端契约、种子数据、测试**，还有 **1 个前端 bug**。不 pull 会对不上。

```bash
cd D:\AGENT_PROJECT\Canku_project
git pull origin main
```

pull 完请确认这 3 处（如果没有，说明没拉到最新）：

| 检查 | 期望 |
|---|---|
| `contracts/CHANGELOG.md` | 有 `## v1.2` 和 `## v1.3` 两节 |
| `db/seed.sql` 库位块 | 编码是 `A0101` / `C0101` 这种，**不是** `WH01-A-01-01-01` |
| `web/src/views/inventory/index.vue` | 只有 `<router-view />`，不再是那个 42 行占位页 |

### ⚠️ `VITE_USE_MOCK` 已改成 `false`（不再走 Mock）

`web/.env.development` 里我把它从 `true` 改成了 `false` —— 因为后端接口已经全部就绪，试运行要连真实数据。**pull 下来之后你的页面会直接打真实后端（`localhost:8000`），MSW 不再拦截。**

这会带来两个变化，心里有数就行：

1. **没接后端的地方会真的报错**（以前 Mock 兜住了）。如果你正在写的页面还需要假数据过渡，本地临时改回 `true` 就行，**但提交前请改回 `false`**，别把它推到远程。
2. **登录必须用真实账号**：`admin/admin123`、`sup01/sup123`、`op01/op123`。Mock 里那套假 token 不再生效。

> 另外 `web/package-lock.json` 我一起提交了，但**只是 npm 版本差异产生的 `peer: true` 标记**，没有增删任何依赖、没改任何版本号。你本地跑 `npm ci` 结果完全一致。

### 我在你的前端修了 1 个 bug（重要）

`web/src/views/inventory/index.vue` 原来是 42 行的骨架占位页（禁用输入框 + "等待 Mock 就绪"提示）。你把真页面建在 `inventory/query/` 和 `inventory/txn/` 下，但**父组件没改成 `<router-view />`**。

后果：`/inventory/query` 匹配到「父组件 + 子组件」，父组件里没有 `<router-view>`，**子组件渲染不出来** —— 点「库存查询」看到的永远是占位页，你写的 284 行（含规格列）根本显示不了。

我按 `inbound/index.vue` 的写法改成了纯出口。`views/pda/index.vue` 也是占位页，但路由用的是 `@/layout/pda.vue` 外壳，那个文件没被引用（死文件），要不要删你定。

---

## 一、结论先说

| 页面 | 状态 | 需要接口 | 能不能现在做 |
|---|---|---|---|
| **库位管理** | 占位 | `GET /locations` | ✅ 现在就能做 |
| **SKU 管理** | 占位 | `GET/POST/PUT /skus` | ✅ 现在就能做 |
| **上架作业** | 占位 | `POST .../putaway` + `GET /locations` | ✅ 现在就能做 |
| **用户角色** | 占位 | `GET /users` | ✅ 现在就能做（只读） |
| **对账页**（新建议） | 还没有 | `GET /inventory/recon` | ✅ 现在就能做 |
| PDA 首页 | 占位 | 纯 UI | ✅ 现在就能做 |
| 审计日志 / 波次 / 打包 | 占位 | 契约里没有 | ⛔ Sprint 2 |

**没有任何页面卡在「等 A 的接口」上了。** 之前唯一的缺口是 `GET /users`，v1.2 已补。

---

## 二、现在库里的真实数据（可直接对着开发）

```
SKU          13 个（10 个业务真实 + 3 个早期开发样例）
库位         13 个（STORAGE 7 / RECEIVING 2 / STAGING 2 / QUARANTINE 2）
库存         14 个维度，现有 800 件，已分配 125 件
对账         14 条全部 OK（无一条 MISMATCH）
用户         3 个（admin / sup01 / op01）
```

### 账号

| 用户名 | 密码 | 角色 | 用来验什么 |
|---|---|---|---|
| `admin` | `admin123` | ADMIN | 全权限，主账号 |
| `sup01` | `sup123` | MANAGER | 能取消单、能查对账、能查用户 |
| `op01` | `op123` | OPERATOR | **取消单会被 403**、**查用户会被 403** |

---

## 三、4 个能立刻开工的页面

### 3.1 库位管理 〔`GET /locations`〕

**接口**：`GET /api/v1/locations`
**分页**：**无分页**（库位数量有限，一次全返回 13 条，`page_size` 参数会被忽略）
**筛选**：`zone_code` / `location_type` / `status`（都可选）

真实响应（第一条）：

```json
{
  "items": [
    {
      "id": 1,
      "warehouse_code": "WH01",
      "zone_code": "A",
      "rack_code": "01",
      "level_no": 1,
      "bin_code": "A0101",
      "location_code": "A0101",
      "location_type": "STORAGE",
      "pick_seq": 1,
      "status": 1
    }
  ]
}
```

**13 个库位分布**：

| 类型 | 数量 | 编码 |
|---|---|---|
| STORAGE（存储位） | 7 | `A0101` `A0102` `A0201` `A0202` `B0101` `B0102` `B0201` |
| RECEIVING（收货暂存） | 2 | `C0101` `C0102` |
| STAGING（发货暂存） | 2 | `C0201` `C0202` |
| QUARANTINE（隔离待检） | 2 | `D0101` `D0102` |

**三个要注意的点**：

1. **`location_code` 现在等于 `bin_code`**（都是 `A0101`）。不要自己拼 `warehouse-zone-rack-level-bin`，会得到现场没人认得的串。我之前就是这么错的，v1.3 已统一。
2. **QUARANTINE 2 个位当前是空的**，业务方说没有待检库存。保留备用，页面上可以显示但会有 0 库存，别当成 bug。
3. **`status`：1 启用 / 0 停用**（不是 `enabled`/`disabled`）。`pick_seq` 是拣货顺序，数字小的先跑。

**不能做的**：库位增删改。契约里没有 `POST/PUT/DELETE /locations`，本期只读。

---

### 3.2 SKU 管理 〔`GET/POST/PUT /skus`〕

**列表**：`GET /api/v1/skus?keyword=&category=&page=&page_size=`
（注意：**没有 `status` 筛选参数**，只有 keyword / category）

```json
{
  "items": [{
    "id": 4,
    "sku_code": "SKU0001",
    "barcode": "6901234567890",
    "name": "矿泉水 550ml",
    "spec": "550ml*24/箱",
    "category": "饮料",
    "base_uom": "箱",
    "weight_kg": 13.2,
    "volume_m3": null,
    "shelf_life_days": 365,
    "abc_class": "A",
    "is_batch_managed": true,
    "safety_stock": 50.0,
    "reorder_point": 30.0,
    "status": 1,
    "created_at": "2026-10-26T15:44:26.891747Z",
    "updated_at": "2026-10-26T15:44:26.891747Z"
  }],
  "meta": { "total": 13, "page": 1, "page_size": 2 }
}
```

**详情**：`GET /api/v1/skus/{id}` → 返回单个对象（同上结构）

**新建**：`POST /api/v1/skus`

```json
{"sku_code":"SKU-TEST-9","name":"测试商品","spec":"1*1","category":"测试",
 "base_uom":"箱","is_batch_managed":true,"safety_stock":10,"reorder_point":5,"abc_class":"C"}
```

必填只有 `sku_code` + `name`，其余有默认值（`base_uom` 默认 `"EA"`）。

**修改**：`PUT /api/v1/skus/{id}`（字段全可选，只传要改的）

```json
{"name":"矿泉水 550ml（新包装）","safety_stock":60}
```

**两个红线**：

1. **`PUT` 不能改 `sku_code` 和 `barcode`** —— 契约没开放这两个字段，传了会被忽略。编码变更会让历史单据指向错货。前端应该把这两个字段在编辑表单里**设为只读**，不要给用户可编辑的错觉。
2. **`base_uom` 是中文**（`箱`/`提`/`袋`），不是 `BOX`。早期样例数据是 `BOX`，现在混着，见第七节已知限制。

---

### 3.3 上架作业 〔`POST .../putaway`〕

**接口**：`POST /api/v1/inbound-orders/{order_id}/putaway`

```json
{"lines":[{"line_id":1,"to_location_id":null}]}
```

- `to_location_id` 传 `null` 或省略 → 系统自己选（策略：先找已有同 SKU 且未满的存储位，否则取 `pick_seq` 最小的）
- 上架页的「推荐库位」可以直接复用这个逻辑，不用自己算
- `lines` 整体可以省略（省略 = 全部明细一起上架）

真实响应（明细部分）：

```json
{
  "id": 1, "line_no": 1,
  "sku_id": 4, "sku_code": "SKU0001", "sku_name": "矿泉水 550ml",
  "qty_required": 10.0, "qty_actual": 10.0, "qty_rejected": 0.0,
  "batch_no": "SAMP-B1", "expiry_date": "2027-09-01",
  "from_location_id": null,
  "to_location_id": 1,
  "status": "DONE"
}
```

**注意**：`from_location_id` 返回 `null`（当前实现里上架是「从收货位搬走」，不回填来源 id）。响应里单头 `status` 会变 `DONE`。

**前置条件**：单据必须是 `RECEIVED` 或 `RECEIVING` 才能上架，否则 409。

---

### 3.4 用户角色 〔`GET /users`，v1.2 新增〕

**接口**：`GET /api/v1/users?keyword=&role=&page=&page_size=`
**权限**：**MANAGER / ADMIN 才能查**，OPERATOR / VIEWER 返回 403

```json
{
  "items": [
    {"id":1,"username":"admin","display_name":"系统管理员","role":"ADMIN","status":1},
    {"id":2,"username":"sup01","display_name":"张主管","role":"MANAGER","status":1}
  ],
  "meta": {"total":3,"page":1,"page_size":2}
}
```

**重要**：

- `status` 是 **数字**（1 启用 / 0 停用），和 `User`（`GET /users/me`）的结构不同 —— `UserListItem` 比分页项多一个 `status`，少 `created_at`
- **本期只有列表，没有增删改**（契约里没有 `POST/PUT/DELETE /users`）。页面请做成**只读列表**，不要放"新建用户"按钮 —— 放了就是给用户一个点了没反应的坑
- 现在只有 3 个账号，列表会很"空"，见第七节

---

## 四、建议顺手做的：对账页（接口刚补齐字段）

这个页面你还没建（`web/src/views/` 下没有 recon 相关目录）。它是「账实一致」的唯一可视化入口，D1 评审时专门讨论过，也是你验收后端时最有用的一页。

**接口**：`GET /api/v1/inventory/recon?recon_status=`
**权限**：MANAGER / ADMIN

```json
{
  "items": [{
    "sku_id": 1,
    "sku_code": "SKU-1001",
    "sku_name": "矿泉水 550ml",
    "location_id": 1,
    "location_code": "A0101",
    "batch_no": "B20261001",
    "expiry_date": "2027-10-01",
    "inv_on_hand": 200.0,
    "txn_on_hand": 200.0,
    "diff_on_hand": 0.0,
    "recon_status": "OK"
  }]
}
```

> `sku_code` / `sku_name` / `location_code` 是 v1.3 刚加的。之前只有 id，前端要自己 join 两个列表，join 不到时还没法排查 —— 而排查异常正是对账页的核心用途。

**`recon_status` 四种值**：

| 值 | 含义 | 前端怎么显示 |
|---|---|---|
| `OK` | 余额与流水累计一致 | 绿色标签 |
| `MISMATCH` | 两边都有但数量不等 | 红色 + 显示 `diff_on_hand` |
| `ONLY_INVENTORY` | 有余额没流水（有人直接改了余额） | 红色，这是最严重的一种 |
| `ONLY_TXN` | 有流水没余额 | 红色 |

**建议交互**：默认显示全部，顶部放 4 个状态筛选 tab；`MISMATCH` 和 `ONLY_*` 用红色高亮，`OK` 用绿色。现在 14 条全 `OK`，正常状态下应该是"一片绿"。

---

## 五、后端有、你还没接的接口（6 个）

| 接口 | 用途 | 建议 |
|---|---|---|
| `GET /locations` | 库位列表 | 做库位管理页（3.1） |
| `GET /inventory/recon` | 对账视图 | 做对账页（第四节） |
| `POST /skus` | 建商品 | 做 SKU 管理页（3.2） |
| `GET /skus/{id}` | 商品详情 | 同上 |
| `PUT /skus/{id}` | 改商品 | 同上 |
| `PATCH /inbound-orders/{id}/lines/{id}` | 改明细数量 | 入库详情页可加「改数量」，**仅 DRAFT 状态可用**，且**需 MANAGER** |

---

## 六、v1.1 那条改动，你的收货页必须跟着改 ⚠️

这是**最容易漏**的一条。v1.1 之后，**收货可以多次调用**：

| 场景 | 现在的行为 |
|---|---|
| 计划 100 件，第一次收 40 | 单头 `RECEIVING`，明细 `PARTIAL`，`qty_actual=40` |
| 再收 60 | 单头 `RECEIVED`，明细 `DONE`，`qty_actual=100`（**累加，不是覆盖**） |
| 超收（收了 120） | 允许，`qty_actual=120`（供应商多发是真实场景） |

**页面要改的地方**：

1. **`RECEIVING` 不是终态**，不能像 `RECEIVED` 那样隐藏"继续收货"按钮
2. **`qty_actual` 是累计值**，收货输入框的默认值应该是「剩余待收数量 = `qty_required - qty_actual`」，不是 `qty_required`
3. 明细 `PARTIAL` 状态要有中文显示（"部分收货"），别直接显示英文枚举
4. 如果单据是 `RECEIVING`，收货页顶部建议提示"已收 40 / 应收 100，剩余 60"

---

## 七、已知限制（不是 bug，别去修）

| # | 限制 | 原因 / 影响 |
|---|---|---|
| 1 | **用户只有 3 个** | 现场回填的 6 个真实用户（张三/李四…）还在 `db/field-data/users.csv`，**没导入** `app_user`。等你把用户页做出来、确认字段够用，我再导 |
| 2 | **`base_uom` 中英混杂** | 现场 10 个 SKU 是 `箱/提/袋`，早期 3 个样例是 `BOX/PACK`。这是真实数据与开发样例并存的结果，生产环境只会是一种。别在页面上做单位枚举校验 |
| 3 | **`safety_stock` 与 `reorder_point` 语义存疑** | 现场 10 个 SKU 全是 `reorder_point < safety_stock`，与常规相反。已列为待业务确认，**不影响页面显示**，但 P2 补货算法要先定这个 |
| 4 | **`Idempotency-Key` 仍不校验** | 见《接口调用红线与开发约定》第二节。前端兜底策略不变：409 + `INVALID_STATUS_TRANSITION` 时先 GET 查状态，别直接重新提交 |
| 5 | **分配是整单 409** | 一行缺货整单失败，Sprint 2 改按明细行。前端暂时按整单处理 |
| 6 | **过期批次不可分配** | v1.1 起，全部批次过期的 SKU 分配会返回 409 `INVENTORY_INSUFFICIENT`，`detail.available` 可能是 0 而库里明明有货。这是正确的（过期货不该发），前端文案要说清"无可用的有效批次库存" |
| 7 | **库存只有 800 件、14 个维度** | 数据量小，分页控件看不出效果。测分页请用 `page_size=2` 手动验证 |

---

## 八、提交前自检

- [ ] `git pull origin main` 拉过，确认 `CHANGELOG.md` 有 v1.2 / v1.3
- [ ] `views/inventory/index.vue` 已是 `<router-view />`，点「库存查询」能看到真页面（10 列含规格）
- [ ] 页面上的库位编码是 `A0101` 这种，不是 `WH01-A-01-01-01`
- [ ] 用户页没有"新建/编辑/删除"按钮（接口没有）
- [ ] SKU 编辑表单里 `sku_code` / `barcode` 是只读
- [ ] 收货页能处理 `RECEIVING` / `PARTIAL`，`qty_actual` 按累计值显示
- [ ] 403 的错误提示走统一错误结构（`code: "FORBIDDEN"`），不是硬编码文案
- [ ] 对账页 `recon_status` 四种值都有中文映射

---

## 九、卡住了怎么办

| 情况 | 找谁 | 怎么描述 |
|---|---|---|
| 接口返回 4xx/5xx，和这份文档不符 | A | 贴 `curl -i` 完整请求 + 响应，我要能复现 |
| 页面渲染问题 / 交互 | B 自己 | — |
| 需要新接口 | A | 说清"哪个页面、要什么数据、为什么现有接口不够"。我会判断是「允许」还是「升版本」 |
| 数据不对 | A | 贴 `curl` 结果 + 期望值。我这边可以用 `db/field-data/` 重建一份干净数据 |

**注意**：后端有 `--reload`，我改代码后你不用重启容器。但如果我改了 `db/seed.sql` 或建了新表，我会通知你重建数据，那之后你本地状态会被重置。

---

## 十、优先级建议

如果时间有限，按这个顺序做：

1. **库位管理**（最简单，纯列表 + 筛选，接口无分页省事）
2. **上架作业**（能补完入库链路：建单 → 收货 → 上架 → DONE）
3. **SKU 管理**（列表 + 详情 + 编辑，建单可放最后）
4. **对账页**（价值最高，验收时最有说服力）
5. **用户角色**（最简单但数据最少，3 条看不出分页效果）
6. **PDA 首页**（纯 UI，随时可做）
