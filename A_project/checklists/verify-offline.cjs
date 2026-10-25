#!/usr/bin/env node
/* ---------------------------------------------------------------
 * schema.sql / seed.sql 离线验证（无需 Docker）
 *
 * 原理：PGlite 是编译成 WASM 的真实 PostgreSQL 引擎（非模拟）。
 *      在内存里起一个库，跑完整建库脚本，逐项断言。
 *
 * 定位：随时能跑的快速自检。它不能替代真实 PG 16 验证
 *      （WASM 版对扩展、并发、锁行为支持有限），
 *      最终结论仍以 checklists/verify-schema.sh 为准。
 *
 * 用法：
 *   node A_project/checklists/verify-offline.cjs
 *
 * 依赖（若未安装）：
 *   cd C:/Users/<you>/.workbuddy/binaries/node/workspace
 *   npm install @electric-sql/pglite
 * --------------------------------------------------------------- */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const SCHEMA = path.join(ROOT, 'db/schema.sql');
const SEED = path.join(ROOT, 'db/seed.sql');

function loadPGlite() {
  const candidates = [
    '@electric-sql/pglite',
    path.join(
      process.env.LOCALAPPDATA || '',
      '..',
      '.workbuddy/binaries/node/workspace/node_modules/@electric-sql/pglite'
    ),
  ];
  for (const c of candidates) {
    try { return require(c); } catch (_) { /* 继续尝试 */ }
  }
  console.error(
    '\n找不到 @electric-sql/pglite。安装方法：\n' +
    '  cd C:/Users/<you>/.workbuddy/binaries/node/workspace\n' +
    '  npm install @electric-sql/pglite\n' +
    '然后用 NODE_PATH 指向该 node_modules 运行本脚本。\n\n' +
    '或者直接用 Docker 版：bash A_project/checklists/verify-schema.sh\n'
  );
  process.exit(2);
}

const { PGlite } = loadPGlite();

let fail = 0;
const ok = (m) => console.log('  \x1b[32m[ OK ]\x1b[0m ' + m);
const bad = (m) => { console.log('  \x1b[31m[FAIL]\x1b[0m ' + m); fail++; };
const step = (m) => console.log('\n\x1b[1m' + m + '\x1b[0m');

