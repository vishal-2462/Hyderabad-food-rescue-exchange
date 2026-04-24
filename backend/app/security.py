from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from passlib.context import CryptContext

from app import models, schemas
from app.auth_store import get_user_store

TOKEN_COOKIE_NAME = "auth_token"
JWT_ALGORITHM = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "ps12-dev-secret")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(user: models.User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user.id,
        "role": user.role.value,
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=TOKEN_COOKIE_NAME, path="/")


def to_auth_user(user: models.User) -> schemas.AuthUser:
    return schemas.AuthUser(id=user.id, email=user.email, role=user.role, profile_id=user.profile_id)


def authenticate_user(email: str, password: str, role: models.UserRole | None = None) -> models.User | None:
    user = get_user_store().get_by_email(email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    if role is not None and user.role != role:
        return None
    return user


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _decode_access_token(token: str) -> tuple[str, models.UserRole]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = str(payload["sub"])
        role = models.UserRole(payload["role"])
        return user_id, role
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc


def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    auth_token: Annotated[str | None, Cookie(alias=TOKEN_COOKIE_NAME)] = None,
) -> models.User:
    token = _extract_bearer_token(authorization) or auth_token
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_id, token_role = _decode_access_token(token)
    user = get_user_store().get_by_id(user_id)
    if user is None or user.role != token_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return user


def require_roles(*roles: models.UserRole):
    def dependency(current_user: Annotated[models.User, Depends(get_current_user)]) -> models.User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this resource")
        return current_user

    return dependency
