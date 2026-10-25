from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """运行配置。

    优先级：环境变量 > .env > 这里的默认值。
    容器里没有 .env，全部走环境变量（见 docker-compose.yml）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    log_level: str = "DEBUG"
    api_prefix: str = "/api/v1"

    # 默认指向宿主机本地库，方便脱离容器直接跑 uvicorn
    database_url: str = "postgresql+asyncpg://canku:canku_dev@localhost:5432/canku"

    @property
    def is_dev(self) -> bool:
        return self.app_env in ("dev", "local", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
