/**
 * API client for DartPR backend.
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

  // Auto-attach auth token from localStorage if available
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("supabase_access_token");
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    }
  }

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
  sub_type: string | null;
  sub_rule_id: string | null;
  dvi_score: number | null;
  impact_level: string | null;
  risk_flag: string | null;
  is_feed_visible: boolean | null;
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
  /** Live feed — public (3-min delay) unless auth token provided */
  live: (authToken?: string) => {
    const headers: Record<string, string> = {};
    if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
    return apiFetch<DisclosureList>("/api/v1/disclosures/live", { headers });
  },

  /** History with full filter support */
  history: (params: {
    ticker?: string;
    company_name?: string;
    category?: string;
    score_min?: number;
    score_max?: number;
    date_from?: string;
    date_to?: string;
    risk_flag?: string;
    page?: number;
    per_page?: number;
  }) => {
    const search = new URLSearchParams();
    const str = (v: unknown) => String(v);
    if (params.ticker) search.set("ticker", params.ticker);
    if (params.company_name) search.set("company_name", params.company_name);
    if (params.category) search.set("category", params.category);
    if (params.score_min !== undefined) search.set("score_min", str(params.score_min));
    if (params.score_max !== undefined) search.set("score_max", str(params.score_max));
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    if (params.risk_flag) search.set("risk_flag", params.risk_flag);
    search.set("page", String(params.page || 1));
    search.set("per_page", String(params.per_page || 20));
    return apiFetch<DisclosureList>(`/api/v1/disclosures/history?${search}`);
  },

  /** Trigger a manual poll */
  poll: () =>
    apiFetch<{ message: string }>("/api/v1/disclosures/poll", { method: "POST" }),

  /** Re-classify all existing disclosures */
  reclassify: () =>
    apiFetch<{ message: string }>("/api/v1/disclosures/reclassify", { method: "POST" }),

  /** Get stats */
  stats: () =>
    apiFetch<{ total_disclosures: number; feed_visible: number; by_category: Record<string, number> }>(
      "/api/v1/disclosures/stats"
    ),
};

export interface Notice {
  id: string;
  title: string;
  content: string;
  author_email: string;
  pinned: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface NoticeList {
  data: Notice[];
  total: number;
}

export const notices_api = {
  list: (page = 1, perPage = 20) =>
    apiFetch<NoticeList>(`/api/v1/notices?page=${page}&per_page=${perPage}`),

  get: (id: string) =>
    apiFetch<Notice>(`/api/v1/notices/${id}`),

  create: (title: string, content: string, pinned = false) =>
    apiFetch<Notice>("/api/v1/notices", {
      method: "POST",
      body: { title, content, pinned },
    }),

  update: (id: string, data: { title?: string; content?: string; pinned?: boolean }) =>
    apiFetch<Notice>(`/api/v1/notices/${id}`, {
      method: "PUT",
      body: data,
    }),

  delete: (id: string) =>
    apiFetch<{ message: string }>(`/api/v1/notices/${id}`, {
      method: "DELETE",
    }),
};
