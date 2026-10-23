import { useCallback, useEffect, useRef, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import {
  getJson,
  type BackupsResponse,
  type HealthResponse,
  type LogsResponse,
  type MetricsResponse,
  type ModsResponse,
  type PlayersResponse,
  type ServerStatus,
} from "./api";

type Panel<T> = { data: T | null; error: string | null; loading: boolean };
const emptyPanel = <T,>(): Panel<T> => ({ data: null, error: null, loading: true });

function useDashboard() {
  const [health, setHealth] = useState<Panel<HealthResponse>>(emptyPanel);
  const [status, setStatus] = useState<Panel<ServerStatus>>(emptyPanel);
  const [players, setPlayers] = useState<Panel<PlayersResponse>>(emptyPanel);
  const [metrics, setMetrics] = useState<Panel<MetricsResponse>>(emptyPanel);
  const [logs, setLogs] = useState<Panel<LogsResponse>>(emptyPanel);
  const [mods, setMods] = useState<Panel<ModsResponse>>(emptyPanel);
  const [backups, setBackups] = useState<Panel<BackupsResponse>>(emptyPanel);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const requestInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setRefreshing(true);
    const load = async <T,>(path: string, update: Dispatch<SetStateAction<Panel<T>>>) => {
      update((previous) => ({ ...previous, error: null, loading: previous.data === null }));
      try {
        const data = await getJson<T>(path);
        update({ data, error: null, loading: false });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Could not load this information.";
        update((previous) => ({ ...previous, error: message, loading: false }));
      }
    };

    await Promise.all([
      load("/api/health", setHealth),
      load("/api/server/status", setStatus),
      load("/api/server/players", setPlayers),
      load("/api/server/metrics", setMetrics),
      load("/api/server/logs", setLogs),
      load("/api/server/mods", setMods),
      load("/api/backups", setBackups),
    ]);

    setLastUpdated(new Date());
    requestInFlight.current = false;
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 10_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return { health, status, players, metrics, logs, mods, backups, lastUpdated, refreshing, refresh };
}

function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value) || value < 0) return "Unavailable";
  if (value < 1024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let scaled = value / 1024;
  let index = 0;
  while (scaled >= 1024 && index < units.length - 1) {
    scaled /= 1024;
    index += 1;
  }
  return `${scaled.toFixed(scaled < 10 ? 1 : 0)} ${units[index]}`;
}

