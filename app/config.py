from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./app.db"
    storage_dir: str = "storage/pdfs"
    max_upload_size_mb: int = 10
    max_docs_per_person: int = 50

    # Admin authentication
    admin_username: str = "admin"
    admin_password: str = "changeme"
    admin_secret_key: str = "change-this-in-production-please"

    # Rate limiting
    rate_limit_general: str = "60/minute"
    rate_limit_upload: str = "10/minute"
    rate_limit_put: str = "5/minute"

    # SMTP email (for password recovery)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Twilio SMS (optional, for password recovery)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # Backup
    backup_auto_enabled: bool = False
    backup_auto_path: str = ""
    backup_auto_interval_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
