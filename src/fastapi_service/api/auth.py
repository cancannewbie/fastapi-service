"""User registration and OAuth2 password bearer authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..db.models import UserModel
from ..db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
password_hasher = PasswordHash.recommended()
_dummy_hash = password_hasher.hash("not-a-real-user-password")
Session = Annotated[AsyncSession, Depends(get_session)]


def configure_auth_openapi(app: FastAPI, api_prefix: str) -> None:
    """Use this application's API prefix in its OAuth2 discovery metadata."""
    original_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        schema = original_openapi()
        scheme = schema["components"]["securitySchemes"][oauth2_scheme.scheme_name]
        scheme["flows"]["password"]["tokenUrl"] = f"{api_prefix}/auth/token".lstrip("/")
        return schema

    app.openapi = openapi  # type: ignore[method-assign]


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100, pattern=r"^\S+$")
    password: str = Field(min_length=8, max_length=1024)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, session: Session) -> UserPublic:
    user = UserModel(
        username=payload.username,
        password_hash=await run_in_threadpool(password_hasher.hash, payload.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Username already registered") from exc
    return UserPublic.model_validate(user)


@router.post("/token")
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session,
) -> Token:
    user = await session.scalar(select(UserModel).where(UserModel.username == form.username))
    password_hash = user.password_hash if user else _dummy_hash
    valid = await run_in_threadpool(password_hasher.verify, form.password, password_hash)
    if user is None or not valid:
        raise _unauthorized()
    settings: Settings = request.app.state.settings
    now = datetime.now(UTC)
    encoded = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return Token(access_token=encoded)


async def get_current_user(
    request: Request, token: Annotated[str, Depends(oauth2_scheme)], session: Session
) -> UserModel:
    """Resolve a valid, unexpired bearer token to an existing user."""
    settings: Settings = request.app.state.settings
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
        subject = payload["sub"]
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
            raise ValueError("Invalid subject")
        user_id = int(subject)
        if not 0 < user_id <= 2_147_483_647:
            raise ValueError("Invalid subject")
    except (InvalidTokenError, ValueError, OverflowError):
        raise _unauthorized() from None
    user = await session.get(UserModel, user_id)
    if user is None:
        raise _unauthorized()
    return user


@router.get("/me")
async def read_current_user(user: Annotated[UserModel, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(user)
