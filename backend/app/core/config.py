from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_NAME: str = "PIQBIT API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Bcrypt
    BCRYPT_ROUNDS: int = 12

    # Brute-force
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # 2FA
    TOTP_ISSUER: str = "PIQBIT"
    TOTP_EXPIRE_SECONDS: int = 300  # 5 min
    TOTP_BACKUP_CODES_COUNT: int = 10

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@piqbit.tn"
    EMAILS_FROM_NAME: str = "PIQBIT"

    # Anthropic / Claude (optional — features degrade gracefully if unset)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/api/v1/auth/google/callback"

    # Google Calendar (optional — interview sync degrades gracefully if unset)
    # Path to the service-account JSON key downloaded from Google Cloud Console.
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str = ""
    # Calendar to write into: "primary" (with impersonation) or the calendar id
    # (e.g. xxxx@group.calendar.google.com) shared with the service account.
    GOOGLE_CALENDAR_ID: str = ""
    # Optional Workspace user to impersonate (domain-wide delegation).
    GOOGLE_CALENDAR_IMPERSONATE: str = ""
    GOOGLE_CALENDAR_TIMEZONE: str = "Africa/Tunis"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:4200", "http://localhost:3000"]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value

    model_config = ConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        case_sensitive=True
    )


settings = Settings()
