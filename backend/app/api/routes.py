import hashlib
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import create_token, hash_password, verify_password
from ..db.models import Feedback, Translation, User
from ..db.session import get_db
from ..schemas import (
    AuthIn,
    FeedbackIn,
    HistoryOut,
    LanguageOut,
    TokenOut,
    TranslateIn,
    TranslateOut,
    TranslationOut,
)
from ..services.cache import cache
from ..services.translator import LANGUAGES, get_translator, validate_pair
from .deps import get_current_user, get_optional_user, rate_limit
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ---------- auth ----------
@router.post("/auth/register", response_model=TokenOut, status_code=201)
def register(body: AuthIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_token(user.id))


@router.post("/auth/login", response_model=TokenOut)
def login(body: AuthIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    return TokenOut(access_token=create_token(user.id))


# ---------- translation ----------
@router.get("/languages", response_model=list[LanguageOut])
def languages():
    return [LanguageOut(code=c, name=n) for c, n in LANGUAGES.items()]


def _cache_key(src: str, tgt: str, text: str) -> str:
    # Contains no user identity: only public text + language pair + model version.
    raw = f"{settings.model_version}|{src}|{tgt}|{text}"
    return "tr:" + hashlib.sha256(raw.encode()).hexdigest()


@router.post("/translations", response_model=TranslateOut, dependencies=[Depends(rate_limit)])
def translate(
    body: TranslateIn, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
):
    try:
        validate_pair(body.source_language, body.target_language)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    text = re.sub(r"[ \t]+", " ", body.text).strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter some text to translate.")

    start = time.perf_counter()
    key = _cache_key(body.source_language, body.target_language, text)
    translated = cache.get(key)
    cached = translated is not None
    if not cached:
        try:
            translated = get_translator().translate(text, body.source_language, body.target_language)
        except Exception:
            logger.exception("Translation failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Translation is unavailable right now.",
            ) from None
        cache.set(key, translated, settings.cache_ttl_seconds)
    latency_ms = int((time.perf_counter() - start) * 1000)

    saved_id = None
    if body.save and user:
        row = Translation(
            user_id=user.id,
            source_lang=body.source_language,
            target_lang=body.target_language,
            source_text=text,
            translated_text=translated,
            model_version=settings.model_version,
            latency_ms=latency_ms,
        )
        db.add(row)
        db.commit()
        saved_id = row.id

    return TranslateOut(
        id=saved_id,
        translated_text=translated,
        model_version=settings.model_version,
        latency_ms=latency_ms,
        cached=cached,
    )


@router.get("/translations", response_model=HistoryOut)
def history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    where = Translation.user_id == user.id
    total = db.scalar(select(func.count()).select_from(Translation).where(where)) or 0
    rows = db.scalars(
        select(Translation).where(where).order_by(Translation.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return HistoryOut(items=[TranslationOut.model_validate(r) for r in rows], total=total)


def _owned(db: Session, translation_id: str, user: User) -> Translation:
    row = db.get(Translation, translation_id)
    # 404 (not 403) so IDs of other users' records are not revealed
    if not row or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Translation not found.")
    return row


@router.get("/translations/{translation_id}", response_model=TranslationOut)
def get_translation(translation_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _owned(db, translation_id, user)


@router.delete("/translations/{translation_id}", status_code=204)
def delete_translation(translation_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_owned(db, translation_id, user))
    db.commit()
    return Response(status_code=204)


@router.post("/feedback", status_code=201)
def feedback(body: FeedbackIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _owned(db, body.translation_id, user)
    db.add(Feedback(translation_id=body.translation_id, rating=body.rating, comment=body.comment))
    db.commit()
    return {"status": "received"}


@router.get("/health")
def health():
    return {"status": "ok", "cache": cache.backend, "translator": settings.translator_backend}
