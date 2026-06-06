"""JWT auth (HS256) with a demo username/password from settings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from sqlmender.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def authenticate(username: str, password: str) -> bool:
    s = get_settings()
    return username == s.demo_username and password == s.demo_password


def create_access_token(subject: str) -> str:
    s = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def verify_token(token: str = Depends(oauth2_scheme)) -> str:
    s = get_settings()
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError as e:
        raise creds_exc from e
    subject = payload.get("sub")
    if subject is None:
        raise creds_exc
    return subject
