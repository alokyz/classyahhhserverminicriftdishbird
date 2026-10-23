# Security model

## Implemented boundaries

- FastAPI accepts only GET routes. There are no RCON, arbitrary command, or server start/stop/restart endpoints.
- The configured dashboard bind host is restricted to `127.0.0.1`, `::1`, or `localhost`; the default is `127.0.0.1`. The Vite development server also binds to `127.0.0.1`. FastAPI CORS allows the two local Vite origins, GET requests, and the `Accept` header, without credentials.
- Backend settings are read from a whitelist of `MCDASH_` environment variables. API responses do not serialize the environment or credentials.
- Server file reads require a configured existing server directory. The log path must be relative and cannot contain `..`; server paths are checked beneath the canonical server root. Log reads and mod listings then use root-anchored, descriptor-relative traversal with `O_NOFOLLOW` for path components and files. Missing or rejected paths yield an unavailable response.
- The log endpoint reads a bounded tail (256 KiB maximum, 200 lines by default, and 4096 characters per returned line) and strips non-printable characters except tabs. The mods endpoint lists at most 500 regular files and skips symlinks; it reads filenames and sizes, not archive contents.
- The Java status query sends only the protocol handshake and status request, not game commands. The configured server host/port is read from local environment configuration, not from browser request parameters.
- The frontend renders log lines, player names, and mod filenames as React text. It does not interpret them as HTML.
- SQLite startup creates schema tables only; it does not copy world files. JVM heap, TPS, and uptime are not fabricated when unavailable.

## Filesystem limitations

The log and mod file operations use root-anchored directory descriptors and no-follow opens, rather than relying on a prior pathname check alone. Deterministic tests replace the validated `logs/` and `mods/` directories with symlinks before the read/list operation and verify that outside files are not returned. This covers the tested swap scenario; continue to treat the configured server directory as trusted local data.

The SQLite path is user-configurable with `MCDASH_DB_PATH` and is not restricted beneath the server directory. Choose a trusted local path. The application currently does not check for a symlinked database target before SQLite opens it.

## Deployment and data guidance

- Run the service as the ordinary desktop user, never root.
- Keep the dashboard loopback-only. The local app has no authentication; do not expose it to the LAN or internet, forward its ports, or change firewall rules.
- Set `MCDASH_SERVER_DIR` only to the intended server directory. The backend does not discover arbitrary directories. Avoid configuring a directory writable by untrusted users.
- Keep `.env`, SQLite files, logs, worlds, and backups out of source control. `.env.example` contains sample configuration only. The backend reads process environment; it does not load `.env` automatically.
- Avoid collecting player activity beyond the server-provided status sample. Join/leave history is not currently collected.
- Do not copy active world files as a backup. Backup creation is planned until a consistency strategy can be implemented and validated.

## Remaining verification

Verified: `python3 -m pytest backend/tests -q` passed with 27 tests, and backend `compileall` plus `pyproject.toml` parsing passed. The suite includes path/config, bounded-log, SQLite, deterministic log/mod symlink-swap, malformed/oversized packet, and deeply nested JSON checks. Frontend tests and production build remain pending because dependencies are unavailable. No live-server protocol query has been verified. The database path remains user-configurable and is not checked for symlink targets before SQLite opens it; choose a trusted local path.
