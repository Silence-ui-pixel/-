#!/usr/bin/env bash
# ---------------------------------------------------------------
# 在真实 PostgreSQL 16 上验证 db/schema.sql + db/seed.sql
# 用途：Sprint 1 环境预检（A 成员的第一件事）
#
# 用法：
#   bash A_project/checklists/verify-schema.sh
#   PORT=55433 bash .../verify-schema.sh      # 5432/55432 被占用时换端口
#   KEEP=1 bash .../verify-schema.sh          # 保留容器，便于手工排查
#
# 它做四件事：起临时库 → 建结构 → 播种两次（验证幂等）→ 检查对象与对账
# 不修改仓库里的任何文件，失败也保留现场（除非 KEEP=0 且成功）
# ---------------------------------------------------------------

set -uo pipefail

CONTAINER="canku-pg-check"
PORT="${PORT:-55432}"
PGPASS="canku_check_pw"
DBNAME="canku_check"
IMAGE="postgres:16"
KEEP="${KEEP:-0}"
# 默认不向宿主机发布端口。
# 原因：本脚本全部通过 docker exec 在容器内执行 psql，根本不需要从宿主机连；
# 而 Windows + Docker Desktop 下 Hyper-V/WinNAT 会保留大量端口段
# （netsh interface ipv4 show excludedportrange protocol=tcp 可查），
# 一旦选中的端口落在保留段里，docker run 会直接报 access permissions 失败。
# 需要外部客户端连进来时：PUBLISH=1 bash ...（脚本会自动避开保留段）
PUBLISH="${PUBLISH:-0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCHEMA="$ROOT/db/schema.sql"
SEED="$ROOT/db/seed.sql"

FAIL=0
ok()   { printf '  \033[32m[ OK ]\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m[FAIL]\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33m[WARN]\033[0m %s\n' "$1"; }
step() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# 判断端口是否落在 Windows 排除段内（非 Windows 环境恒返回「不排除」）
port_excluded() {
  local p="$1"
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) ;;
    *) return 1 ;;
  esac
  netsh interface ipv4 show excludedportrange protocol=tcp 2>/dev/null \
    | tr -d '\r' \
    | awk -v p="$p" '$1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && p+0 >= $1+0 && p+0 <= $2+0 { f=1 } END { exit(f?0:1) }'
}

