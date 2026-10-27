#!/usr/bin/env node
/**
 * P1 验收：20 单连跑 + 异常场景 + 并发不超卖
 *
 * 依据 02-kickoff-plan.html 的 P1 验收标准：
 *   ① 用真实 SKU 数据跑 20 单，账实一致率 100%
 *   ② 并发扣减不超卖
 *   ③ 异常单据可回滚
 *
 * 用法（在后端已启动的前提下）：
 *   cd B_project
 *   bash scripts/dev.sh up            # 起后端（数据卷在，不用 db-init）
 *   node web/scripts/acceptance-20-orders.mjs
 *
 * 可选参数（环境变量）：
 *   API_BASE=http://127.0.0.1:8000/api/v1   后端地址
 *   ORDERS=20                                跑几轮
 *   WMS_USER=admin  WMS_PASS=admin123        登录账号（需 MANAGER/ADMIN，因对账接口要）
 *
 *   注意：不要用 USERNAME/PASSWORD 作变量名——Windows 上 USERNAME 是系统内置变量，
 *   会被解析成当前 Windows 登录名，导致 401 登录失败。
 *
 * 退出码：0 = 全部通过；1 = 有断言失败（会打印失败项）
 *
 * 注意：
 *   - 脚本会真实写入数据（建单/收货/上架/分配/拣货/发运），建议在可重建的库上跑；
 *   - 跑完想恢复干净基线：bash scripts/dev.sh db-reset 再导入 db/field-data/import.sql
 *   - 全程带 Idempotency-Key，重复执行不会重复扣账
 */

const BASE = process.env.API_BASE || 'http://127.0.0.1:8000/api/v1'
const ROUNDS = Number(process.env.ORDERS || 20)
const USERNAME = process.env.WMS_USER || 'admin'
const PASSWORD = process.env.WMS_PASS || 'admin123'

const RUN_ID = Date.now().toString(36)
let TOKEN = ''

/* ------------------------------ 基础设施 ------------------------------ */

