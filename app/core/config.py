from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Travel Planner API"
    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./travel_planner.db"
    api_username: str = "admin"
    api_password: str = "change-me"
    art_institute_base_url: str = "https://api.artic.edu/api/v1"
    art_institute_timeout_seconds: float = Field(default=10.0, gt=0)
    art_institute_cache_ttl_seconds: int = Field(default=300, ge=0)
    art_institute_user_agent: str = "travel-planner-api (contact@example.com)"
    auto_create_tables: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
