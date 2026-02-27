const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface FetchOptions extends RequestInit {
  token?: string;
}

export async function apiFetch<T = any>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { token, ...init } = opts;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API Error: ${res.status}`);
  }

  return res.json();
}

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    apiFetch("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (data: { email: string; password: string; full_name: string; org_name: string }) =>
    apiFetch("/api/auth/register", { method: "POST", body: JSON.stringify(data) }),
  me: (token: string) =>
    apiFetch("/api/auth/me", { token }),
  refresh: (refresh_token: string) =>
    apiFetch("/api/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token }) }),
};

// Companies
export const companiesApi = {
  lookup: (nip: string, token: string) =>
    apiFetch("/api/companies/lookup", { method: "POST", body: JSON.stringify({ nip, purpose: "credit_assessment" }), token }),
  search: (q: string, token: string) =>
    apiFetch(`/api/companies/search?q=${encodeURIComponent(q)}`, { token }),
  get: (nip: string, token: string) =>
    apiFetch(`/api/companies/${nip}`, { token }),
  getNotes: (nip: string, token: string) =>
    apiFetch(`/api/companies/${nip}/notes`, { token }),
  addNote: (nip: string, text: string, tags: string[], token: string) =>
    apiFetch(`/api/companies/${nip}/notes`, { method: "POST", body: JSON.stringify({ text, tags }), token }),
  getTasks: (nip: string, token: string) =>
    apiFetch(`/api/companies/${nip}/tasks`, { token }),
  addTask: (nip: string, data: any, token: string) =>
    apiFetch(`/api/companies/${nip}/tasks`, { method: "POST", body: JSON.stringify(data), token }),
  watch: (nip: string, token: string) =>
    apiFetch(`/api/companies/${nip}/watch`, { method: "POST", token }),
  unwatch: (nip: string, token: string) =>
    apiFetch(`/api/companies/${nip}/watch`, { method: "DELETE", token }),
  watchlist: (token: string) =>
    apiFetch("/api/companies/watchlist/all", { token }),
};

// Subscriptions
export const subscriptionsApi = {
  plans: () => apiFetch("/api/subscriptions/plans"),
  checkout: (planCode: string, token: string) =>
    apiFetch(`/api/subscriptions/checkout?plan_code=${planCode}`, { method: "POST", token }),
  portal: (token: string) =>
    apiFetch("/api/subscriptions/portal", { method: "POST", token }),
};

// Admin
export const adminApi = {
  orgs: (token: string) => apiFetch("/api/admin/orgs", { token }),
  users: (token: string) => apiFetch("/api/admin/users", { token }),
  plans: (token: string) => apiFetch("/api/admin/plans", { token }),
  audit: (token: string) => apiFetch("/api/admin/audit", { token }),
  health: (token: string) => apiFetch("/api/admin/system/health", { token }),
  updateOrg: (orgId: string, data: any, token: string) =>
    apiFetch(`/api/admin/orgs/${orgId}`, { method: "PATCH", body: JSON.stringify(data), token }),
  updateUser: (userId: string, data: any, token: string) =>
    apiFetch(`/api/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(data), token }),
};
