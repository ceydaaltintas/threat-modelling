// Thin API client. Every call is made from the browser against the backend
// origin, so the demo needs no server-side proxy.

import type {
  AuditEntry,
  KbStats,
  Meta,
  ProgressEvent,
  ProjectRow,
  Run,
  SampleScenario,
} from "@/lib/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

/** Demo-only identity. A real deployment plugs in the bank's SSO here. */
function demoHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const role = window.localStorage.getItem("tm.role") ?? "security_expert";
  const actor =
    role === "manager" ? "yonetici@ornekbanka.local" : "uzman@ornekbanka.local";
  return { "x-demo-role": role, "x-demo-actor": actor };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        "content-type": "application/json",
        ...demoHeaders(),
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(
      "Arka uca ulaşılamadı. `docker compose up` çalışıyor mu?",
      0,
    );
  }

  if (!response.ok) {
    let detail = `İstek başarısız (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* body was not JSON; keep the generic message */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  meta: () => request<Meta>("/api/meta"),
  samples: () => request<SampleScenario[]>("/api/samples"),
  projects: () => request<ProjectRow[]>("/api/projects"),
  run: (runId: string) => request<Run>(`/api/runs/${runId}`),
  runLog: (runId: string) => request<ProgressEvent[]>(`/api/runs/${runId}/log`),
  createRun: (body: {
    project_name?: string;
    sample_key?: string;
    auto_continue?: boolean;
  }) =>
    request<Run>("/api/runs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  resumeRun: (runId: string) =>
    request<Run>(`/api/runs/${runId}/resume`, { method: "POST" }),
  cancelRun: (runId: string) =>
    request<Run>(`/api/runs/${runId}/cancel`, { method: "POST" }),
  audit: (params?: { run_id?: string; action?: string }) => {
    const query = new URLSearchParams();
    if (params?.run_id) query.set("run_id", params.run_id);
    if (params?.action) query.set("action", params.action);
    const suffix = query.toString() ? `?${query}` : "";
    return request<AuditEntry[]>(`/api/audit${suffix}`);
  },
  kbStats: () => request<KbStats>("/api/kb/stats"),
  kbSearch: (q: string) =>
    request<{
      query: string;
      mode: string;
      note: string;
      results: Array<{
        id: string;
        source: string;
        identifier: string;
        title: string;
        url: string | null;
        license: string | null;
      }>;
    }>(`/api/kb/search?q=${encodeURIComponent(q)}`),
};

export function eventStreamUrl(runId: string): string {
  return `${API_BASE}/api/runs/${runId}/events`;
}
