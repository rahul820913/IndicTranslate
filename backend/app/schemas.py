import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .core.config import settings


class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LanguageOut(BaseModel):
    code: str
    name: str


class TranslateIn(BaseModel):
    text: str = Field(min_length=1, max_length=settings.max_chars)
    source_language: str
    target_language: str
    save: bool = False  # only stored when the caller is authenticated


class TranslateOut(BaseModel):
    id: str | None = None
    translated_text: str
    model_version: str
    latency_ms: int
    cached: bool


class TranslationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_lang: str
    target_lang: str
    source_text: str
    translated_text: str
    model_version: str
    latency_ms: int
    created_at: dt.datetime


class HistoryOut(BaseModel):
    items: list[TranslationOut]
    total: int


class FeedbackIn(BaseModel):
    translation_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)
