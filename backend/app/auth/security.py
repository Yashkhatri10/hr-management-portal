from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from app.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int, role: str, email: str, expires_in_seconds: int = 28800) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        claims["sub"] = int(claims["sub"])
        return claims
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from exc