async function api(method, path, { body, idem } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`
  if (idem) headers['Idempotency-Key'] = idem
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  let data = null
  const text = await res.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }
  return { status: res.status, ok: res.ok, data }
}

function isoDate(offsetDays) {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return d.toISOString().slice(0, 10)
}

const stats = {
  inboundCreated: 0,
  inboundDone: 0,
  outboundCreated: 0,
  outboundShipped: 0,
  steps: 0,
  errors: [],
  /** 本次运行创建的入库 / 出库单 id（终态检查只看自己造的，不误伤历史单据） */
  inboundIds: [],
  outboundIds: [],
}

/** 运行开始时的暂存位基线（同一维度已有库存不算本次残留） */
let stagingBaseline = new Map()

function record(label, resp, { allow } = {}) {
  stats.steps += 1
  // 默认接受任意 2xx：建单类接口返回 201，不能只放 200
  const ok = allow ? allow.includes(resp.status) : resp.status >= 200 && resp.status < 300
  if (!ok) {
    const msg = resp.data?.message || resp.data?.detail || JSON.stringify(resp.data).slice(0, 160)
    throw new Error(`${label} 失败：HTTP ${resp.status} ${msg}`)
  }
  return resp.data
}

/* ------------------------------ 主流程 ------------------------------ */

async function login() {
  const r = await api('POST', '/auth/login', { body: { username: USERNAME, password: PASSWORD } })
  if (!r.ok) throw new Error(`登录失败：${r.status} ${JSON.stringify(r.data)}`)
  TOKEN = r.data.access_token
  const me = await api('GET', '/users/me')
  console.log(`登录成功：${me.data.display_name}（${me.data.role}）`)
}

/** 读主数据：SKU、库位、当前库存可用量 */
async function loadMaster() {
  const [skuRes, locRes, invRes] = await Promise.all([
    api('GET', '/skus?page=1&page_size=100'),
    api('GET', '/locations'),
    api('GET', '/inventory?page=1&page_size=100'),
  ])
  const skus = skuRes.data?.items ?? []
  const locations = locRes.data?.items ?? []
  const inventory = invRes.data?.items ?? []
  const storageLocs = locations.filter((l) => l.location_type === 'STORAGE')
  if (!skus.length) throw new Error('没有 SKU，先把数据准备好（db-init 或导入现场数据）')
  if (!storageLocs.length) throw new Error('没有 STORAGE 类型库位，无法上架')
  return { skus, storageLocs, inventory }
}

/** 记录暂存位基线：现场数据本身可能已有货在收货暂存位，不能当成本次残留 */
async function captureStagingBaseline() {
  const [locRes, invRes] = await Promise.all([
    api('GET', '/locations'),
    api('GET', '/inventory?page=1&page_size=100'),
  ])
  const stagingIds = new Set(
    (locRes.data?.items ?? [])
      .filter((l) => ['RECEIVING', 'STAGING'].includes(l.location_type))
      .map((l) => l.id),
  )
  stagingBaseline = new Map()
  for (const r of invRes.data?.items ?? []) {
    if (stagingIds.has(r.location_id)) {
      stagingBaseline.set(`${r.sku_id}@${r.location_id}`, Number(r.qty_on_hand))
    }
  }
}

/** 一轮完整作业：入库 3 步 + 出库 4 步 */
async function runRound(i, ctx) {
  const { skus, storageLocs } = ctx
  const sku = skus[i % skus.length]
  const loc = storageLocs[i % storageLocs.length]
  const inQty = 8 + (i % 4) * 2 // 8 / 10 / 12 / 14
  const outQty = 3 + (i % 3) // 3 / 4 / 5
  const batch = `ACC${RUN_ID}${String(i).padStart(2, '0')}`

  // ---------- 入库 ----------
  const create = record(
    '建入库单',
    await api('POST', '/inbound-orders', {
      body: {
        order_type: 'PO',
        supplier_name: `验收供应商-${i + 1}`,
        lines: [{ sku_id: sku.id, qty_required: inQty }],
      },
    }),
  )
  stats.inboundCreated += 1
  stats.inboundIds.push(create.id)
  const inId = create.id
  const lineId = create.lines?.[0]?.id
  if (!lineId) throw new Error('建单返回缺明细 id')

  record(
    '收货',
    await api('POST', `/inbound-orders/${inId}/receive`, {
      idem: `ACC-${RUN_ID}-${i}-RECV`,
      body: {
        lines: [
          {
            line_id: lineId,
            qty_actual: inQty,
            qty_rejected: 0,
            batch_no: sku.is_batch_managed ? batch : undefined,
            expiry_date: sku.is_batch_managed ? isoDate(180) : undefined,
          },
        ],
      },
    }),
  )

  record(
    '上架',
    await api('POST', `/inbound-orders/${inId}/putaway`, {
      idem: `ACC-${RUN_ID}-${i}-PUT`,
      body: { lines: [{ line_id: lineId, to_location_id: loc.id }] },
    }),
  )
  stats.inboundDone += 1

  // ---------- 出库（同 SKU 刚上架的库存，保证可满足） ----------
  const out = record(
    '建出库单',
    await api('POST', '/outbound-orders', {
      body: {
        order_type: 'SALE',
        customer_name: `验收客户-${i + 1}`,
        priority: 100,
        lines: [{ sku_id: sku.id, qty_required: outQty }],
      },
    }),
  )
  stats.outboundCreated += 1
  stats.outboundIds.push(out.id)
  const outId = out.id

  record(
    '分配',
    await api('POST', `/outbound-orders/${outId}/allocate`, { idem: `ACC-${RUN_ID}-${i}-ALLOC` }),
  )

  const plan = record('取拣货路径', await api('GET', `/outbound-orders/${outId}/pick`))
  const pickLines = (plan.lines ?? []).map((l) => ({
    line_id: l.line_id,
    qty_actual: l.qty_required,
    qty_rejected: 0,
  }))
  if (!pickLines.length) throw new Error('拣货路径为空')

  record(
    '拣货',
    await api('POST', `/outbound-orders/${outId}/pick`, {
      idem: `ACC-${RUN_ID}-${i}-PICK`,
      body: { lines: pickLines },
    }),
  )

  record(
    '发运',
    await api('POST', `/outbound-orders/${outId}/ship`, {
      idem: `ACC-${RUN_ID}-${i}-SHIP`,
      body: { carrier: '验收承运商', tracking_no: `ACC${RUN_ID}${i}` },
    }),
  )
  stats.outboundShipped += 1

  process.stdout.write(
    `  第 ${String(i + 1).padStart(2)} 轮 ✓ 入库 ${inQty} → 出库 ${outQty}（${sku.sku_code} @ ${loc.location_code}）\n`,
  )
}

/* --------------------------- 异常场景（③） --------------------------- */

async function testAnomalies(ctx) {
  const { skus } = ctx
  const sku = skus[0]
  const results = []

  // A. 建单后取消：库存不应有任何变化
  const before = await snapshotQty()
  const draft = record(
    '建单(待取消)',
    await api('POST', '/inbound-orders', {
      body: { order_type: 'PO', supplier_name: '取消测试', lines: [{ sku_id: sku.id, qty_required: 5 }] },
    }),
  )
  const cancelled = record('取消入库单', await api('POST', `/inbound-orders/${draft.id}/cancel`))
  const after = await snapshotQty()
  results.push({
    name: '异常①：建单后取消 → 库存不变',
    pass: cancelled.status === 'CANCELLED' && before === after,
    detail: `状态 ${cancelled.status}，库存 ${before} → ${after}`,
  })

  // B. 超量分配：应被 409 INVENTORY_INSUFFICIENT 拒绝，库存不变
  const beforeOver = await snapshotQty()
  const over = record(
    '建超量出库单',
    await api('POST', '/outbound-orders', {
      body: {
        order_type: 'SALE',
        priority: 100,
        lines: [{ sku_id: sku.id, qty_required: 999999 }],
      },
    }),
  )
  const overAlloc = await api('POST', `/outbound-orders/${over.id}/allocate`, {
    idem: `ACC-${RUN_ID}-OVER-ALLOC`,
  })
  const afterOver = await snapshotQty()
  results.push({
    name: '异常②：超量分配 → 409 且库存不变',
    pass: overAlloc.status === 409 && beforeOver === afterOver,
    detail: `HTTP ${overAlloc.status} ${overAlloc.data?.code ?? ''}，库存 ${beforeOver} → ${afterOver}`,
  })

  // C. 重复收货：应被状态机拒绝（409），不得二次入账
  const dupCreate = record(
    '建单(重复收货)',
    await api('POST', '/inbound-orders', {
      body: { order_type: 'PO', supplier_name: '重复收货测试', lines: [{ sku_id: sku.id, qty_required: 6 }] },
    }),
  )
  const dupLine = dupCreate.lines[0].id
  const recvBody = {
    lines: [
      {
        line_id: dupLine,
        qty_actual: 6,
        qty_rejected: 0,
        ...(sku.is_batch_managed ? { batch_no: `DUPTEST${RUN_ID}`, expiry_date: isoDate(180) } : {}),
      },
    ],
  }
  record(
    '首次收货',
    await api('POST', `/inbound-orders/${dupCreate.id}/receive`, { idem: `ACC-${RUN_ID}-DUP-1`, body: recvBody }),
  )
  const beforeDup = await snapshotQty()
  const dupAgain = await api('POST', `/inbound-orders/${dupCreate.id}/receive`, {
    idem: `ACC-${RUN_ID}-DUP-2`,
    body: recvBody,
  })
  const afterDup = await snapshotQty()
  results.push({
    name: '异常③：重复收货 → 409 且不二次入账',
    pass: dupAgain.status === 409 && beforeDup === afterDup,
    detail: `HTTP ${dupAgain.status} ${dupAgain.data?.code ?? ''}，库存 ${beforeDup} → ${afterDup}`,
  })

  // 清理：把这张已收货的单上架掉，避免留在 RECEIVED 影响终检
  await api('POST', `/inbound-orders/${dupCreate.id}/putaway`, {
    idem: `ACC-${RUN_ID}-DUP-PUT`,
    body: { lines: [{ line_id: dupLine, to_location_id: ctx.storageLocs[0].id }] },
  })

  // 清理：把测试单取消，避免污染
  await api('POST', `/outbound-orders/${over.id}/cancel`, { idem: `ACC-${RUN_ID}-OVER-CANCEL` })
  return results
}

/* --------------------------- 并发不超卖（②） --------------------------- */

async function testConcurrency(ctx) {
  const { skus, storageLocs } = ctx
  const sku = skus.find((s) => s.is_batch_managed === false) ?? skus[1] ?? skus[0]
  const loc = storageLocs[0]

  /** 该 SKU 当前总可用量 */
  async function availOf() {
    const inv = await api('GET', '/inventory?page=1&page_size=100')
    return (inv.data?.items ?? [])
      .filter((r) => r.sku_id === sku.id)
      .reduce((s, r) => s + Number(r.qty_available), 0)
  }

  // 备货 20，确保有可竞争的库存（批次号仅对批次管理商品传）
  const create = record(
    '并发送货备货',
    await api('POST', '/inbound-orders', {
      body: { order_type: 'PO', supplier_name: '并发测试', lines: [{ sku_id: sku.id, qty_required: 20 }] },
    }),
  )
  record(
    '并发备货收货',
    await api('POST', `/inbound-orders/${create.id}/receive`, {
      idem: `ACC-${RUN_ID}-CONC-RECV`,
      body: {
        lines: [
          {
            line_id: create.lines[0].id,
            qty_actual: 20,
            qty_rejected: 0,
            ...(sku.is_batch_managed ? { batch_no: `CONC${RUN_ID}`, expiry_date: isoDate(180) } : {}),
          },
        ],
      },
    }),
  )
  record(
    '并发备货上架',
    await api('POST', `/inbound-orders/${create.id}/putaway`, {
      idem: `ACC-${RUN_ID}-CONC-PUT`,
      body: { lines: [{ line_id: create.lines[0].id, to_location_id: loc.id }] },
    }),
  )

  // 关键：按「当前可用量」动态定单量，保证两张单加起来一定超过可用量，
  // 否则历史上多轮连跑累积的库存会让两单都成功，测试就失去意义
  const avail = await availOf()
  if (avail < 2) throw new Error(`并发测试前置库存不足（可用 ${avail}）`)
  const need = Math.floor(avail * 0.6) + 1

  const mk = async (n) =>
    record(
      `并发建单 ${n}`,
      await api('POST', '/outbound-orders', {
        body: { order_type: 'SALE', priority: 100, lines: [{ sku_id: sku.id, qty_required: need }] },
      }),
    )
  const o1 = await mk(1)
  const o2 = await mk(2)

  const [r1, r2] = await Promise.all([
    api('POST', `/outbound-orders/${o1.id}/allocate`, { idem: `ACC-${RUN_ID}-CONC-A1` }),
    api('POST', `/outbound-orders/${o2.id}/allocate`, { idem: `ACC-${RUN_ID}-CONC-A2` }),
  ])
  const okCount = [r1, r2].filter((r) => r.ok).length

  // 关键断言：不看 qty_available（生成列可能滞后），直接比「已分配合计 vs 现有合计」
  const inv = await api('GET', '/inventory?page=1&page_size=100')
  const rows = inv.data?.items ?? []
  const skuRows = rows.filter((r) => r.sku_id === sku.id)
  const onHand = skuRows.reduce((s, r) => s + Number(r.qty_on_hand), 0)
  const allocated = skuRows.reduce((s, r) => s + Number(r.qty_allocated), 0)
  const overAllocated = allocated > onHand + 0.001

  // 清理
  const c1 = await api('POST', `/outbound-orders/${o1.id}/cancel`, { idem: `ACC-${RUN_ID}-CONC-C1` })
  const c2 = r2.ok
    ? await api('POST', `/outbound-orders/${o2.id}/cancel`, { idem: `ACC-${RUN_ID}-CONC-C2` })
    : null

  return [
    {
      name: `并发②：两单同时分配各 ${need}（当时可用 ${avail}），最多只能成一单且不得超卖`,
      pass: okCount === 1 && !overAllocated,
      detail:
        (overAllocated
          ? `⚠ 超卖：成功 ${okCount}/2 单后，已分配 ${allocated} > 现有 ${onHand}（超出 ${allocated - onHand}）`
          : `成功 ${okCount}/2 单，已分配 ${allocated} / 现有 ${onHand}，未超卖`) +
        `｜分配响应 ${r1.status}/${r2.status}，取消响应 ${c1.status}${c2 ? '/' + c2.status : ''}`,
    },
  ]
}

/** 全局库存量快照（用于断言「库存不变」） */
async function snapshotQty() {
  const inv = await api('GET', '/inventory?page=1&page_size=100')
  const rows = inv.data?.items ?? []
  const onHand = rows.reduce((s, r) => s + Number(r.qty_on_hand), 0)
  const alloc = rows.reduce((s, r) => s + Number(r.qty_allocated), 0)
  return `${onHand}/${alloc}`
}

/* ------------------------------ 终检 ------------------------------ */

async function finalChecks(ctx) {
  const checks = []

  // ① 对账 100% 一致
  const recon = await api('GET', '/inventory/recon')
  const items = recon.data?.items ?? []
  const bad = items.filter((r) => r.recon_status !== 'OK')
  checks.push({
    name: '验收①：账实一致率 100%',
    pass: recon.status === 200 && items.length > 0 && bad.length === 0,
    detail: `${items.length - bad.length}/${items.length} 条 OK${bad.length ? `，异常 ${bad.length} 条` : ''}`,
  })

  // ② 暂存位应归零（只用「本次新增」判断：现场数据本身可能已把货放在暂存位）
  const [locRes, invRes] = await Promise.all([
    api('GET', '/locations'),
    api('GET', '/inventory?page=1&page_size=100'),
  ])
  const locs = locRes.data?.items ?? []
  const stagingIds = new Set(
    locs.filter((l) => ['RECEIVING', 'STAGING'].includes(l.location_type)).map((l) => l.id),
  )
  const invRows = invRes.data?.items ?? []
  const stagingLeft = invRows
    .filter((r) => stagingIds.has(r.location_id))
    .map((r) => ({
      ...r,
      delta: Number(r.qty_on_hand) - (stagingBaseline.get(`${r.sku_id}@${r.location_id}`) ?? 0),
    }))
    .filter((r) => r.delta > 0)
  checks.push({
    name: '暂存位归零（本次运行未在收货/发货暂存留残货）',
    pass: stagingLeft.length === 0,
    detail: stagingLeft.length
      ? `${stagingLeft.length} 条新增残留：` +
        stagingLeft.map((r) => `${r.sku_code}@${r.location_code}=${r.delta}`).join(', ')
      : `${stagingIds.size} 个暂存位无新增残留`,
  })

  // ③ 无负库存
  const negative = invRows.filter(
    (r) => Number(r.qty_on_hand) < 0 || Number(r.qty_available) < 0 || Number(r.qty_allocated) < 0,
  )
  checks.push({
    name: '无负库存 / 负可用量',
    pass: negative.length === 0,
    detail: negative.length ? `${negative.length} 条为负` : `${invRows.length} 个维度全部非负`,
  })

  // ④ 可用 = 现有 − 已分配（账本口径自洽）
  const broken = invRows.filter(
    (r) => Math.abs(Number(r.qty_on_hand) - Number(r.qty_allocated) - Number(r.qty_available)) > 0.001,
  )
  checks.push({
    name: '可用 = 现有 − 已分配（口径自洽）',
    pass: broken.length === 0,
    detail: broken.length ? `${broken.length} 条不成立` : `${invRows.length} 个维度全部成立`,
  })

  // ⑤ 单据终态（只看本次运行创建的单据，避免历史残留干扰）
  const [inbRes, outRes] = await Promise.all([
    api('GET', '/inbound-orders?page=1&page_size=100'),
    api('GET', '/outbound-orders?page=1&page_size=100'),
  ])
  const myInb = (inbRes.data?.items ?? []).filter((o) => stats.inboundIds.includes(o.id))
  const myOut = (outRes.data?.items ?? []).filter((o) => stats.outboundIds.includes(o.id))
  const inbBad = myInb.filter((o) => !['DONE', 'CANCELLED'].includes(o.status))
  const outBad = myOut.filter((o) => !['SHIPPED', 'CANCELLED'].includes(o.status))
  checks.push({
    name: '本次单据无卡死状态（入库全 DONE/CANCELLED、出库全 SHIPPED/CANCELLED）',
    pass: inbBad.length === 0 && outBad.length === 0,
    detail: `入库 ${myInb.length} 张异常 ${inbBad.length}；出库 ${myOut.length} 张异常 ${outBad.length}` +
      (inbBad.length || outBad.length
        ? `｜异常：${[...inbBad, ...outBad].map((o) => `${o.order_no}(${o.status})`).join(', ')}`
        : ''),
  })

  return checks
}

/* ------------------------------ 输出 ------------------------------ */

function line(char = '─', n = 76) {
  return char.repeat(n)
}

function printReport(anomalyResults, concurrencyResults, checks) {
  console.log('\n' + line('═'))
  console.log('P1 验收报告')
  console.log(line('═'))

  console.log('\n【数据量】')
  console.log(`  连跑轮次        ${ROUNDS} 轮`)
  console.log(`  入库单（创建/完成）  ${stats.inboundCreated} / ${stats.inboundDone}`)
  console.log(`  出库单（创建/发运）  ${stats.outboundCreated} / ${stats.outboundShipped}`)
  console.log(`  接口调用次数      ${stats.steps} 次（异常场景与并发另计）`)

  console.log('\n【异常与并发】')
  for (const r of [...anomalyResults, ...concurrencyResults]) {
    console.log(`  ${r.pass ? '✅' : '❌'} ${r.name}`)
    console.log(`      ${r.detail}`)
  }

  console.log('\n【终检】')
  for (const c of checks) {
    console.log(`  ${c.pass ? '✅' : '❌'} ${c.name}`)
    console.log(`      ${c.detail}`)
  }

  const all = [...anomalyResults, ...concurrencyResults, ...checks]
  const failed = all.filter((r) => !r.pass)
  console.log('\n' + line())
  if (failed.length === 0) {
    console.log(`结论：全部通过（${all.length}/${all.length}）→ P1 验收达标`)
  } else {
    console.log(`结论：${all.length - failed.length}/${all.length} 通过，${failed.length} 项失败：`)
    for (const f of failed) console.log(`  - ${f.name}：${f.detail}`)
  }
  console.log(line())
  return failed.length === 0
}

/* ------------------------------ 入口 ------------------------------ */

;(async () => {
  console.log(line('═'))
  console.log(`P1 验收：${ROUNDS} 单连跑 + 异常场景 + 并发不超卖`)
  console.log(`目标后端：${BASE}`)
  console.log(line('═'))

  try {
    await login()
    const ctx = await loadMaster()
    console.log(`主数据：${ctx.skus.length} 个 SKU、${ctx.storageLocs.length} 个存储位\n`)
    await captureStagingBaseline()

    console.log('【一、连跑】')
    for (let i = 0; i < ROUNDS; i++) {
      await runRound(i, ctx)
    }

    console.log('\n【二、异常场景（可回滚）】')
    const anomalyResults = await testAnomalies(ctx)
    for (const r of anomalyResults) console.log(`  ${r.pass ? '✅' : '❌'} ${r.name}｜${r.detail}`)

    console.log('\n【三、并发不超卖】')
    const concurrencyResults = await testConcurrency(ctx)
    for (const r of concurrencyResults) console.log(`  ${r.pass ? '✅' : '❌'} ${r.name}｜${r.detail}`)

    const checks = await finalChecks(ctx)
    const pass = printReport(anomalyResults, concurrencyResults, checks)
    process.exit(pass ? 0 : 1)
  } catch (e) {
    console.error('\n❌ 执行中断：', e.message)
    console.error('   排查提示：确认后端已启动（bash scripts/dev.sh up）、数据库已初始化（dev.sh db-init）')
    process.exit(1)
  }
})()
