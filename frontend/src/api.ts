export type ServerState = "online" | "offline" | "unknown";
export type Availability = "available" | "unavailable";

export interface ServerStatus {
  state: ServerState;
  name: string | null;
  version: string | null;
  players_online: number | null;
  players_max: number | null;
  uptime_seconds: number | null;
  sampled_at: string;
  adapter: string;
  capabilities: Record<string, unknown>;
}

export interface Player {
  name: string;
  uuid: string | null;
}

export interface PlayersResponse {
  state: Availability;
  online: number | null;
  max: number | null;
  players: Player[];
  source: string | null;
}

export interface MetricsResponse {
  host_cpu_percent: number | null;
  host_memory_total_bytes: number | null;
  host_memory_used_bytes: number | null;
  jvm_heap_used_bytes: number | null;
  jvm_heap_max_bytes: number | null;
  tps: number | null;
  availability?: Record<string, Availability | string>;
}

export interface LogsResponse {
  state: Availability;
  lines: string[];
  reason: string | null;
}

export interface ModItem {
  filename: string;
  size_bytes: number;
  metadata?: Record<string, unknown> | null;
}

export interface ModsResponse {
  state: Availability;
  items: ModItem[];
  reason: string | null;
}

export interface BackupsResponse {
  state: "planned";
  backups: Array<Record<string, string | number | null>>;
  message?: string | null;
}

export interface HealthResponse {
  status: string;
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}
