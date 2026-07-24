"""DART0s FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, disclosures, admin, dev, notices


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background services on startup, clean up on shutdown."""
    # Startup: initialize background poller etc.
    from app.services.dart_poller import start_poller, stop_poller
    await start_poller()
    yield
    # Shutdown
    await stop_poller()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(disclosures.router, prefix="/api/v1/disclosures", tags=["disclosures"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(notices.router, prefix="/api/v1", tags=["notices"])
app.include_router(dev.router, prefix="/api/v1/dev", tags=["developer"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}
