from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "المدير المحترف"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://professional_manager:professional_manager@localhost:5432/professional_manager"
    api_cors_origins: list[str] = ["http://localhost:3000"]
    import_max_file_bytes: int = 10 * 1024 * 1024
    import_max_rows: int = 20_000
    import_max_sheets: int = 30
    import_max_zip_entries: int = 2_000
    import_max_expanded_bytes: int = 100 * 1024 * 1024
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
