import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole:
    ADMIN = "ADMIN"
    RH_MANAGER = "RH_MANAGER"
    RH_STAFF = "RH_STAFF"
    READ_ONLY = "READ_ONLY"

    ALL = [ADMIN, RH_MANAGER, RH_STAFF, READ_ONLY]


class User(Base):
    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Credentials
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users

    # OAuth
    google_id = Column(String(255), nullable=True, unique=True, index=True)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'linkedin', etc.

    # Status flags
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Profile
    full_name = Column(String(200), nullable=True)
    phone_number = Column(String(30), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    ministry = Column(String(200), nullable=True, index=True)
    department = Column(String(200), nullable=True)
    job_title = Column(String(200), nullable=True)
    employee_id = Column(String(100), nullable=True, unique=True)

    # Role & permissions
    role = Column(String(50), nullable=False, default=UserRole.READ_ONLY, index=True)
    permissions = Column(JSON, nullable=True, default=dict)

    # 2FA
    totp_enabled = Column(Boolean, default=False, nullable=False)
    totp_secret = Column(String(255), nullable=True)
    totp_backup_codes = Column(JSON, nullable=True, default=list)  # stored as hashed codes

    # Session management
    refresh_token = Column(Text, nullable=True)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Brute-force protection
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Activity tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)

    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft delete sentinel

    # Preferences
    language = Column(String(5), default="fr", nullable=False)
    timezone = Column(String(100), default="Africa/Tunis", nullable=False)
    notification_preferences = Column(JSON, nullable=True, default=dict)

    # Relationships
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        foreign_keys="AuditLog.user_id",
        lazy="dynamic",
    )
    candidate = relationship("Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_role_ministry", "role", "ministry"),
        Index("ix_users_deleted_at", "deleted_at"),
    )

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until.replace(tzinfo=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
