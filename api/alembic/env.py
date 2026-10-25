"""Alembic 迁移环境。

关键点：业务层用的是 async SQLAlchemy（asyncpg），但 alembic 本身
走同步引擎。所以这里把 async 的 database_url 转成同步 psycopg 版本，
再交给 alembic。这样迁移脚本既能在容器里跑，也能在宿主机直接跑。

连接串复用 app.core.config 的 settings，保证「迁移连的库」和
「业务连的库」永远是同一个，不会出现迁错库的经典事故。
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings

# alembic.ini 里的 [alembic] 段
config = context.config

# 读日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 把 async 连接串转成同步的，交给 alembic 用。
# asyncpg://  -> postgresql+psycopg://
_sync_url = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg://", 1
)
config.set_main_option("sqlalchemy.url", _sync_url)


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL，不连库（用于 review 迁移脚本产出的 SQL）。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连库执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
