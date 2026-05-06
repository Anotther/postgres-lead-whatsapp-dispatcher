from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: str = "local"
    app_name: str = "postgres-lead-whatsapp-dispatcher"
    dry_run: bool = True
    timezone: str = "America/Sao_Paulo"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "leads_db"
    postgres_user: str = "postgres"
    postgres_password: str = "change_me"
    postgres_sslmode: str = "prefer"

    # Query
    lead_query_path: str = "config/lead_query.example.sql"
    lead_limit: int = 100

    # Evolution API / Evolution Go
    evolution_base_url: str = "http://localhost:8080"
    evolution_api_key: str = "change_me"
    evolution_send_text_path: str = "/message/sendText/{instance}"
    evolution_instance_status_path: str = "/instance/status"
    evolution_connected_states: str = "open,connected,online"

    # Config files
    instances_config_path: str = "config/instances.example.yml"
    messages_config_path: str = "config/messages.example.yml"

    # Dispatch
    default_country_code: str = "55"
    max_retries: int = 3
    request_timeout_seconds: int = 30
    stop_on_critical_error: bool = False
    dispatch_limit_override: str = "ask"
    limit_override_prompt_timeout_seconds: int = 120
    dispatch_state_path: str = "data/dispatch_state.json"

    # Logs
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_retention_days: int = 7
    log_mask_phone: bool = True

    # Reports
    report_dir: str = "reports"
    report_formats: str = "md"
    report_keep_history: bool = False
    report_send_whatsapp: bool = False
    report_recipient_number: str | None = None
    report_recipient_instance: str | None = None


settings = Settings()
