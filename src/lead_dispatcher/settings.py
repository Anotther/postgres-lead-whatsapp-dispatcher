from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    app_env: str = "local"
    dry_run: bool = True

    # PostgreSQL
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str

    # Evolution API
    evolution_base_url: str
    evolution_api_key: str

    # Dispatch
    lead_limit: int = 100
    default_country_code: str = "55"

    # Logs
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()