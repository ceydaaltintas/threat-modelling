// Thin API client. Every call is made from the browser against the backend
// origin, so the demo needs no server-side proxy.

import type { SystemModelData, SystemModelVersion } from "@/lib/system-model";
import type {
  AuditEntry,
  DashboardData,
  DashboardRun,
  DocumentOut,
  KbSearchResult,
  KbStats,
  ReviewAction,
  ThreatListResponse,
  ThreatRow,
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
  runDocuments: (runId: string) =>
    request<DocumentOut[]>(`/api/runs/${runId}/documents`),
  systemModel: (runId: string) =>
    request<SystemModelVersion>(`/api/runs/${runId}/system-model`),
  saveSystemModel: (runId: string, data: SystemModelData, reason?: string) =>
    request<SystemModelVersion>(`/api/runs/${runId}/system-model`, {
      method: "PUT",
      body: JSON.stringify({ data, reason }),
    }),
  retryStep: (runId: string, stepNo: number) =>
    request<Run>(`/api/runs/${runId}/steps/${stepNo}/retry`, { method: "POST" }),
  uploadRun: async (
    files: File[],
    options: { project_name?: string; auto_continue?: boolean },
  ) => {
    const form = new FormData();
    for (const file of files) form.append("files", file);
    if (options.project_name) form.append("project_name", options.project_name);
    form.append("auto_continue", String(Boolean(options.auto_continue)));

    let response: Response;
    try {
      response = await fetch(`${API_BASE}/api/runs/upload`, {
        method: "POST",
        body: form,
        headers: demoHeaders(),
      });
    } catch {
      throw new ApiError("Arka uca ulaşılamadı. `docker compose up` çalışıyor mu?", 0);
    }
    if (!response.ok) {
      let detail = `Yükleme başarısız (HTTP ${response.status}).`;
      try {
        const body = await response.json();
        if (typeof body?.detail === "string") detail = body.detail;
      } catch {
        /* keep the generic message */
      }
      throw new ApiError(detail, response.status);
    }
    return (await response.json()) as Run;
  },
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
  kbSearch: (q: string, limit = 10) =>
    request<KbSearchResult>(
      `/api/kb/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),
  threats: (runId: string) =>
    request<ThreatListResponse>(`/api/runs/${runId}/threats`),
  reviewThreat: (
    runId: string,
    threatId: string,
    body: {
      action: ReviewAction;
      note?: string;
      likelihood?: number;
      impact?: number;
      reason?: string;
    },
  ) =>
    request<ThreatRow>(`/api/runs/${runId}/threats/${threatId}/review`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  reviewBulk: (
    runId: string,
    body: {
      threat_ids: string[];
      action: "accept" | "reject" | "false_positive" | "reset";
      note?: string;
    },
  ) =>
    request<{ updated: number; review_status: string }>(
      `/api/runs/${runId}/threats/review-bulk`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  dashboard: (runId?: string) =>
    request<DashboardData>(
      `/api/dashboard${runId ? `?run_id=${runId}` : ""}`,
    ),
  dashboardRuns: () => request<DashboardRun[]>("/api/dashboard/runs"),
  reportUrl: (runId: string, name: string) =>
    `${API_BASE}/api/runs/${runId}/reports/${name}`,
};

export function eventStreamUrl(runId: string): string {
  return `${API_BASE}/api/runs/${runId}/events`;
}
