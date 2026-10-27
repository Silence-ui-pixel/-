// =============================================================================
// MSW Mock 数据（开发环境假数据）
// 字段严格对齐 contracts/openapi.yaml（snake_case），显式标注契约 schema 类型，
// 让数组元素保持完整契约类型（status/order_type 为完整联合），改契约写错即被 vue-tsc 报出。
// =============================================================================

import type { components } from '@/api/schema'

type S = components['schemas']

// 商品主数据
export const skus: S['Sku'][] = [
  { id: 1, sku_code: 'SKU-1001', barcode: '690000000001', name: '矿泉水 500ml', spec: '24瓶/箱', category: '饮料', base_uom: 'EA', is_batch_managed: false, abc_class: 'A', safety_stock: 100, reorder_point: 200, status: 1, created_at: '2026-10-01T08:00:00Z', updated_at: '2026-10-01T08:00:00Z' },
  { id: 2, sku_code: 'SKU-1002', barcode: '690000000002', name: '纯牛奶 250ml', spec: '16盒/箱', category: '乳品', base_uom: 'EA', is_batch_managed: true, abc_class: 'A', safety_stock: 80, reorder_point: 160, status: 1, created_at: '2026-10-01T08:00:00Z', updated_at: '2026-10-01T08:00:00Z' },
  { id: 3, sku_code: 'SKU-1003', barcode: '690000000003', name: '抽纸 3层', spec: '10包/提', category: '日用品', base_uom: 'EA', is_batch_managed: false, abc_class: 'B', safety_stock: 60, reorder_point: 120, status: 1, created_at: '2026-10-01T08:00:00Z', updated_at: '2026-10-01T08:00:00Z' },
  { id: 4, sku_code: 'SKU-1004', barcode: '690000000004', name: '方便面 红烧牛肉', spec: '24袋/箱', category: '食品', base_uom: 'EA', is_batch_managed: true, abc_class: 'C', safety_stock: 50, reorder_point: 100, status: 1, created_at: '2026-10-01T08:00:00Z', updated_at: '2026-10-01T08:00:00Z' },
]

// 库位（编码与 db/seed.sql 一致：契约 v1.3 起 location_code = bin_code）
export const locations: S['Location'][] = [
  { id: 1, warehouse_code: 'WH01', zone_code: 'A', rack_code: '01', level_no: 1, bin_code: 'A0101', location_code: 'A0101', location_type: 'STORAGE', pick_seq: 1, status: 1 },
  { id: 2, warehouse_code: 'WH01', zone_code: 'A', rack_code: '01', level_no: 2, bin_code: 'A0102', location_code: 'A0102', location_type: 'STORAGE', pick_seq: 2, status: 1 },
  { id: 3, warehouse_code: 'WH01', zone_code: 'B', rack_code: '02', level_no: 1, bin_code: 'B0201', location_code: 'B0201', location_type: 'STORAGE', pick_seq: 3, status: 1 },
  { id: 4, warehouse_code: 'WH01', zone_code: 'C', rack_code: '01', level_no: 1, bin_code: 'C0101', location_code: 'C0101', location_type: 'RECEIVING', pick_seq: null, status: 1 },
  { id: 5, warehouse_code: 'WH01', zone_code: 'C', rack_code: '02', level_no: 1, bin_code: 'C0201', location_code: 'C0201', location_type: 'STAGING', pick_seq: null, status: 1 },
]

