// Typed fetch wrappers for the FastAPI backend. The base URL comes from
// NEXT_PUBLIC_API_BASE_URL and falls back to http://localhost:8000. Every
// endpoint here maps directly to the REST contract in tasks/ORCHESTRATION.md.

import type {
  DefaultConfigResponse,
  SampleScenariosResponse,
  ScheduleRequest,
  ScheduleResponse,
  SimulateRequest,
  SimulateResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Thrown for any non-2xx response. `detail` carries the backend message so the
// UI can show a 422 validation reason verbatim near the controls.
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      0,
      `Could not reach the backend at ${API_BASE_URL}. Make sure it is running.`,
    );
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response));
  }

  return (await response.json()) as T;
}

// FastAPI puts validation messages under `detail`. That value can be a string
// or a list of field errors, so normalize both into one readable line.
async function readDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          const loc = Array.isArray((item as { loc?: unknown[] }).loc)
            ? (item as { loc: unknown[] }).loc.join(".")
            : "";
          const msg = (item as { msg?: string }).msg ?? "invalid value";
          return loc ? `${loc}: ${msg}` : msg;
        })
        .join("; ");
    }
  } catch {
    // Fall through to the generic message below.
  }
  return `Request failed with status ${response.status}.`;
}

export function getDefaultConfig(): Promise<DefaultConfigResponse> {
  return request<DefaultConfigResponse>("/api/config/default");
}

export function getSampleScenarios(): Promise<SampleScenariosResponse> {
  return request<SampleScenariosResponse>("/api/scenarios/sample");
}

export function postSimulate(
  payload: SimulateRequest,
): Promise<SimulateResponse> {
  return request<SimulateResponse>("/api/simulate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function postSchedule(
  payload: ScheduleRequest,
): Promise<ScheduleResponse> {
  return request<ScheduleResponse>("/api/schedule", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
