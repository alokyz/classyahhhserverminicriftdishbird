"""FastAPI application for the read-only local Minecraft dashboard."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database, monitoring
from .config import Settings
from .models import (
    BackupsResponse,
    HealthResponse,
    LogsResponse,
    MetricsResponse,
    ModsResponse,
    PlayersResponse,
    ServerStatusResponse,
)

settings = Settings.from_env()


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize_database(settings.db_path)
    yield


app = FastAPI(
    title="classyahhhserverminicriftdishbird",
    description="Read-only local monitoring for a Minecraft Java server.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/server/status", response_model=ServerStatusResponse)
def get_server_status() -> dict:
    return monitoring.server_status(settings)


@app.get("/api/server/players", response_model=PlayersResponse)
def get_players() -> dict:
    return monitoring.player_status(settings)


@app.get("/api/server/metrics", response_model=MetricsResponse)
def get_metrics() -> dict:
    return monitoring.host_metrics()


@app.get("/api/server/logs", response_model=LogsResponse)
def get_logs() -> dict:
    return monitoring.server_logs(settings)


@app.get("/api/server/mods", response_model=ModsResponse)
def get_mods() -> dict:
    return monitoring.mods_inventory(settings)


@app.get("/api/backups", response_model=BackupsResponse)
def get_backups() -> dict:
    return {
        "state": "planned",
        "backups": [],
        "message": "Backup history is planned. Consistent live-world backups are not implemented.",
    }