// 库存余额（InventoryItem：已含 sku/location 联表展示字段）
export const inventoryItems: S['InventoryItem'][] = [
  { sku_id: 1, sku_code: 'SKU-1001', sku_name: '矿泉水 500ml', spec: '24瓶/箱', location_id: 1, location_code: 'A0101', location_type: 'STORAGE', batch_no: '', expiry_date: '9999-12-30', qty_on_hand: 500, qty_allocated: 50, qty_available: 450, base_uom: 'EA' },
  { sku_id: 2, sku_code: 'SKU-1002', sku_name: '纯牛奶 250ml', spec: '16盒/箱', location_id: 2, location_code: 'A0102', location_type: 'STORAGE', batch_no: 'B20260920', expiry_date: '2026-11-20', qty_on_hand: 300, qty_allocated: 120, qty_available: 180, base_uom: 'EA' },
  { sku_id: 2, sku_code: 'SKU-1002', sku_name: '纯牛奶 250ml', spec: '16盒/箱', location_id: 2, location_code: 'A0102', location_type: 'STORAGE', batch_no: 'B20261001', expiry_date: '2026-12-01', qty_on_hand: 200, qty_allocated: 0, qty_available: 200, base_uom: 'EA' },
  { sku_id: 3, sku_code: 'SKU-1003', sku_name: '抽纸 3层', spec: '10包/提', location_id: 3, location_code: 'B0201', location_type: 'STORAGE', batch_no: '', expiry_date: '9999-12-30', qty_on_hand: 800, qty_allocated: 0, qty_available: 800, base_uom: 'EA' },
  { sku_id: 1, sku_code: 'SKU-1001', sku_name: '矿泉水 500ml', spec: '24瓶/箱', location_id: 4, location_code: 'C0101', location_type: 'RECEIVING', batch_no: 'B20261025', expiry_date: '9999-12-30', qty_on_hand: 200, qty_allocated: 0, qty_available: 200, base_uom: 'EA' },
]

// 库存流水
export const stockTxns: S['StockTxnItem'][] = [
  { id: 1, txn_no: 'IB-20261001-001-RECEIPT', txn_type: 'RECEIPT', sku_id: 1, sku_code: 'SKU-1001', location_code: 'C0101', batch_no: 'B20261025', expiry_date: '9999-12-31', on_hand_delta: 200, allocated_delta: 0, before_on_hand: 0, after_on_hand: 200, ref_type: 'INBOUND', ref_id: 2, source: 'PDA', created_at: '2026-10-25T09:30:00Z' },
  { id: 2, txn_no: 'OB-20261020-001-ALLOCATE', txn_type: 'ALLOCATE', sku_id: 2, sku_code: 'SKU-1002', location_code: 'A0102', batch_no: 'B20260920', expiry_date: '2026-11-20', on_hand_delta: 0, allocated_delta: 120, before_on_hand: 300, after_on_hand: 300, ref_type: 'OUTBOUND', ref_id: 1, source: 'WEB', created_at: '2026-10-24T15:00:00Z' },
  { id: 3, txn_no: 'OB-20261020-001-PICK', txn_type: 'PICK', sku_id: 2, sku_code: 'SKU-1002', location_code: 'A0102', batch_no: 'B20260920', expiry_date: '2026-11-20', on_hand_delta: 0, allocated_delta: -120, before_on_hand: 300, after_on_hand: 300, ref_type: 'OUTBOUND', ref_id: 1, source: 'PDA', created_at: '2026-10-24T16:00:00Z' },
  { id: 4, txn_no: 'OB-20261020-001-SHIP', txn_type: 'SHIP', sku_id: 2, sku_code: 'SKU-1002', location_code: 'A0102', batch_no: 'B20260920', expiry_date: '2026-11-20', on_hand_delta: -120, allocated_delta: 0, before_on_hand: 300, after_on_hand: 180, ref_type: 'OUTBOUND', ref_id: 1, source: 'WEB', created_at: '2026-10-24T17:00:00Z' },
  { id: 5, txn_no: 'ADJ-20261025-001', txn_type: 'ADJUST', sku_id: 3, sku_code: 'SKU-1003', location_code: 'B0201', batch_no: '', expiry_date: '9999-12-31', on_hand_delta: 50, allocated_delta: 0, before_on_hand: 750, after_on_hand: 800, ref_type: 'MANUAL', source: 'WEB', created_at: '2026-10-25T10:00:00Z' },
]

// 对账视图
export const reconItems: S['ReconItem'][] = [
  { sku_id: 1, location_id: 1, batch_no: '', expiry_date: '9999-12-31', inv_on_hand: 500, txn_on_hand: 500, diff_on_hand: 0, recon_status: 'OK' },
  { sku_id: 4, location_id: 3, batch_no: 'B20261010', expiry_date: '2026-11-10', inv_on_hand: 100, txn_on_hand: 90, diff_on_hand: 10, recon_status: 'MISMATCH' },
]

