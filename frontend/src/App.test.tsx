import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import App, { formatBytes, formatPercent } from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function stubDashboardApi(playersResponse: unknown, logLines: string[] = []) {
  const payloads: Record<string, unknown> = {
    "/api/health": { status: "ok" },
    "/api/server/status": {
      state: "online", name: "Tiny World", version: "1.21.1", players_online: 1,
      players_max: 20, uptime_seconds: 120, sampled_at: "2026-10-23T09:00:00Z", adapter: "java-status", capabilities: {},
    },
    "/api/server/players": playersResponse,
    "/api/server/metrics": {
      host_cpu_percent: 12, host_memory_total_bytes: 1024, host_memory_used_bytes: 512,
      jvm_heap_used_bytes: null, jvm_heap_max_bytes: null, tps: null,
    },
    "/api/server/logs": { state: "available", lines: logLines, reason: null },
    "/api/server/mods": { state: "available", items: [], reason: null },
    "/api/backups": { state: "planned", backups: [], message: "Planned" },
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    const body = payloads[path];
    return new Response(JSON.stringify(body), { status: body ? 200 : 404, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("display formatting", () => {
  it("keeps missing metrics explicit", () => {
    expect(formatBytes(null)).toBe("Unavailable");
    expect(formatPercent(undefined)).toBe("Unavailable");
  });

  it("formats byte values without inventing data", () => {
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
  });
});

describe("dashboard API rendering", () => {
  it("loads real endpoint data and renders log content as text", async () => {
    const hostileText = '<img src=x onerror="alert(1)">';
    const fetchMock = stubDashboardApi({
      state: "available", online: 1, max: 20, players: [{ name: "Alex", uuid: null }], source: "status_protocol",
    }, [hostileText]);

    render(<App />);

    expect(await screen.findByText("Tiny World")).toBeInTheDocument();
    expect(await screen.findByText(hostileText)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/server/logs", expect.objectContaining({ headers: { Accept: "application/json" } }));
  });

  it("does not say nobody is online when the server omits its player-name sample", async () => {
    stubDashboardApi({ state: "available", online: 2, max: 20, players: [], source: "status_protocol" });

    render(<App />);

    expect(await screen.findByText("The server reports 2 online, but did not provide their names.")).toBeInTheDocument();
    expect(screen.queryByText("It’s quiet in here. No players are online.")).not.toBeInTheDocument();
  });

  it("navigates to dashboard sections and highlights the selected section", async () => {
    stubDashboardApi({ state: "available", online: 0, max: 20, players: [], source: "status_protocol" });

    render(<App />);

    const playersLink = screen.getByRole("link", { name: "Players" });
    expect(playersLink).toHaveAttribute("href", "#players");
    fireEvent.click(playersLink);
    expect(playersLink).toHaveAttribute("aria-current", "location");

    const modsLink = screen.getByRole("link", { name: "Mods" });
    expect(modsLink).toHaveAttribute("href", "#mods");
    fireEvent.click(modsLink);
    expect(modsLink).toHaveAttribute("aria-current", "location");
  });
});
