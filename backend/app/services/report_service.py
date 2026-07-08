"""Auth service — register, login, logout, token refresh, 2FA, password reset."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import (
    get_login_attempts,
    increment_login_attempts,
    reset_login_attempts,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_backup_codes,
    generate_secure_token,
    generate_totp_secret,
    get_totp_uri,
    hash_backup_code,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_backup_code,
    verify_password,
    verify_token_hash,
    verify_totp,
)
from app.models.user import AuditLog, User, UserRole
from app.schemas.agent import TokenResponse


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:

    # ---- Registration ----

    async def register(
        self,
        db: AsyncSession,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
        role: str = UserRole.READ_ONLY,
        created_by: UUID | None = None,
    ) -> User:
        await self._assert_email_unique(db, email)
        await self._assert_username_unique(db, username)

        if not validate_password_strength(password):
            raise HTTPException(status_code=400, detail="Password too weak.")

        verification_token = generate_secure_token()
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
            is_verified=False,
            email_verification_token=verification_token,
            email_verification_expires_at=_utcnow() + timedelta(hours=24),
            created_by=created_by,
        )
        db.add(user)
        await db.flush()
        await self._log(db, user.id, "REGISTER", "user", str(user.id))
        return user

    # ---- Login ----

    async def login(
        self,
        db: AsyncSession,
        request: Request,
        email: str,
        password: str,
        totp_code: str | None = None,
    ) -> TokenResponse:
        ip = self._get_ip(request)
        attempts = await get_login_attempts(ip)

        if attempts >= settings.MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {settings.LOCKOUT_MINUTES} minutes.",
            )

        user = await self._get_user_by_email(db, email)

        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            await increment_login_attempts(ip)
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                    user.locked_until = _utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES)
                await self._log(db, user.id, "LOGIN_FAIL", "user", str(user.id), {"ip": ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled.")

        if user.is_locked:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked. Try later.")

        # 2FA check
        if user.totp_enabled:
            if not totp_code:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="2FA code required.")
            if not verify_totp(user.totp_secret, totp_code):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code.")

        # Success — reset brute-force counters
        await reset_login_attempts(ip)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = _utcnow()
        user.last_login_ip = ip

        tokens = self._issue_tokens(user)
        user.refresh_token = hash_token(tokens.refresh_token)
        user.refresh_token_expires_at = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self._log(db, user.id, "LOGIN_SUCCESS", "user", str(user.id), {"ip": ip})
        return tokens

    # ---- Google OAuth Login ----

    async def google_login(
        self,
        db: AsyncSession,
        request: Request,
        id_token: str,
    ) -> TokenResponse:
        """Login or register user via Google OAuth"""
        try:
            # Verify Google token
            user_info = await self._verify_google_token(id_token)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Google token: {str(e)}")

        google_id = user_info.get("sub")
        email = user_info.get("email")
        full_name = user_info.get("name")
        
        if not google_id or not email:
            raise HTTPException(status_code=400, detail="Missing required Google data.")

        # Try to find user by google_id first
        result = await db.execute(
            select(User).where(User.google_id == google_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        # If not found by google_id, try by email
        if not user:
            result = await db.execute(
                select(User).where(User.email == email, User.deleted_at.is_(None))
            )
            user = result.scalar_one_or_none()

        # Create new user if doesn't exist
        if not user:
            username = email.split("@")[0]  # Use email prefix as username
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                google_id=google_id,
                oauth_provider="google",
                hashed_password=None,  # OAuth users don't have passwords
                is_active=True,
                is_verified=True,  # Assume verified via Google
                role=UserRole.READ_ONLY,
            )
            db.add(user)
            await db.flush()
            await self._log(db, user.id, "GOOGLE_REGISTER", "user", str(user.id))
        else:
            # Update google_id if not set
            if not user.google_id:
                user.google_id = google_id
                user.oauth_provider = "google"
                await self._log(db, user.id, "GOOGLE_LINKED", "user", str(user.id))

        # Update last login
        ip = self._get_ip(request)
        user.last_login_at = _utcnow()
        user.last_login_ip = ip

        # Issue tokens
        tokens = self._issue_tokens(user)
        user.refresh_token = hash_token(tokens.refresh_token)
        user.refresh_token_expires_at = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self._log(db, user.id, "LOGIN_SUCCESS_GOOGLE", "user", str(user.id), {"ip": ip})
        return tokens

    async def _verify_google_token(self, id_token: str) -> dict:
        """Verify Google ID token and return user info"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import id_token as google_id_token
            
            # Verify token using Google's library
            request = Request()
            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                request,
                audience=settings.GOOGLE_CLIENT_ID
            )
            
            # Verify that the token issuer is Google
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            # Additional validation: check audience matches our Client ID
            if idinfo.get('aud') != settings.GOOGLE_CLIENT_ID:
                raise ValueError(f'Audience mismatch: expected {settings.GOOGLE_CLIENT_ID}, got {idinfo.get("aud")}')
            
            return idinfo
        except Exception as e:
            import logging
            logging.error(f"Google token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}"
            )

    # ---- Logout ----

    async def logout(self, db: AsyncSession, user: User) -> None:
        user.refresh_token = None
        user.refresh_token_expires_at = None
        await self._log(db, user.id, "LOGOUT", "user", str(user.id))

    # ---- Refresh ----

    async def refresh(self, db: AsyncSession, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")

        user = await self._get_user_by_id(db, UUID(payload["sub"]))
        if not user or not user.refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")

        if not verify_token_hash(refresh_token, user.refresh_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token mismatch.")

        # SQLite renvoie des datetimes naïves (PostgreSQL des aware) : normaliser
        # avant comparaison pour éviter « can't compare offset-naive and
        # offset-aware datetimes ».
        expires_at = user.refresh_token_expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and _utcnow() > expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")

        # Rotate
        tokens = self._issue_tokens(user)
        user.refresh_token = hash_token(tokens.refresh_token)
        user.refresh_token_expires_at = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self._log(db, user.id, "TOKEN_REFRESH", "user", str(user.id))
        return tokens

    # ---- Email verification ----

    async def verify_email(self, db: AsyncSession, token: str) -> None:
        result = await db.execute(select(User).where(User.email_verification_token == token))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token.")
        if user.email_verification_expires_at and _utcnow() > user.email_verification_expires_at:
            raise HTTPException(status_code=400, detail="Verification token expired.")
        user.is_verified = True
        user.email_verification_token = None
        user.email_verification_expires_at = None
        await self._log(db, user.id, "EMAIL_VERIFIED", "user", str(user.id))

    # ---- Password reset ----

    async def request_password_reset(self, db: AsyncSession, email: str) -> str | None:
        user = await self._get_user_by_email(db, email)
        if not user:
            return None  # silent — don't leak existence
        token = generate_secure_token()
        user.password_reset_token = token
        user.password_reset_expires_at = _utcnow() + timedelta(hours=1)
        await self._log(db, user.id, "PASSWORD_RESET_REQUEST", "user", str(user.id))
        return token  # caller sends this via email

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> None:
        if not validate_password_strength(new_password):
            raise HTTPException(status_code=400, detail="Password too weak.")
        result = await db.execute(select(User).where(User.password_reset_token == token))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid token.")
        if user.password_reset_expires_at and _utcnow() > user.password_reset_expires_at:
            raise HTTPException(status_code=400, detail="Token expired.")
        user.hashed_password = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        user.refresh_token = None  # invalidate sessions
        await self._log(db, user.id, "PASSWORD_RESET", "user", str(user.id))

    async def change_password(self, db: AsyncSession, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password incorrect.")
        if not validate_password_strength(new):
            raise HTTPException(status_code=400, detail="Password too weak.")
        user.hashed_password = hash_password(new)
        user.refresh_token = None
        await self._log(db, user.id, "PASSWORD_CHANGE", "user", str(user.id))

    # ---- 2FA ----

    async def setup_totp(self, db: AsyncSession, user: User) -> dict:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, user.email)
        plain_codes = generate_backup_codes(settings.TOTP_BACKUP_CODES_COUNT)
        hashed_codes = [hash_backup_code(c) for c in plain_codes]

        user.totp_secret = secret
        user.totp_backup_codes = hashed_codes
        await self._log(db, user.id, "TOTP_SETUP_INIT", "user", str(user.id))

        return {"secret": secret, "provisioning_uri": uri, "backup_codes": plain_codes}

    async def enable_totp(self, db: AsyncSession, user: User, code: str) -> None:
        if not user.totp_secret:
            raise HTTPException(status_code=400, detail="TOTP not initialized. Call setup first.")
        if not verify_totp(user.totp_secret, code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code.")
        user.totp_enabled = True
        await self._log(db, user.id, "TOTP_ENABLED", "user", str(user.id))

    async def disable_totp(self, db: AsyncSession, user: User, code: str) -> None:
        if not user.totp_enabled:
            raise HTTPException(status_code=400, detail="2FA is not enabled.")
        if not verify_totp(user.totp_secret, code):
            raise HTTPException(status_code=400, detail="Invalid TOTP code.")
        user.totp_enabled = False
        user.totp_secret = None
        user.totp_backup_codes = []
        await self._log(db, user.id, "TOTP_DISABLED", "user", str(user.id))

    async def use_backup_code(self, db: AsyncSession, user: User, plain_code: str) -> TokenResponse:
        stored: list[str] = user.totp_backup_codes or []
        for i, hashed in enumerate(stored):
            if verify_backup_code(plain_code, hashed):
                stored.pop(i)
                user.totp_backup_codes = stored
                await self._log(db, user.id, "BACKUP_CODE_USED", "user", str(user.id))
                return self._issue_tokens(user)
        raise HTTPException(status_code=400, detail="Invalid backup code.")

    # ---- Helpers ----

    def _issue_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(
            str(user.id), user.role, user.permissions or {}
        )
        refresh = create_refresh_token(str(user.id))
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def _get_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def _get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        result = await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def _assert_email_unique(self, db: AsyncSession, email: str) -> None:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered.")

    async def _assert_username_unique(self, db: AsyncSession, username: str) -> None:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken.")

    async def _log(
        self,
        db: AsyncSession,
        user_id: UUID | None,
        action: str,
        resource: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
        )
        db.add(log)


auth_service = AuthService()
