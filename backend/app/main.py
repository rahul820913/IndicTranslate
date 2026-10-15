from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.config import settings
from .db import models  # noqa: F401  (register tables)
from .db.session import Base, engine
from .services.translator import get_translator


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # swap for Alembic migrations once the schema settles
    get_translator().load()  # load the model once, not per request
    yield


app = FastAPI(title="IndicTranslate API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
