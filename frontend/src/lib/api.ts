/**
 * API client for DART0s backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FetchOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API ${res.status}: ${errorBody}`);
  }

  return res.json();
}

// ─── Auth ──────────────────────────────────────────────────────

export interface UserResponse {
  id: string;
  email: string;
  plan: string;
  api_key?: string;
  created_at?: string;
}

export interface AuthResponse {
  user: UserResponse;
  access_token: string;
  refresh_token?: string;
}

export const auth = {
  signup: (email: string, password: string) =>
    apiFetch<AuthResponse>("/api/v1/auth/signup", {
      method: "POST",
      body: { email, password },
    }),

  login: (email: string, password: string) =>
    apiFetch<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),

  logout: () =>
    apiFetch<{ message: string }>("/api/v1/auth/logout", { method: "POST" }),

  me: () => apiFetch<UserResponse>("/api/v1/auth/me"),
};

// ─── Disclosures ───────────────────────────────────────────────

export interface KeyMetric {
  label: string;
  value: string;
  status: "POSITIVE" | "NEUTRAL" | "NEGATIVE";
}

export interface DisclosureItem {
  id: string;
  dart_rcept_no: string;
  dart_url: string;
  ticker: string;
  company_name: string;
  title: string;
  published_at: string;
  category: string | null;
  sub_rule_id: string | null;
  deceptive_pattern_detected: boolean | null;
  momentum_authenticity: string | null;
  llm_summary: string | null;
  key_metrics: KeyMetric[] | null;
  llm_status: string;
  created_at: string | null;
}

export interface DisclosureList {
  data: DisclosureItem[];
  total: number;
  page: number;
  per_page: number;
}

export const disclosures = {
  list: () =>
    apiFetch<DisclosureList>("/api/v1/disclosures/list"),

  history: (params: {
    ticker?: string;
    category?: string;
    page?: number;
    per_page?: number;
  }) => {
    const search = new URLSearchParams();
    if (params.ticker) search.set("ticker", params.ticker);
    if (params.category) search.set("category", params.category);
    search.set("page", String(params.page || 1));
    search.set("per_page", String(params.per_page || 20));
    return apiFetch<DisclosureList>(`/api/v1/disclosures/history?${search}`);
  },
};
