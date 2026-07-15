from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.routers.tracks import router as tracks_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.audio_root.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Eureka Music Server", version="0.1.0", lifespan=lifespan)
app.include_router(tracks_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
