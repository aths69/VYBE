import type {
  ConfigResponse,
  EfficiencyAnalysis,
  GPUInfo,
  SessionCalculations,
  SessionComparisonResponse,
  SessionDetail,
  SessionInfo,
  SessionListResponse,
  SessionSummary,
  SystemInfo,
  TelemetrySample,
} from "./types";

// Defaults to the same hostname the dashboard was loaded from, so this works
// whether the app is opened via localhost or from another machine on the
// network (Section 31) - only overridden by VITE_API_BASE_URL if explicitly set.
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? `http://${window.location.hostname}:8000`;

class ApiError extends Error {}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* response wasn't JSON - keep statusText */
    }
    throw new ApiError(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  getGpuInfo: () => request<GPUInfo>("/api/gpu/info"),
  getSystemInfo: () => request<SystemInfo>("/api/system/info"),
  getConfig: () => request<ConfigResponse>("/api/config"),

  startSession: (workloadName: string, intervalSeconds?: number, simulate?: boolean) =>
    request<SessionInfo>("/api/sessions/start", {
      method: "POST",
      body: JSON.stringify({
        workload_name: workloadName,
        interval_seconds: intervalSeconds ?? null,
        simulate: simulate ?? false,
      }),
    }),

  stopSession: (
    sessionId: string,
    usefulOutputCount?: number,
    usefulOutputUnit?: string,
  ) =>
    request<SessionSummary>(`/api/sessions/${sessionId}/stop`, {
      method: "POST",
      body: JSON.stringify({
        useful_output_count: usefulOutputCount ?? null,
        useful_output_unit: usefulOutputUnit ?? null,
      }),
    }),

  getCurrentSession: () => request<SessionInfo>("/api/sessions/current"),
  getSessionStatus: (sessionId: string) =>
    request<SessionInfo>(`/api/sessions/${sessionId}`),

  getSessionTelemetry: (sessionId: string, sinceIndex: number) =>
    request<TelemetrySample[]>(
      `/api/sessions/${sessionId}/telemetry?since_index=${sinceIndex}`,
    ),

  getSessionCalculations: (sessionId: string) =>
    request<SessionCalculations>(`/api/sessions/${sessionId}/calculations`),

  getSessionEfficiency: (sessionId: string) =>
    request<EfficiencyAnalysis>(`/api/sessions/${sessionId}/efficiency`),

  listHistory: (params: {
    limit?: number;
    offset?: number;
    workloadName?: string;
    status?: string;
    sortBy?: string;
    sortDir?: string;
  }) => {
    const q = new URLSearchParams();
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.workloadName) q.set("workload_name", params.workloadName);
    if (params.status) q.set("status", params.status);
    if (params.sortBy) q.set("sort_by", params.sortBy);
    if (params.sortDir) q.set("sort_dir", params.sortDir);
    return request<SessionListResponse>(`/api/sessions/history?${q.toString()}`);
  },

  getSessionDetail: (sessionId: string) =>
    request<SessionDetail>(`/api/sessions/${sessionId}/detail`),

  deleteSession: (sessionId: string) =>
    request<{ deleted: boolean }>(`/api/sessions/${sessionId}`, {
      method: "DELETE",
    }),

  compareSessions: (sessionIds: string[]) => {
    const q = new URLSearchParams();
    sessionIds.forEach((id) => q.append("session_ids", id));
    return request<SessionComparisonResponse>(`/api/sessions/compare?${q.toString()}`);
  },

  // Opened directly in a new tab (window.open) rather than fetched - the
  // endpoint returns a printable HTML page, not JSON.
  getReportUrl: (sessionId: string) => `${API_BASE}/api/sessions/${sessionId}/report`,
};

export { ApiError };
