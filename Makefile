# 薄封装：所有逻辑在 scripts/dev.sh，这里只做命令转发。
# 没装 make 也能直接用 bash scripts/dev.sh <命令>。
# 注意：Makefile 的缩进必须是 TAB，不是空格。

.DEFAULT_GOAL := help
SHELL := bash

.PHONY: help up down restart ps logs psql db-init db-reset db-check test lint fmt sh

help:       ## 显示全部命令
	@bash scripts/dev.sh help
up:         ## 启动 db + api 并等待就绪
	@bash scripts/dev.sh up
down:       ## 停止（make down ARGS=-v 连数据卷一起删）
	@bash scripts/dev.sh down $(ARGS)
restart:    ## 重启
	@bash scripts/dev.sh restart $(ARGS)
ps:         ## 容器状态
	@bash scripts/dev.sh ps
logs:       ## 跟踪日志（make logs ARGS=api）
	@bash scripts/dev.sh logs $(ARGS)
psql:       ## 进数据库终端
	@bash scripts/dev.sh psql
db-init:    ## 建结构 + 播种
	@bash scripts/dev.sh db-init
db-reset:   ## 清空重建（需确认）
	@bash scripts/dev.sh db-reset
db-check:   ## 对账检查
	@bash scripts/dev.sh db-check
test:       ## pytest
	@bash scripts/dev.sh test
lint:       ## ruff check
	@bash scripts/dev.sh lint
fmt:        ## ruff format
	@bash scripts/dev.sh fmt
sh:         ## 进 api 容器
	@bash scripts/dev.sh sh
