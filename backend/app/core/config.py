from pydantic_settings import BaseSettings, NoDecode
from pydantic import ConfigDict, field_validator
from pathlib import Path
from typing import Annotated


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

    # Brute-force (/login : compteur par IP + verrouillage du compte en base)
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # Limitation des autres routes d'authentification non protégées par le
    # mécanisme ci-dessus. Format : (nombre d'appels, fenêtre en secondes).
    #   register        — freine la création massive de comptes
    #   forgot-password — freine l'énumération d'e-mails et le mail-bombing
    #   token           — freine le brute-force des jetons de vérification
    #                     et de réinitialisation (reset-password, verify-email)
    RATE_LIMIT_REGISTER: tuple[int, int] = (10, 3600)
    RATE_LIMIT_FORGOT_PASSWORD: tuple[int, int] = (3, 600)
    RATE_LIMIT_TOKEN: tuple[int, int] = (10, 600)

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

    # Société (en-tête des contrats de travail)
    COMPANY_NAME: str = "PIQBIT Lab"
    COMPANY_MANAGER: str = "Mohamed Derbali"       # le gérant
    COMPANY_TAX_ID: str = ""                        # matricule fiscal (optionnel)
    COMPANY_ADDRESS: str = "Tunis, Tunisie"
    COMPANY_CITY: str = "Tunis"

    # Anthropic / Claude (optional — features degrade gracefully if unset)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/api/v1/auth/google/callback"

    # Embeddings / matching sémantique
    # Backend : "auto" (sentence-transformers si dispo, sinon hash), "model", "hash".
    EMBEDDINGS_BACKEND: str = "auto"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384

    # Google Calendar (optional — interview sync degrades gracefully if unset)
    # Path to the service-account JSON key downloaded from Google Cloud Console.
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str = ""
    # Calendar to write into: "primary" (with impersonation) or the calendar id
    # (e.g. xxxx@group.calendar.google.com) shared with the service account.
    GOOGLE_CALENDAR_ID: str = ""
    # Optional Workspace user to impersonate (domain-wide delegation).
    GOOGLE_CALENDAR_IMPERSONATE: str = ""
    GOOGLE_CALENDAR_TIMEZONE: str = "Africa/Tunis"

    # ─── CORS ──────────────────────────────────────────────────────────────
    # Origines autorisées à appeler l'API depuis un navigateur. Renseigner en
    # production le(s) domaine(s) du frontend, séparés par des virgules :
    #   ALLOWED_ORIGINS=https://app.piqbit.tn,https://admin.piqbit.tn
    # `NoDecode` désactive le décodage JSON automatique que pydantic-settings
    # applique aux types complexes AVANT les validateurs : sans lui, une valeur
    # « a,b » lève une JSONDecodeError et le validateur ci-dessous n'est jamais
    # atteint.
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:4200",
        "http://localhost:3000",
    ]

    # Autorise TOUT port de localhost/127.0.0.1 (previews Angular, second
    # `ng serve`…). Pratique en développement, à passer à False en production
    # où seule la liste ALLOWED_ORIGINS doit faire foi.
    ALLOW_LOCALHOST_ORIGINS: bool = True

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        """
        Accepte trois écritures, les variables d'environnement (Docker,
        systemd, CI) ne sachant transporter que des chaînes :
          - liste séparée par des virgules : a,b        <- forme recommandée
          - tableau JSON                   : ["a","b"]  <- rétrocompatibilité
          - chaîne vide                    : aucune origine autorisée

        Le parsing JSON est fait ici explicitement : `NoDecode` sur le champ
        désactive celui de pydantic-settings, sinon la forme à virgules
        échouerait avant d'atteindre ce validateur.
        """
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            import json
            return json.loads(stripped)
        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

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
