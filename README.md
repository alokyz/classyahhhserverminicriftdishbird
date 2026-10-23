# classyahhhserverminicriftdishbird

> maybe working minicriftdashboard (holy vibecode ahahhah hoy ahhh)

A local Minecraft Java server command center for Fedora KDE and other Linux desktops. This project starts with a read-only dashboard: it does not control the server, execute commands, install mods, or expose itself to the network.

## What is implemented

The source now includes a read-only FastAPI API, a React/Vite dashboard, a Java status-protocol adapter, Linux host CPU/RAM sampling, bounded log-tail reading, safe mod filename/size inventory, and SQLite tables prepared for configuration, player-event history, and backup metadata. The frontend polls the API every 10 seconds and renders untrusted text as text.

The backend test suite passes in the current environment. The frontend tests/build and a live API/server query have not been verified here because frontend dependencies and FastAPI are not installed. Install project dependencies using the steps below before treating the full application as runnable. No live Minecraft server was available for protocol validation.

TPS, JVM heap values, uptime, player session history, launch-layout detection, and consistent live-world backups remain unavailable or planned. SQLite schema preparation does not mean player history is collected or backups are created.

Supported server labels include Vanilla, NeoForge, Forge, Fabric, Quilt, Paper, and Purpur. The dashboard does not assume their launch scripts or installation layouts are interchangeable. It uses a configurable server directory and a standard Java server status query; additional server-specific capabilities must be detected and documented.

## Requirements

- Python 3.12 or newer.
- Node.js and npm versions supported by the selected Vite release.
- A Minecraft Java server reachable at the configured status host and port for live status/player data.
- A local server directory configured explicitly before reading logs or mods.

No system packages or privileged services are required. The app should run as your normal desktop user and bind to `127.0.0.1`.

## Setup

1. Copy `.env.example` to `.env` and set `MCDASH_SERVER_DIR` to the server directory you want the dashboard to inspect. Keep the bind host at `127.0.0.1` unless you have deliberately reviewed the security implications.
2. Create and activate a Python virtual environment, then install the backend project dependencies:

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -e 'backend[test]'
   ```

3. Install the frontend dependencies and start the Vite development server:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

4. In another terminal from the project root, start the API:

   ```sh
   source .venv/bin/activate
   set -a
   source .env
   set +a
   python -m uvicorn app.main:app --app-dir backend --host "$MCDASH_BIND_HOST" --port "$MCDASH_PORT"
   ```

5. Open the local address printed by Vite, normally `http://127.0.0.1:5173`.

The API should remain bound to loopback. Do not forward ports or change firewall settings as part of setup.

## Configuration

Configuration is supplied through environment variables; `.env` is local and ignored by Git. The example file documents the dashboard bind host/port, the optional server directory, Java status host/port, display name, server type label, relative log path, and local SQLite database path. File reads must stay inside the configured server directory, including when symlinks are present.

## API

- `GET /api/health`
- `GET /api/server/status`
- `GET /api/server/players`
- `GET /api/server/metrics`
- `GET /api/server/logs`
- `GET /api/server/mods`
- `GET /api/backups`

See `docs/architecture.md` for response contracts, adapters, and implemented capabilities. Unavailable information should use explicit states and null values rather than sample data.

## Development checks

From the project root:

```sh
python -m pytest backend/tests
```

For frontend checks, run the scripts listed in `frontend/package.json`, including its tests, type check, lint (if configured), and production build. Tests and build are only considered passing when run successfully in the current environment.

From `frontend/`, the configured checks are:

```sh
npm test
npm run build
```

## Security and limitations

The dashboard is read-only. It does not implement RCON, start/stop/restart controls, arbitrary command execution, automatic mod changes, or live-world backup creation. Logs are untrusted text and should be rendered as text, with a bounded tail. TPS, JVM heap, uptime, and session history are unavailable unless a compatible source is implemented and validated. Connecting an actual NeoForge installation requires setting the server directory and status host/port; the launch configuration is not inferred as a universal format.

See `docs/security.md` before changing network exposure or file access behavior.

## Original repository note

> (btw i accidentally picked random liscence so uhmm woo)
