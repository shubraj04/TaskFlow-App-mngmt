/** Thin fetch wrapper: bearer auth, one transparent token refresh, typed errors. */
const BASE = "/api";
const ACCESS_KEY = "taskflow.access";
const REFRESH_KEY = "taskflow.refresh";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: Record<string, unknown>,
  ) {
    super(ApiError.describe(status, body));
  }

  /** Field-level messages, e.g. { title: "Title cannot be blank." } */
  get fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const [key, value] of Object.entries(this.body)) {
      out[key] = Array.isArray(value) ? value.join(" ") : String(value);
    }
    return out;
  }

  private static describe(status: number, body: Record<string, unknown>): string {
    if (status === 429) return "Too many requests. Please wait a moment and try again.";
    if (typeof body.detail === "string") return body.detail;
    const first = Object.values(body)[0];
    if (first !== undefined) return Array.isArray(first) ? String(first[0]) : String(first);
    return `Request failed (${status})`;
  }
}

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler = () => {};
export const setUnauthorizedHandler = (fn: UnauthorizedHandler) => {
  onUnauthorized = fn;
};

let refreshing: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  // share one in-flight refresh between concurrent requests
  refreshing ??= fetch(`${BASE}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  })
    .then(async (res) => {
      if (!res.ok) return false;
      tokens.set((await res.json()).access);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  auth?: boolean;
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, auth = true } = opts;

  const send = () =>
    fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(auth && tokens.access ? { Authorization: `Bearer ${tokens.access}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let res = await send();
  if (res.status === 401 && auth && (await refreshAccessToken())) {
    res = await send();
  }
  if (res.status === 401 && auth) onUnauthorized();

  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}
