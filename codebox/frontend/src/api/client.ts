import type {
  AIRequest,
  AIResponse,
  ExecutionAccepted,
  ExecutionResult,
  LanguagesResponse,
  ProblemDetail,
  ProblemSummary,
  SubmissionDetail,
  SubmissionList,
  TokenResponse,
  User,
} from "./types";

const BASE = "/api/v1";
const TOKEN_KEY = "codebox.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    /** Structured error detail when the server sends an object instead of a message */
    public data?: Record<string, unknown>,
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: session-only login */
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

function describe(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) return String((detail as { message: unknown }).message);
  if (Array.isArray(detail)) {
    // FastAPI validation errors
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => {
        const field = d.loc?.slice(1).join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return "Request failed";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(BASE + path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the backend running?");
  }
  if (response.status === 401 && token) onUnauthorized();
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    let data: Record<string, unknown> | undefined;
    try {
      const detail = (await response.json()).detail;
      message = describe(detail);
      if (detail && typeof detail === "object" && !Array.isArray(detail)) data = detail;
    } catch {
      /* non-JSON error body (e.g. proxy error page) */
      if (response.status >= 502) message = "The server is unavailable. Please try again shortly.";
    }
    throw new ApiError(response.status, message, data);
  }
  return (await response.json()) as T;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  register: (username: string, email: string, password: string) =>
    post<TokenResponse>("/auth/register", { username, email, password }),
  login: (username: string, password: string) =>
    post<TokenResponse>("/auth/login", { username, password }),
  me: () => request<User>("/auth/me"),

  languages: () => request<LanguagesResponse>("/languages"),
  problems: () => request<ProblemSummary[]>("/problems"),
  problem: (slug: string) => request<ProblemDetail>(`/problems/${encodeURIComponent(slug)}`),

  execute: (language: string, source_code: string, stdin: string, problem_id?: number) =>
    post<ExecutionAccepted>("/execute", { language, source_code, stdin, problem_id }),
  submit: (problem_id: number, language: string, source_code: string) =>
    post<ExecutionAccepted>("/submissions", { problem_id, language, source_code }),
  execution: (id: string) => request<ExecutionResult>(`/executions/${encodeURIComponent(id)}`),

  submissions: (params: { page?: number; page_size?: number; kind?: string; problem_id?: number }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && query.set(k, String(v)));
    return request<SubmissionList>(`/submissions?${query}`);
  },
  submission: (id: number) => request<SubmissionDetail>(`/submissions/${id}`),

  aiStatus: () => request<{ enabled: boolean; model: string | null }>("/ai/status"),
  assist: (body: AIRequest) => post<AIResponse>("/ai/assist", body),
};
