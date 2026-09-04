from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    instagram_provider: str = "demo"
    instagram_login_username: str | None = None
    instagram_password: SecretStr | None = None
    instagram_session_file: str | None = None
    cache_ttl_seconds: int = 900
    max_posts: int = 24
    max_scan_posts: int = 200

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
