from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ---------- Auth schemas ----------

class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str | None = None


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: list[str]  # shown once, plain text


class TOTPVerifyRequest(BaseModel):
    code: str


class BackupCodeRequest(BaseModel):
    code: str


class EmailVerifyRequest(BaseModel):
    token: str


# ---------- Audit log ----------

class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    resource: str | None
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAuditLogs(BaseModel):
    total: int
    page: int
    size: int
    items: list[AuditLogResponse]