function formatPercent(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value)}%` : "Unavailable";
}

function formatTimestamp(value: string | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatUptime(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value) || value < 0) return "Unavailable";
  const seconds = Math.floor(value);
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
}

function Icon({ name, size = 18 }: { name: "grid" | "users" | "activity" | "terminal" | "box" | "archive" | "refresh" | "server"; size?: number }) {
  const paths: Record<typeof name, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    activity: <><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></>,
    terminal: <><path d="m4 17 6-6-6-6"/><path d="M12 19h8"/></>,
    box: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 8 9 5 9-5M3 16l9 5 9-5M3 8v8m18-8v8M12 13v8"/></>,
    archive: <><rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v12h14V8M10 12h4"/></>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.6 9a7 7 0 0 1 11.55-2.6L20 12M4 12l2.85 5.6A7 7 0 0 0 18.4 15"/></>,
    server: <><rect x="3" y="3" width="18" height="8" rx="2"/><rect x="3" y="13" width="18" height="8" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/></>,
  };
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function PanelMessage({ state, error, message }: { state: "loading" | "error" | "unavailable" | "empty"; error?: string | null; message?: string | null }) {
  if (state === "loading") return <div className="panel-message"><span className="spinner" />Connecting to local API…</div>;
  if (state === "error") return <div className="panel-message panel-message--error"><span className="message-mark">!</span>{error || "Could not reach the local API."}</div>;
  if (state === "unavailable") return <div className="panel-message"><span className="message-mark">—</span>{message || "This information is not available yet."}</div>;
  return <div className="panel-message"><span className="message-mark">·</span>{message || "Nothing to show yet."}</div>;
}

function Metric({ label, value, unit, icon, detail }: { label: string; value: string; unit?: string; icon: "cpu" | "memory" | "chip" | "activity"; detail?: string }) {
  return <div className="metric-row">
    <div className={`metric-icon metric-icon--${icon}`} aria-hidden="true">{icon === "cpu" ? "⌁" : icon === "memory" ? "▤" : icon === "activity" ? "↗" : "◈"}</div>
    <div className="metric-copy"><span>{label}</span><small>{detail || "Host resource"}</small></div>
    <strong>{value}{unit && value !== "Unavailable" ? <small className="metric-unit">{unit}</small> : null}</strong>
  </div>;
}

function App() {
  const data = useDashboard();
  const status = data.status.data;
  const players = data.players.data;
  const metrics = data.metrics.data;
  const logs = data.logs.data;
  const mods = data.mods.data;
  const backups = data.backups.data;
  const serverState = status?.state || "unknown";
  const serverLabel = serverState === "online" ? "Online" : serverState === "offline" ? "Offline" : "Status unknown";
  const apiConnected = data.health.data?.status === "ok";
  const playersAvailable = players?.state === "available";
  const logsAvailable = logs?.state === "available";
  const modsAvailable = mods?.state === "available";
  const cpu = formatPercent(metrics?.host_cpu_percent);
  const hostMemory = metrics?.host_memory_used_bytes != null && metrics.host_memory_total_bytes != null
    ? `${formatBytes(metrics.host_memory_used_bytes)} / ${formatBytes(metrics.host_memory_total_bytes)}`
    : "Unavailable";
  const jvmMemory = metrics?.jvm_heap_used_bytes != null && metrics.jvm_heap_max_bytes != null
    ? `${formatBytes(metrics.jvm_heap_used_bytes)} / ${formatBytes(metrics.jvm_heap_max_bytes)}`
    : "Unavailable";
  const uptime = formatUptime(status?.uptime_seconds);
  const playerSampleEmpty = playersAvailable && (players?.players.length ?? 0) === 0;
  const playerEmptyMessage = players?.online != null && players.online > 0
    ? `The server reports ${players.online} online, but did not provide their names.`
    : players?.online === 0
      ? "It’s quiet in here. No players are online."
      : "Player names are unavailable from the server.";

  const goTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#top" aria-label="Classyhhh Server Command Center home">
        <span className="brand-mark"><Icon name="server" size={20}/></span>
        <span className="brand-name">classyhhh<span>server control</span></span>
      </a>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Dashboard sections">
        <button className="nav-item nav-item--active" onClick={() => goTo("overview")}><Icon name="grid"/> Overview</button>
        <button className="nav-item" onClick={() => goTo("players")}><Icon name="users"/> Players</button>
        <button className="nav-item" onClick={() => goTo("performance")}><Icon name="activity"/> Performance</button>
        <button className="nav-item" onClick={() => goTo("console")}><Icon name="terminal"/> Console & logs</button>
        <button className="nav-item" onClick={() => goTo("mods")}><Icon name="box"/> Mods</button>
        <button className="nav-item" onClick={() => goTo("backups")}><Icon name="archive"/> Backups</button>
      </nav>
      <div className="sidebar-bottom">
        <div className="privacy-card"><span className="privacy-dot"/><div><strong>Local by default</strong><small>Dashboard is designed for your machine.</small></div></div>
        <div className="sidebar-foot"><span className="tiny-cube">✳</span> A tiny server, big dreams.</div>
      </div>
    </aside>

    <main id="top" className="main-content">
      <header className="topbar">
        <div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>Overview</strong></div>
        <div className="top-actions">
          <div className={`api-indicator ${apiConnected ? "is-connected" : data.health.loading ? "is-waiting" : "is-disconnected"}`}><span/> {apiConnected ? "API connected" : data.health.loading ? "Connecting" : "API unavailable"}</div>
          <button className="refresh-button" onClick={() => void data.refresh()} disabled={data.refreshing} aria-label="Refresh dashboard">
            <Icon name="refresh" size={16}/><span>{data.refreshing ? "Refreshing" : "Refresh"}</span>
          </button>
        </div>
      </header>

      <section id="overview" className="welcome-row">
        <div>
          <div className="eyebrow"><span className="eyebrow-line"/> SERVER COMMAND CENTER</div>
          <h1>Good things are <em>loading.</em></h1>
          <p className="welcome-subtitle">Your little window into the world you built.</p>
        </div>
        <div className="last-updated"><span className="pulse-dot"/> Updated {data.lastUpdated ? data.lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}<span className="update-separator">·</span> Auto refresh 10s</div>
      </section>

      <section className="server-banner" aria-label="Minecraft server status">
        <div className="banner-glow"/>
        <div className="banner-content">
          <div className="banner-label"><span className={`status-dot status-dot--${serverState}`}/>{serverLabel}</div>
          {data.status.loading && !status ? <h2>Finding your server<span className="loading-ellipsis">…</span></h2> : <h2>{status?.name || "Your Minecraft server"}</h2>}
          <p>{status?.version ? <>Minecraft Java <span className="version-chip">{status.version}</span></> : data.status.error && !status ? `Server status unavailable · ${data.status.error}` : "Waiting for a compatible server status response"}</p>
          <div className="banner-meta">
            <span><Icon name="server" size={15}/>{status?.adapter || "Adapter unknown"}</span>
            <span><span className="meta-separator"/> Updated {formatTimestamp(status?.sampled_at)}</span>
          </div>
        </div>
        <div className="banner-right">
          <div className="player-total"><strong>{typeof status?.players_online === "number" ? status.players_online : "—"}</strong><span>/ {typeof status?.players_max === "number" ? status.players_max : "—"}</span></div>
          <div className="player-total-label">PLAYERS ONLINE</div>
          <div className="player-dots" aria-hidden="true">{Array.from({ length: Math.min(status?.players_max ?? 0, 12) }, (_, index) => <i key={index} className={index < (status?.players_online ?? 0) ? "dot-filled" : ""}/>)}</div>
        </div>
      </section>

      <div className="summary-grid">
        <article className="summary-card">
          <div className="card-heading"><span className="section-icon section-icon--green"><Icon name="users" size={17}/></span><span>Players online</span><span className="card-kebab">···</span></div>
          <div className="summary-value">{playersAvailable && typeof players?.online === "number" ? players.online : "—"}<small>{playersAvailable && typeof players?.max === "number" ? ` / ${players.max}` : ""}</small></div>
          <div className="summary-foot">{playersAvailable ? playerSampleEmpty && players?.online && players.online > 0 ? `Names unavailable · ${players.online} online` : players?.online === 0 ? "No players online" : `${players?.players.length ?? 0} listed right now` : players?.state === "unavailable" ? "Player list unavailable" : "Awaiting server response"}</div>
        </article>
        <article className="summary-card">
          <div className="card-heading"><span className="section-icon section-icon--blue"><Icon name="activity" size={17}/></span><span>Host CPU</span><span className="card-kebab">···</span></div>
          <div className="summary-value">{cpu === "Unavailable" ? "—" : cpu}</div>
          <div className="mini-meter"><span style={{ width: cpu === "Unavailable" ? "0%" : cpu }}/></div>
          <div className="summary-foot">{cpu === "Unavailable" ? "Metric unavailable" : "Current host usage"}</div>
        </article>
        <article className="summary-card">
          <div className="card-heading"><span className="section-icon section-icon--purple"><Icon name="server" size={17}/></span><span>Server uptime</span><span className="card-kebab">···</span></div>
          <div className="summary-value summary-value--text">{uptime}</div>
          <div className="summary-foot">{uptime === "Unavailable" ? "Not reported by status query" : "Reported by the configured source"}</div>
        </article>
      </div>

      <div className="content-grid">
        <section id="players" className="panel players-panel">
          <div className="panel-header"><div><span className="panel-icon panel-icon--mint"><Icon name="users"/></span><div><h3>Who’s playing</h3><p>The people in your world right now</p></div></div><span className="panel-count">{playersAvailable ? players?.online ?? players?.players.length ?? 0 : "—"}</span></div>
          {data.players.loading && !players ? <PanelMessage state="loading"/> : data.players.error && !players ? <PanelMessage state="error" error={data.players.error}/> : !playersAvailable ? <PanelMessage state="unavailable" message={players?.state === "unavailable" ? "The server can’t provide a player list right now." : data.players.error}/> : players?.players.length ? <ul className="player-list">{players.players.map((player, index) => <li key={player.uuid || `${player.name}-${index}`}><span className={`avatar avatar-${index % 5}`}>{player.name.slice(0, 1).toUpperCase()}</span><span className="player-name">{player.name}</span><span className="player-online"><i/>Online</span></li>)}</ul> : <PanelMessage state="empty" message={playerEmptyMessage}/>}
          <div className="panel-footer">{playersAvailable ? `Source: ${players?.source || "server status"}` : "Player names are shown only when provided by the server."}</div>
        </section>

        <section id="performance" className="panel performance-panel">
          <div className="panel-header"><div><span className="panel-icon panel-icon--blue"><Icon name="activity"/></span><div><h3>System pulse</h3><p>Host and Minecraft process resources</p></div></div><span className="live-tag"><i/> LIVE</span></div>
          {data.metrics.loading && !metrics ? <PanelMessage state="loading"/> : data.metrics.error && !metrics ? <PanelMessage state="error" error={data.metrics.error}/> : <div className="metrics-list">
            <Metric icon="cpu" label="Host CPU" value={cpu} detail="System utilization"/>
            <Metric icon="memory" label="Host memory" value={hostMemory} detail="Used / total"/>
            <Metric icon="chip" label="JVM heap" value={jvmMemory} detail="Minecraft process only"/>
            <Metric icon="activity" label="Tick rate" value={metrics?.tps == null ? "Unavailable" : `${metrics.tps.toFixed(1)} TPS`} detail="Requires a compatible server source"/>
          </div>}
          <div className="panel-footer">Host memory and JVM heap are separate measurements.</div>
        </section>

        <section id="console" className="panel logs-panel">
          <div className="panel-header"><div><span className="panel-icon panel-icon--amber"><Icon name="terminal"/></span><div><h3>Log window</h3><p>Read-only tail from the configured server log</p></div></div><span className="readonly-tag">READ ONLY</span></div>
          {data.logs.loading && !logs ? <PanelMessage state="loading"/> : data.logs.error && !logs ? <PanelMessage state="error" error={data.logs.error}/> : !logsAvailable ? <PanelMessage state="unavailable" message={logs?.reason || "No compatible server log is configured."}/> : logs?.lines.length ? <div className="log-window" role="log" aria-label="Recent server log lines" aria-live="polite">{logs.lines.map((line, index) => <div className="log-line" key={`${index}-${line}`}><span className="log-index">{String(index + 1).padStart(2, "0")}</span><span className="log-text">{line}</span></div>)}</div> : <PanelMessage state="empty" message={logs?.reason || "The configured log is empty."}/>}
          <div className="panel-footer"><span className="log-lock">⌑</span> Log contents are displayed as plain text.</div>
        </section>

        <section id="mods" className="panel mods-panel">
          <div className="panel-header"><div><span className="panel-icon panel-icon--purple"><Icon name="box"/></span><div><h3>Mod shelf</h3><p>Files found in your configured mods folder</p></div></div><span className="panel-count">{modsAvailable ? mods?.items.length ?? 0 : "—"}</span></div>
          {data.mods.loading && !mods ? <PanelMessage state="loading"/> : data.mods.error && !mods ? <PanelMessage state="error" error={data.mods.error}/> : !modsAvailable ? <PanelMessage state="unavailable" message={mods?.reason || "No compatible mods folder is configured."}/> : mods?.items.length ? <ul className="mod-list">{mods.items.map((mod) => <li key={mod.filename}><span className="file-badge">JAR</span><span className="mod-file"><strong>{mod.filename}</strong><small>{formatBytes(mod.size_bytes)}</small></span><span className="mod-check" aria-label="Read only">↗</span></li>)}</ul> : <PanelMessage state="empty" message={mods?.reason || "No mod files found."}/>}
          <div className="panel-footer">Inventory only · files are never changed automatically.</div>
        </section>

        <section id="backups" className="panel backup-panel">
          <div className="panel-header"><div><span className="panel-icon panel-icon--rose"><Icon name="archive"/></span><div><h3>World backups</h3><p>Safe snapshots, when ready</p></div></div><span className="planned-tag">PLANNED</span></div>
          <div className="backup-empty"><div className="backup-art"><span className="backup-star">✳</span><Icon name="archive" size={27}/></div><strong>Backups are on the roadmap</strong><p>World files need a consistency strategy before a snapshot can be trusted.</p></div>
          <div className="panel-footer">{backups?.message || "No world files are copied by this dashboard."}</div>
        </section>
      </div>

      <footer className="page-footer"><span>Made for the worlds you keep coming back to.</span><span>Local dashboard <i/> read-only MVP</span></footer>
    </main>
  </div>;
}

export { formatBytes, formatPercent };
export default App;