(async () => {
  for (const f of [SCHEMA, SEED]) {
    if (!fs.existsSync(f)) {
      console.error('找不到文件：' + f);
      process.exit(2);
    }
  }
  const schemaSql = fs.readFileSync(SCHEMA, 'utf8');
  const seedSql = fs.readFileSync(SEED, 'utf8');
  const db = await PGlite.create();

  // ---- 1. DDL ----
  step('1 / 6  执行 schema.sql（DDL）');
  try {
    await db.exec(schemaSql);
    ok('全部语句执行成功');
  } catch (e) {
    bad('执行中断：' + e.message.split('\n')[0]);
    if (e.position) console.log('      出错位置（字符偏移）：' + e.position);
    console.log('\n修复后重跑。D3 的模型评审不能建立在跑不起来的设计上。');
    await db.close();
    process.exit(1);
  }

  const tb = (await db.query(
    "select count(*)::int c from information_schema.tables where table_schema='public' and table_type='BASE TABLE'"
  )).rows[0].c;
  tb >= 8 ? ok(`基础表 ${tb} 张`) : bad(`表数量不足 8（实际 ${tb}）`);

  const vw = (await db.query(
    "select count(*)::int c from information_schema.views where table_schema='public' and table_name='v_inventory_recon'"
  )).rows[0].c;
  vw === 1 ? ok('对账视图 v_inventory_recon 存在') : bad('对账视图缺失');

  const tg = (await db.query(
    "select count(*)::int c from pg_trigger t join pg_class c on c.oid=t.tgrelid where not t.tgisinternal and c.relname='stock_txn'"
  )).rows[0].c;
  tg >= 1 ? ok(`stock_txn 上有 ${tg} 个触发器`) : bad('stock_txn 缺少只追加触发器');

  // ---- 2. 播种 ----
  step('2 / 6  执行 seed.sql（首次）');
  try { await db.exec(seedSql); ok('首次播种成功'); }
  catch (e) { bad('播种失败：' + e.message.split('\n')[0]); }

  const inv1 = (await db.query('select count(*)::int c from inventory')).rows[0].c;
  const txn1 = (await db.query('select count(*)::int c from stock_txn')).rows[0].c;
  inv1 === 1 ? ok('inventory 1 行') : bad('inventory 行数 = ' + inv1);
  txn1 === 1 ? ok('stock_txn 1 行') : bad('stock_txn 行数 = ' + txn1);

  // ---- 3. 幂等（连跑两次）----
  step('3 / 6  幂等性：seed.sql 再执行两次');
  for (let i = 2; i <= 3; i++) {
    try { await db.exec(seedSql); ok(`第 ${i} 次执行成功`); }
    catch (e) { bad(`第 ${i} 次执行失败：` + e.message.split('\n')[0]); }
  }
  const inv2 = (await db.query('select count(*)::int c from inventory')).rows[0].c;
  const txn2 = (await db.query('select count(*)::int c from stock_txn')).rows[0].c;
  const qty = (await db.query('select qty_on_hand::int q from inventory')).rows[0].q;
  inv2 === 1 ? ok('inventory 仍 1 行（未重复插入）') : bad('inventory 行数变成 ' + inv2);
  txn2 === 1 ? ok('stock_txn 仍 1 行（未重复记流水）') : bad('stock_txn 行数变成 ' + txn2);
  qty === 200 ? ok('qty_on_hand 仍 200（未重复累加）') : bad('qty_on_hand 变成 ' + qty);

  // ---- 4. 对账 ----
  step('4 / 6  余额与流水对账');
  const recon = (await db.query('select recon_status, count(*)::int n from v_inventory_recon group by 1')).rows;
  recon.forEach((r) => console.log(`      ${r.recon_status}  ${r.n} 行`));
  recon.length === 1 && recon[0].recon_status === 'OK'
    ? ok('全部 OK，账实一致')
    : bad('存在对账异常：' + JSON.stringify(recon));

  // ---- 5. 只追加保护 ----
  step('5 / 6  历史流水不可篡改');
  for (const [label, stmt] of [
    ['UPDATE', 'update stock_txn set after_on_hand = after_on_hand'],
    ['DELETE', 'delete from stock_txn'],
  ]) {
    try { await db.exec(stmt); bad(`${label} 竟然成功了 —— 审计链可被破坏`); }
    catch (e) { ok(`${label} 被触发器拦下：${e.message.split('\n')[0].slice(0, 40)}`); }
  }

  // ---- 6. 约束 ----
  step('6 / 6  关键业务约束');

  // 快照不自洽
  try {
    await db.exec(`insert into stock_txn (txn_no,txn_type,sku_id,location_id,batch_no,expiry_date,
      on_hand_delta,allocated_delta,before_on_hand,after_on_hand,source)
      select 'BAD-1','ADJUST',sku_id,location_id,batch_no,expiry_date,10,0,100,999,'MANUAL'
        from inventory limit 1`);
    bad('快照不自洽的流水插入成功（before + delta <> after 未被拦住）');
  } catch (e) { ok('快照不自洽被 CHECK 拦下'); }

  // 负库存
  try { await db.exec('update inventory set qty_on_hand = -5'); bad('负库存写入成功'); }
  catch (e) { ok('负库存被 CHECK 拦下'); }

  // 重复维度
  try {
    await db.exec(`insert into inventory (sku_id,location_id,batch_no,expiry_date,qty_on_hand)
      select sku_id,location_id,batch_no,expiry_date,0 from inventory limit 1`);
    bad('同一 SKU+库位+批次 插入两行成功（唯一约束失效，库存会算错）');
  } catch (e) { ok('重复库存维度被 uk_inventory_dim 拦下'); }

  // NULL 维度
  try {
    await db.exec(`insert into inventory (sku_id,location_id,batch_no,expiry_date,qty_on_hand)
      select sku_id,location_id,null,expiry_date,0 from inventory limit 1`);
    bad('batch_no 允许 NULL —— 唯一约束会对 NULL 行失效');
  } catch (e) { ok('batch_no 的 NULL 被 NOT NULL 拦下（哨兵值设计生效）'); }

  // 生成列
  const gen = (await db.query(
    "select column_name from information_schema.columns where table_name='inventory' and is_generated='ALWAYS'"
  )).rows.map((r) => r.column_name);
  gen.length ? ok('生成列正常：' + gen.join(', ')) : bad('生成列缺失');

  await db.close();

  console.log('\n----------------------------------------------');
  if (fail === 0) {
    console.log('\x1b[32m全部通过\x1b[0m · schema.sql + seed.sql 可在真实 PG 引擎落地，D3 评审结论有效。');
    process.exit(0);
  } else {
    console.log(`\x1b[31m${fail} 项未通过\x1b[0m · 先修脚本，再让 D3 评审它。`);
    process.exit(1);
  }
})().catch((e) => {
  console.error('FATAL', e.message || e);
  process.exit(2);
});
