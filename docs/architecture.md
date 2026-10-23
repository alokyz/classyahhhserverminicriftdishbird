# Architecture

## Current implementation

The MVP is a local React/TypeScript/Vite frontend backed by a Python 3.12+ FastAPI service. The frontend polls the backend every 10 seconds and renders API data; it does not read server files or connect directly to Minecraft. The Vite development server binds to `127.0.0.1:5173` and proxies `/api` to `127.0.0.1:8000`.

The backend uses only read operations against the configured Minecraft server. `ServerAdapter` is a small protocol with one implementation, `JavaStatusAdapter`, which queries the standard Minecraft Java status protocol. Vanilla, NeoForge, Forge, Fabric, Quilt, Paper, and Purpur are accepted as configuration labels, but they do not currently select distinct implementations or prove a launch setup was detected. The launch command and installation layout are not inferred.

## API

The application exposes these GET endpoints:

| Endpoint | Current behavior and response |
| --- | --- |
| `/api/health` | `{status: "ok"}` when the FastAPI app responds. |
| `/api/server/status` | `state` (`online`, `offline`, or `unknown`), configured/server-advertised name, version, player counts, `uptime_seconds` (currently null), sample time, adapter name, and capability labels. |
| `/api/server/players` | `state`, nullable online/max counts, up to 100 player samples when supplied by the server, and source. A server may not provide player names. |
| `/api/server/metrics` | Linux host CPU sampled from `/proc/stat` and host memory from `/proc/meminfo`; JVM heap and TPS are explicitly null/unavailable. |
| `/api/server/logs` | A bounded tail of the configured relative log path under the server directory, or an unavailable state and reason. The current bound is at most 256 KiB, the configured maximum of 200 lines, and 4096 characters per line. |
| `/api/server/mods` | Up to 500 regular, non-symlink entries in `mods/`, with filename and size only. Archive metadata is not extracted. |
| `/api/backups` | `planned` with an empty list and explanation. No backup creation or history is exposed. |

The backend models live in `backend/app/models.py`. Log and mod failures currently use a `reason` field. Status/probe failures distinguish `offline` on connection refusal and `unknown` on socket/protocol errors. Oversized packets, unexpected packet IDs, invalid JSON lengths, and excessively nested JSON return `unknown`. Status JSON nesting is limited to 64 levels; description traversal is iterative and limited to 500 nodes and 200 output characters. File inspection reports `unavailable` when the server directory or target is missing or unsafe.

## Persistence and lifecycle

On application startup, SQLite initialization creates three tables: `dashboard_config`, `player_events`, and `backup_metadata`. This is schema preparation only: the current endpoints do not persist configuration, collect player join/leave history, or create world backups. The default database path is `backend/data/dashboard.sqlite3`; `MCDASH_DB_PATH` can override it.

## Configuration and adapters

The backend reads settings from process environment variables prefixed `MCDASH_`. Supported values include loopback bind host and port, configured server directory, status target host and port, display name and server-type label, relative log path, status timeout, and SQLite path. The `.env.example` file documents sample values; the backend itself does not load `.env` files automatically, so the variables must be exported by the shell or supplied by the process manager.

The Java status implementation uses protocol version 767 and a bounded response size. It is implemented but has not been validated against a live Vanilla, NeoForge, Forge, Fabric, Quilt, Paper, or Purpur server. Host CPU and memory collection is implemented for Linux procfs; JVM heap, TPS/tick timing, and uptime remain unavailable. `ServerAdapter` currently has no software-specific variants beyond the standard Java status adapter.

## Validation status

- Verified: `python3 -m pytest backend/tests -q` passed with 27 tests; backend `compileall` and `pyproject.toml` parsing also passed. The suite includes deterministic symlink-swap and malformed-status tests.
- Frontend tests and production build have not run because Vitest, TypeScript, and frontend dependencies are not installed in this environment. No dependencies were installed during implementation.
- No live Minecraft server query has been verified.

Do not describe a capability as supported for a particular server installation until it has been tested with that installation. Backups, session history, launch configuration discovery, JVM/TPS metrics, and server-control actions are not implemented.
