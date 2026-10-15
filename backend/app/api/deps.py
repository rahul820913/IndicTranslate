import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import decode_token
from ..db.models import User
from ..db.session import get_db
from ..services.cache import cache

bearer = HTTPBearer(auto_error=False)


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User | None:
    if not creds:
        return None
    user_id = decode_token(creds.credentials)
    return db.get(User, user_id) if user_id else None


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    return user


def rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    key = f"rl:{ip}:{int(time.time() // 60)}"
    if cache.incr(key, 60) > settings.rate_limit_per_minute:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Try again in a minute.")