cleanup() {
  if [ "$KEEP" = "1" ]; then
    printf '\n容器已保留：%s（库 %s）\n' "$CONTAINER" "$DBNAME"
    printf '进容器排查：docker exec -it %s psql -U postgres -d %s\n' "$CONTAINER" "$DBNAME"
    [ "$PUBLISH" = "1" ] && printf '宿主机连接：psql "host=127.0.0.1 port=%s user=postgres dbname=%s"\n' "$PORT" "$DBNAME"
    printf '清理：docker rm -f %s\n' "$CONTAINER"
  else
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# ---------- 0. 前置检查 ----------
step "0 / 6  前置检查"

if ! command -v docker >/dev/null 2>&1; then
  printf '  未找到 docker。请先安装 Docker Desktop 并启动，或改用本地 psql 手工执行（见 D1-环境预检.md）。\n'
  exit 2
fi

if ! docker info >/dev/null 2>&1; then
  printf '  Docker 已安装但守护进程没起来。请先启动 Docker Desktop，等状态变成 Running 再重跑。\n'
  exit 2
fi
ok "docker 可用：$(docker --version | cut -d, -f1)"

if [ ! -f "$SCHEMA" ]; then
  printf '  找不到 %s\n' "$SCHEMA"
  exit 2
fi
ok "schema.sql 存在：$(wc -l < "$SCHEMA" | tr -d ' ') 行"

# ---------- 1. 起临时库 ----------
step "1 / 6  启动临时 PostgreSQL 16"

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

RUN_ARGS=(-d --name "$CONTAINER" -e POSTGRES_PASSWORD="$PGPASS" -e POSTGRES_DB="$DBNAME")
if [ "$PUBLISH" = "1" ]; then
  # Windows 的保留段常常连续覆盖几百个端口（本机实测 55348–56247 连续 900 个），
  # 所以不能只做「起始端口 +N」的线性探测，必须优先退回常规端口。
  PICKED=""
  for CAND in "$PORT" 5432 5433 15432 25432 45432 35432; do
    if ! port_excluded "$CAND"; then PICKED="$CAND"; break; fi
  done
  if [ -z "$PICKED" ]; then
    bad "候选端口（$PORT / 5432 / 5433 / 15432 / 25432 / 45432 / 35432）都在 Windows 保留段内"
    printf '      查证：netsh interface ipv4 show excludedportrange protocol=tcp\n'
    printf '      处理：用 PORT=xxxxx 指定一个不在保留段内的端口；\n'
    printf '            或以管理员身份 net stop winnat && net start winnat 释放保留段。\n'
    printf '            注意：本脚本默认不需要发布端口，直接重跑即可。\n'
    exit 1
  fi
  if [ "$PICKED" != "$PORT" ]; then
    printf '  端口 %s 在 Windows 保留段内，自动避开，改用 %s\n' "$PORT" "$PICKED"
  fi
  PORT="$PICKED"
  RUN_ARGS+=(-p "127.0.0.1:$PORT:5432")
  printf '  发布宿主机端口：127.0.0.1:%s\n' "$PORT"
else
  printf '  不发布宿主机端口（全部操作走 docker exec，不需要暴露）\n'
fi

RUN_ERR=$(docker run "${RUN_ARGS[@]}" "$IMAGE" 2>&1)
if [ $? -ne 0 ]; then
  bad "容器启动失败，Docker 原始报错："
  printf '%s\n' "$RUN_ERR" | sed 's/^/      /'
  printf '\n'
  if printf '%s' "$RUN_ERR" | grep -qi "access permissions\|ports are not available"; then
    printf '  诊断：宿主机端口被 Windows 保留段占用（Hyper-V / WinNAT 动态端口），不是 Docker 坏了。\n'
    printf '  查证：netsh interface ipv4 show excludedportrange protocol=tcp\n'
    printf '  处理：脚本默认不发布端口，直接重跑即可；确实要发布就用 PUBLISH=1 自动避让，\n'
    printf '        或用管理员 PowerShell 执行 net stop winnat && net start winnat 后再试。\n'
  elif printf '%s' "$RUN_ERR" | grep -qi "already in use by container"; then
    printf '  诊断：同名容器已存在。执行 docker rm -f %s 后重跑。\n' "$CONTAINER"
  elif printf '%s' "$RUN_ERR" | grep -qi "no such image\|pull access denied"; then
    printf '  诊断：本地没有 %s 镜像。执行 docker pull %s 后重跑。\n' "$IMAGE" "$IMAGE"
  elif printf '%s' "$RUN_ERR" | grep -qi "cannot connect\|pipe"; then
    printf '  诊断：Docker 守护进程未就绪。等 Docker Desktop 显示 Running 后重跑。\n'
  else
    printf '  未能识别的错误，请把上面这段原始报错发出来。\n'
  fi
  exit 1
fi

printf '  等待数据库就绪'
READY=0
for _ in $(seq 1 60); do
  if docker exec "$CONTAINER" pg_isready -U postgres -d "$DBNAME" >/dev/null 2>&1; then
    READY=1; break
  fi
  printf '.'; sleep 1
done
printf '\n'

if [ "$READY" != "1" ]; then
  bad "数据库 60 秒内未就绪"
  docker logs --tail 20 "$CONTAINER" 2>&1 | sed 's/^/      /'
  exit 1
fi
if [ "$PUBLISH" = "1" ]; then
  ok "数据库就绪（postgres:16 · 容器 $CONTAINER · 宿主机 127.0.0.1:$PORT）"
else
  ok "数据库就绪（postgres:16 · 容器 $CONTAINER · 仅容器内可达）"
fi

# ---------- 2. 执行 schema.sql ----------
step "2 / 6  执行 schema.sql（ON_ERROR_STOP=1，遇错即停）"

if docker exec -i "$CONTAINER" psql -v ON_ERROR_STOP=1 -q -U postgres -d "$DBNAME" -f - < "$SCHEMA" >/tmp/canku_schema_out.txt 2>/tmp/canku_schema_err.txt; then
  ok "全部语句执行成功"
  if [ -s /tmp/canku_schema_err.txt ]; then
    printf '      仅存在 NOTICE 级提示，非错误：\n'
    sed 's/^/      /' /tmp/canku_schema_err.txt | head -8
  fi
else
  bad "执行中断，错误如下："
  sed 's/^/      /' /tmp/canku_schema_err.txt | head -25
  printf '\n      定位建议：上面的行号对应 schema.sql 的物理行。\n'
  printf '      常见原因：外键指向的表还没建（调整语句顺序）、生成列用了非 immutable 函数、\n'
  printf '                唯一约束含 NULL 列导致种子数据重复插入。\n'
  exit 1
fi

# ---------- 3. 种子数据 + 幂等 ----------
step "3 / 6  执行 seed.sql 两次（验证可重复导入）"

if [ ! -f "$SEED" ]; then
  bad "找不到 $SEED"
else
  for i in 1 2; do
    if docker exec -i "$CONTAINER" psql -v ON_ERROR_STOP=1 -q -U postgres -d "$DBNAME" -f - < "$SEED" \
         >/dev/null 2>/tmp/canku_seed_err.txt; then
      ok "第 $i 次播种成功"
    else
      bad "第 $i 次播种失败：$(head -1 /tmp/canku_seed_err.txt)"
    fi
  done
  INV=$(docker exec "$CONTAINER" psql -tAq -U postgres -d "$DBNAME" -c "select count(*) from inventory" 2>/dev/null | tr -d '\r')
  TXN=$(docker exec "$CONTAINER" psql -tAq -U postgres -d "$DBNAME" -c "select count(*) from stock_txn" 2>/dev/null | tr -d '\r')
  [ "${INV:-0}" = "1" ] && ok "inventory 仍 1 行（未重复插入）" || bad "inventory 行数 = ${INV:-?}，种子数据不幂等"
  [ "${TXN:-0}" = "1" ] && ok "stock_txn 仍 1 行（未重复记流水）" || bad "stock_txn 行数 = ${TXN:-?}，期初库存被重复累加"
fi

# ---------- 4. 对象检查 ----------
step "4 / 6  检查关键对象是否就位"

q() { docker exec "$CONTAINER" psql -tAq -U postgres -d "$DBNAME" -c "$1" 2>/dev/null | tr -d '\r'; }

TB=$(q "select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE'")
printf '  基础表数量：%s\n' "$TB"
if [ "${TB:-0}" -ge 8 ] 2>/dev/null; then ok "表数量 >= 8"; else bad "表数量不足 8（实际 ${TB:-0}）"; fi

VIEW=$(q "select count(*) from information_schema.views where table_schema='public' and table_name='v_inventory_recon'")
if [ "${VIEW:-0}" = "1" ]; then ok "对账视图 v_inventory_recon 存在"; else bad "对账视图 v_inventory_recon 缺失"; fi

TRG=$(q "select count(*) from pg_trigger t join pg_class c on c.oid=t.tgrelid
         where not t.tgisinternal and c.relname='stock_txn'")
if [ "${TRG:-0}" -ge 1 ] 2>/dev/null; then ok "stock_txn 上有 $TRG 个触发器（只追加保护）"; else bad "stock_txn 缺少只追加触发器"; fi

IDX=$(q "select count(*) from pg_indexes where schemaname='public'")
printf '  索引数量：%s\n' "${IDX:-0}"

# ---------- 4. 只追加保护是否真的生效 ----------
step "5 / 6  验证 stock_txn 的修改/删除保护"

UPD=$(docker exec "$CONTAINER" psql -tAq -U postgres -d "$DBNAME" \
      -c "update stock_txn set remark = remark where ctid = (select ctid from stock_txn limit 1)" 2>&1)
if printf '%s' "$UPD" | grep -qi "exception\|错误\|禁止\|not allow\|只追加"; then
  ok "UPDATE 被触发器拦下（审计链不可篡改）"
else
  if [ -z "$UPD" ]; then
    bad "UPDATE 竟然成功了 —— 触发器没生效，历史流水可被篡改"
  else
    warn "UPDATE 返回：$(printf '%s' "$UPD" | head -1)"
    printf '      请人工确认这是被拦下而非执行成功。\n'
  fi
fi

# ---------- 5. 对账视图 ----------
step "6 / 6  对账视图 v_inventory_recon"

q "select recon_status, count(*) from v_inventory_recon group by 1 order by 1" | while IFS='|' read -r st cnt; do
  [ -z "$st" ] && continue
  printf '  %-16s %s 行\n' "$st" "$cnt"
done

NONOK=$(q "select count(*) from v_inventory_recon where recon_status <> 'OK'")
printf '\n  非 OK 记录数：%s\n' "${NONOK:-?}"
if [ "${NONOK:-1}" = "0" ]; then
  ok "余额与流水完全对账一致"
else
  bad "存在 $NONOK 条对账异常（MISMATCH / ONLY_INVENTORY / ONLY_TXN）"
  printf '      查询明细：select * from v_inventory_recon where recon_status <> '"'"'OK'"'"';\n'
fi

# ---------- 结论 ----------
printf '\n----------------------------------------------\n'
if [ "$FAIL" -eq 0 ]; then
  printf '\033[32m全部通过\033[0m · schema.sql 可以在真实 PG 16 上落地，D3 的模型评审结论有效。\n'
  printf '下一步：把这份产物搬进 alembic 迁移（S1-06）。\n'
  exit 0
else
  printf '\033[31m%d 项未通过\033[0m · 先修 schema.sql，再让 D3 评审它。\n' "$FAIL"
  printf '重跑：KEEP=1 bash %s\n' "$0"
  exit 1
fi
