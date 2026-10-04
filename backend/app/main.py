"""FastAPI entry point for MarketMiner."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers.analytics import router as analytics_router
from app.routers.data import router as data_router
from app.routers.experiments import router as experiments_router
import app.models.experiment  # noqa: F401 - register metadata before create_all

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize the local database schema when the API starts."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(data_router)
app.include_router(analytics_router)
app.include_router(experiments_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok", "service": "marketminer-api"}
