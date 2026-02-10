from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_request_id, require_roles
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_refresh_token,
    validate_password_policy,
    verify_password,
)
from app.models import Invite, RefreshToken, User
from app.schemas.auth import (
    InviteCreateRequest,
    InviteOut,
    LoginRequest,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import MessageResponse
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(tags=["admin-users"])


@router.post("/register", response_model=UserOut)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    invite_result = await db.execute(
        select(Invite).where(
            Invite.code == payload.invite_code,
            Invite.is_active.is_(True),
            Invite.used_at.is_(None),
        )
    )
    invite = invite_result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invite code")

    if invite.expires_at and invite.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite code expired")

    if invite.email and invite.email.lower() != payload.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite code restricted to another email")

    exists = await db.execute(select(User).where(User.email == payload.email.lower()))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    try:
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = User(
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        name=payload.name,
        role=invite.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    invite.used_by = user.id
    invite.used_at = datetime.now(UTC)

    await record_audit_event(
        db,
        actor_id=user.id,
        actor_type="USER",
        action="register",
        entity_type="user",
        entity_id=user.id,
        before_state=None,
        after_state={"email": user.email, "role": user.role},
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email.lower(), User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token, access_exp = create_access_token(str(user.id), user.email, user.role)
    raw_refresh = create_refresh_token()
    refresh_hash = hash_refresh_token(raw_refresh)
    refresh_exp = datetime.now(UTC) + timedelta(hours=get_settings().refresh_token_expire_hours)

    active_tokens_result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        .order_by(RefreshToken.created_at.asc())
    )
    active_tokens = list(active_tokens_result.scalars().all())
    max_sessions = get_settings().max_concurrent_sessions
    if len(active_tokens) >= max_sessions:
        for token in active_tokens[: len(active_tokens) - max_sessions + 1]:
            token.revoked_at = datetime.now(UTC)

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=refresh_exp,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(refresh_token)

    user.last_login = datetime.now(UTC)

    await record_audit_event(
        db,
        actor_id=user.id,
        actor_type="USER",
        action="login",
        entity_type="auth",
        entity_id=user.id,
        before_state=None,
        after_state={"session_created": True},
        request_id=get_request_id(request),
    )

    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=get_settings().app_env != "development",
        samesite="lax",
        max_age=get_settings().refresh_token_expire_hours * 3600,
    )

    return TokenResponse(access_token=access_token, access_token_expires_at=access_exp)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RefreshResponse:
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    refresh_hash = hash_refresh_token(raw_refresh)
    token_result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == refresh_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    token = token_result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_result = await db.execute(select(User).where(User.id == token.user_id, User.is_active.is_(True)))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    token.revoked_at = datetime.now(UTC)

    new_raw_refresh = create_refresh_token()
    new_hash = hash_refresh_token(new_raw_refresh)
    new_exp = datetime.now(UTC) + timedelta(hours=get_settings().refresh_token_expire_hours)
    new_token = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=new_exp,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(new_token)

    access_token, access_exp = create_access_token(str(user.id), user.email, user.role)

    await record_audit_event(
        db,
        actor_id=user.id,
        actor_type="USER",
        action="refresh",
        entity_type="auth",
        entity_id=user.id,
        before_state=None,
        after_state={"session_rotated": True},
        request_id=get_request_id(request),
    )
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh,
        httponly=True,
        secure=get_settings().app_env != "development",
        samesite="lax",
        max_age=get_settings().refresh_token_expire_hours * 3600,
    )

    return RefreshResponse(access_token=access_token, access_token_expires_at=access_exp)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        refresh_hash = hash_refresh_token(raw_refresh)
        await db.execute(
            delete(RefreshToken).where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.token_hash == refresh_hash,
            )
        )

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="logout",
        entity_type="auth",
        entity_id=current_user.id,
        before_state=None,
        after_state={"logout": True},
        request_id=get_request_id(request),
    )
    await db.commit()

    response.delete_cookie("refresh_token")
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.model_validate(current_user)


@admin_router.get("/users", response_model=list[UserOut])
async def list_users(
    _: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserOut]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@admin_router.post("/invites", response_model=InviteOut)
async def create_invite(
    payload: InviteCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InviteOut:
    code = f"INV-{secrets.token_hex(3).upper()}"
    invite = Invite(
        code=code,
        email=payload.email.lower() if payload.email else None,
        role=payload.role,
        expires_at=payload.expires_at,
        created_by=current_user.id,
        is_active=True,
    )
    db.add(invite)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="create",
        entity_type="invite",
        entity_id=invite.id,
        before_state=None,
        after_state={"code": code, "role": payload.role, "email": payload.email},
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(invite)
    return InviteOut.model_validate(invite)


@admin_router.get("/invites", response_model=list[InviteOut])
async def list_invites(
    _: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[InviteOut]:
    result = await db.execute(select(Invite).order_by(Invite.created_at.desc()))
    return [InviteOut.model_validate(i) for i in result.scalars().all()]


@admin_router.delete("/invites/{invite_id}", response_model=MessageResponse)
async def revoke_invite(
    invite_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    invite_result = await db.execute(select(Invite).where(Invite.id == invite_id))
    invite = invite_result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    invite.is_active = False

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="revoke",
        entity_type="invite",
        entity_id=invite.id,
        before_state={"is_active": True},
        after_state={"is_active": False},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Invite revoked")
