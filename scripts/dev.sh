#!/usr/bin/env bash
# ---------------------------------------------------------------
# 开发入口。所有常用命令集中在这里，Makefile 只做转发。
# 命令逻辑只有一份 —— 两份必然漂移。
#
#   bash scripts/dev.sh help
#
# Windows 上没装 make 也能直接用；装了 make 的话 `make up` 等价。
# ---------------------------------------------------------------

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 读取 .env（不存在的变量由默认值兜底）
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

DB_USER="${POSTGRES_USER:-canku}"
DB_NAME="${POSTGRES_DB:-canku}"
API_PORT="${API_PORT:-8000}"

c_ok()   { printf '\033[32m%s\033[0m\n' "$1"; }
c_info() { printf '\033[36m%s\033[0m\n' "$1"; }
c_warn() { printf '\033[33m%s\033[0m\n' "$1"; }
die()    { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

need_docker() {
  docker info >/dev/null 2>&1 || die "Docker 守护进程没起来，先启动 Docker Desktop。"
}

ensure_env() {
  if [ ! -f .env ]; then
    cp .env.example .env
    c_warn "未找到 .env，已从 .env.example 生成。需要改端口或密码请编辑 .env。"
  fi
}

wait_api() {
  local i
  for i in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:${API_PORT}/api/v1/health" >/dev/null 2>&1; then
      c_ok "API 就绪：http://127.0.0.1:${API_PORT}/api/v1/health"
      return 0
    fi
    sleep 1
  done
  c_warn "API 40 秒内未就绪，查看日志：bash scripts/dev.sh logs api"
  return 1
}

cmd_db_init() {
  need_docker
  # DDL 走 alembic 迁移（版本化），不再直接 psql 执行 schema.sql。
  # schema.sql 保留作为「基线快照」供人工对照，但唯一真源是 alembic/versions/。
  c_info "迁移：alembic upgrade head"
  docker compose exec -T api alembic upgrade head
  c_ok "结构完成"
  # 种子数据仍走 seed.sql，幂等可重复执行
  c_info "播种：db/seed.sql（幂等，可重复执行）"
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -q -U "$DB_USER" -d "$DB_NAME" < db/seed.sql
  c_ok "播种完成"
  cmd_db_check
}

cmd_db_check() {
  c_info "对账检查：v_inventory_recon"
  docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" \
    -c "select recon_status, count(*) as rows from v_inventory_recon group by 1 order by 1;"
  local n
  n=$(docker compose exec -T db psql -tAq -U "$DB_USER" -d "$DB_NAME" \
        -c "select count(*) from v_inventory_recon where recon_status <> 'OK';" | tr -d '\r')
  if [ "${n:-1}" = "0" ]; then
    c_ok "账实一致（非 OK 记录 0 条）"
  else
    c_warn "存在 $n 条对账异常，明细："
    docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" \
      -c "select * from v_inventory_recon where recon_status <> 'OK' limit 20;"
    return 1
  fi
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  up)
    need_docker
    ensure_env
    c_info "启动 db + api ..."
    docker compose up -d "$@"
    wait_api || true
    c_ok "完成。文档：http://127.0.0.1:${API_PORT}/docs"
    ;;

  down)
    need_docker
    docker compose down "$@"
    c_ok "已停止（数据卷保留，加 -v 可连同数据一起删）"
    ;;

  restart)
    need_docker
    docker compose restart "$@"
    c_ok "已重启"
    ;;

  ps)
    need_docker
    docker compose ps
    ;;

  logs)
    need_docker
    docker compose logs -f --tail=100 "$@"
    ;;

  psql)
    need_docker
    docker compose exec db psql -U "$DB_USER" -d "$DB_NAME"
    ;;

  db-init)
    cmd_db_init
    ;;

  db-reset)
    need_docker
    c_warn "危险：将清空库 $DB_NAME 的全部数据后重建。"
    read -r -p "输入 yes 确认： " ans
    [ "$ans" = "yes" ] || die "已取消"
    docker compose exec -T db psql -v ON_ERROR_STOP=1 -q -U "$DB_USER" -d "$DB_NAME" \
      -c "drop schema public cascade; create schema public;"
    c_ok "已清空"
    cmd_db_init
    ;;

  db-check)
    need_docker
    cmd_db_check
    ;;

  db-migrate)
    need_docker
    c_info "迁移：alembic upgrade head"
    docker compose exec -T api alembic upgrade head
    c_ok "迁移完成"
    ;;

  test)
    need_docker
    docker compose exec -T api python -m pytest -q "$@"
    ;;

  lint)
    need_docker
    docker compose exec -T api ruff check app tests
    ;;

  fmt)
    need_docker
    docker compose exec -T api ruff format app tests
    ;;

  sh)
    need_docker
    docker compose exec api bash
    ;;

  help|*)
    cat <<'EOF'
仓储智能管理 Agent 系统 · 开发命令

  up [服务...]      启动 db + api（自动生成 .env），并等待 API 就绪
  down [-v]         停止（-v 连同数据卷一起删除）
  restart [服务]    重启
  ps                查看容器状态
  logs [服务]       跟踪日志

  psql              进入数据库交互终端
  db-init           迁移（alembic upgrade head）+ 播种（seed.sql，幂等）
  db-migrate        只跑迁移，不播种
  db-reset          清空并重建（需输入 yes）
  db-check          查对账视图，非空即账实不一致

  test              跑 pytest
  lint / fmt        ruff 检查 / 格式化
  sh                进入 api 容器

  help              显示本帮助

示例：
  bash scripts/dev.sh up
  bash scripts/dev.sh logs api
  bash scripts/dev.sh psql
EOF
    ;;
esac

