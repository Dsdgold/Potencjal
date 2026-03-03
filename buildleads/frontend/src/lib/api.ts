function getApiUrl(): string {
  if (typeof window === "undefined") return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
  // In browser: use /api proxy (Next.js rewrites) to avoid CORS/Codespace port issues
  return "";
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("bl_token");
}

export function setTokens(tokens: TokenPair) {
  localStorage.setItem("bl_token", tokens.access_token);
  localStorage.setItem("bl_refresh", tokens.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("bl_token");
  localStorage.removeItem("bl_refresh");
}

export async function apiFetch(path: string, opts: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((opts.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${getApiUrl()}${path}`, { ...opts, headers });

  if (res.status === 401 && token) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getToken()}`;
      return fetch(`${getApiUrl()}${path}`, { ...opts, headers });
    }
    clearTokens();
    window.location.href = "/login";
  }

  return res;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem("bl_refresh");
  if (!refresh) return false;

  const res = await fetch(`${getApiUrl()}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!res.ok) return false;

  const data = await res.json();
  setTokens(data);
  return true;
}

export async function login(email: string, password: string) {
  const res = await fetch(`${getApiUrl()}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  setTokens(data);
  return data;
}

export async function getMe() {
  const res = await apiFetch("/api/v1/auth/me");
  if (!res.ok) return null;
  return res.json();
}