// 入库单
export const inboundOrders: S['InboundOrder'][] = [
  { id: 1, order_no: 'IB-20261025-001', order_type: 'PO', supplier_name: '农夫山泉华东仓', status: 'DRAFT', expected_at: '2026-10-28', total_expected_qty: 1000, total_received_qty: 0, remark: '双十一备货', created_at: '2026-10-25T08:00:00Z', updated_at: '2026-10-25T08:00:00Z' },
  { id: 2, order_no: 'IB-20261025-002', order_type: 'PO', supplier_name: '伊利乳品仓', status: 'RECEIVED', expected_at: '2026-10-26', total_expected_qty: 500, total_received_qty: 200, remark: null, created_at: '2026-10-25T09:00:00Z', updated_at: '2026-10-25T09:30:00Z' },
  { id: 3, order_no: 'IB-20261020-001', order_type: 'RETURN', supplier_name: '退货仓', status: 'DONE', expected_at: '2026-10-22', total_expected_qty: 50, total_received_qty: 50, remark: null, created_at: '2026-10-20T10:00:00Z', updated_at: '2026-10-20T12:00:00Z' },
]

// 入库单明细
export const inboundLines: S['OrderLine'][] = [
  { id: 101, line_no: 1, sku_id: 1, sku_code: 'SKU-1001', sku_name: '矿泉水 500ml', qty_required: 600, qty_actual: 0, qty_rejected: 0, batch_no: '', expiry_date: '9999-12-31', status: 'OPEN' },
  { id: 102, line_no: 2, sku_id: 2, sku_code: 'SKU-1002', sku_name: '纯牛奶 250ml', qty_required: 400, qty_actual: 0, qty_rejected: 0, batch_no: '', expiry_date: '9999-12-31', status: 'OPEN' },
  { id: 201, line_no: 1, sku_id: 1, sku_code: 'SKU-1001', sku_name: '矿泉水 500ml', qty_required: 500, qty_actual: 200, qty_rejected: 0, batch_no: 'B20261025', expiry_date: '9999-12-31', status: 'PARTIAL' },
]

// 出库单
export const outboundOrders: S['OutboundOrder'][] = [
  { id: 1, order_no: 'OB-20261025-001', order_type: 'SALE', customer_name: '天猫超市', status: 'DRAFT', priority: 100, total_qty: 300, requested_ship_at: '2026-10-29', remark: '加急', created_at: '2026-10-25T08:00:00Z', updated_at: '2026-10-25T08:00:00Z' },
  { id: 2, order_no: 'OB-20261024-001', order_type: 'SALE', customer_name: '京东自营', status: 'ALLOCATED', priority: 80, total_qty: 120, requested_ship_at: '2026-10-28', remark: null, created_at: '2026-10-24T10:00:00Z', updated_at: '2026-10-24T15:00:00Z' },
  { id: 3, order_no: 'OB-20261020-001', order_type: 'SALE', customer_name: '社区团购', status: 'SHIPPED', priority: 90, total_qty: 120, requested_ship_at: '2026-10-24', remark: null, created_at: '2026-10-20T09:00:00Z', updated_at: '2026-10-20T17:00:00Z' },
]

// 出库单明细
export const outboundLines: S['OrderLine'][] = [
  { id: 301, line_no: 1, sku_id: 1, sku_code: 'SKU-1001', sku_name: '矿泉水 500ml', qty_required: 200, qty_actual: 0, qty_rejected: 0, batch_no: '', expiry_date: '9999-12-31', status: 'OPEN' },
  { id: 302, line_no: 2, sku_id: 2, sku_code: 'SKU-1002', sku_name: '纯牛奶 250ml', qty_required: 100, qty_actual: 0, qty_rejected: 0, batch_no: '', expiry_date: '9999-12-31', status: 'OPEN' },
  { id: 401, line_no: 1, sku_id: 2, sku_code: 'SKU-1002', sku_name: '纯牛奶 250ml', qty_required: 120, qty_actual: 0, qty_rejected: 0, batch_no: 'B20260920', expiry_date: '2026-11-20', status: 'ALLOCATED' },
]

// 拣货计划（出库分配后返回的拣货路径）
export const pickPlan: S['PickPlanResponse'] = {
  lines: [
    { line_id: 401, sku_id: 2, sku_code: 'SKU-1002', sku_name: '纯牛奶 250ml', location_id: 2, location_code: 'A0102', qty_required: 120, batch_no: 'B20260920', expiry_date: '2026-11-20' },
  ],
}
