from typing import Annotated

from fastapi import APIRouter, Depends, Request, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.agent import (
    BackupCodeRequest,
    EmailVerifyRequest,
    RefreshTokenRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TokenResponse,
)
from app.schemas.user import (
    PasswordChange,
    PasswordReset,
    PasswordResetRequest,
    UserCreate,
    UserResponse,
)
from app.services.report_service import auth_service

router = APIRouter()

class GoogleLoginRequest(BaseModel):
    id_token: str

@router.post("/google", response_model=TokenResponse)
async def login_with_google(
    request: Request,
    body: dict,  # {id_token: string}
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login with Google OAuth using ID token"""
    if "id_token" not in body:
        raise HTTPException(status_code=400, detail="Missing id_token")
    
    tokens = await auth_service.google_login(db, request, body["id_token"])
    await db.commit()
    return tokens


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await auth_service.register(
        db,
        email=body.email,
        username=body.username,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: dict,  # accepts email + password + optional totp_code
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.schemas.agent import LoginRequest
    parsed = LoginRequest(**body)
    tokens = await auth_service.login(
        db, request, parsed.email, parsed.password, parsed.totp_code
    )
    await db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await auth_service.logout(db, current_user)
    await db.commit()


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tokens = await auth_service.refresh(db, body.refresh_token)
    await db.commit()
    return tokens


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    body: EmailVerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await auth_service.verify_email(db, body.token)
    await db.commit()
    return {"message": "Email verified successfully."}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Token returned but NOT sent here — wire your email service to deliver it
    await auth_service.request_password_reset(db, body.email)
    await db.commit()
    return {"message": "If this email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    body: PasswordReset,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await auth_service.reset_password(db, body.token, body.new_password)
    await db.commit()
    return {"message": "Password reset successful."}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    body: PasswordChange,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await auth_service.change_password(db, current_user, body.current_password, body.new_password)
    await db.commit()
    return {"message": "Password changed."}


# ---------- 2FA ----------

@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    data = await auth_service.setup_totp(db, current_user)
    await db.commit()
    return TOTPSetupResponse(**data)


@router.post("/2fa/enable", status_code=status.HTTP_200_OK)
async def enable_2fa(
    body: TOTPVerifyRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await auth_service.enable_totp(db, current_user, body.code)
    await db.commit()
    return {"message": "2FA enabled."}


@router.post("/2fa/disable", status_code=status.HTTP_200_OK)
async def disable_2fa(
    body: TOTPVerifyRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await auth_service.disable_totp(db, current_user, body.code)
    await db.commit()
    return {"message": "2FA disabled."}


@router.post("/2fa/backup", response_model=TokenResponse)
async def use_backup_code(
    body: BackupCodeRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tokens = await auth_service.use_backup_code(db, current_user, body.code)
    await db.commit()
    return tokens
