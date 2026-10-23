# classyahhhserverminicriftdishbird project instructions

Build a local, read-only Minecraft Java server dashboard. Inspect existing files, applicable instructions, and current Git state before editing. Preserve user changes, credentials, the project identity, and the BSD 3-Clause license if one exists.

## Delegation and ownership

- Delegate substantial independent work only when it improves speed or coverage. Assign focused roles, concrete deliverables, and exclusive file ownership.
- Keep API contracts and integration decisions with the orchestrator. Backend owns `backend/**`; frontend owns `frontend/**`; architecture/security documentation owns `docs/architecture.md` and `docs/security.md`; orchestrator owns root files and integration.
- All agents share a working directory. Avoid concurrent edits to the same files. Review each agent's diff and claims before integrating.
- Work alone for trivial, tightly coupled tasks. Do not create a fixed team when a task does not justify one.

## Safety and product boundaries

- Bind to `127.0.0.1` by default; never expose the service to LAN or internet or alter firewall rules automatically.
- Treat all server files as read-only. Resolve configured paths beneath the explicitly configured server directory and reject traversal and symlink escapes.
- Never execute browser-supplied shell commands. Do not implement RCON, server start/stop/restart controls, or arbitrary commands.
- Do not fabricate TPS, uptime, player history, JVM metrics, or adapter capabilities. Return explicit unknown or unavailable states when unsupported.
- Never read unrelated machine files or expose environment values, secrets, or credentials.
- Do not add, delete, install, or modify Minecraft mods. Do not create backups from live world files without a verified consistency strategy.
- Do not run destructive commands, install system-wide dependencies, spend money, or weaken security settings without the user's approval.

## Integration and checks

- Keep backend and frontend contracts documented and consistent. Verify the backend and frontend independently, then test the integrated API path where available.
- Run relevant existing tests and builds, fix regressions caused by the work, and report checks that could not run with the reason.
- Do not claim support for server layouts or metrics unless implementation and checks establish it. Keep setup steps and limitations current in the README.
