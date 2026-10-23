"""Public response models for the dashboard API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Availability = Literal["available", "unavailable"]
ServerState = Literal["online", "offline", "unknown"]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ServerCapabilities(BaseModel):
    status_query: Availability
    player_sample: Availability
    uptime: Availability
    console_commands: Literal["unsupported"]
    server_type: str
    server_type_source: Literal["configured", "unknown"]


class ServerStatusResponse(BaseModel):
    state: ServerState
    name: str | None
    version: str | None
    players_online: int | None
    players_max: int | None
    uptime_seconds: int | None
    sampled_at: str
    adapter: str
    capabilities: ServerCapabilities


class Player(BaseModel):
    name: str
    uuid: str | None


class PlayersResponse(BaseModel):
    state: Availability
    online: int | None
    max: int | None
    players: list[Player]
    source: str | None


class MetricAvailability(BaseModel):
    host_cpu: Availability
    host_memory: Availability
    jvm_memory: Availability
    tps: Availability


class MetricsResponse(BaseModel):
    host_cpu_percent: float | None
    host_memory_total_bytes: int | None
    host_memory_used_bytes: int | None
    jvm_heap_used_bytes: int | None
    jvm_heap_max_bytes: int | None
    tps: float | None
    availability: MetricAvailability
    sampled_at: str


class LogsResponse(BaseModel):
    state: Availability
    lines: list[str]
    reason: str | None


class ModItem(BaseModel):
    filename: str
    size_bytes: int


class ModsResponse(BaseModel):
    state: Availability
    items: list[ModItem]
    reason: str | None


class BackupsResponse(BaseModel):
    state: Literal["planned"]
    backups: list[dict[str, str | int | None]]
    message: str
