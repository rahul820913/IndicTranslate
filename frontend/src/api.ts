export type Lang = { code: string; name: string };
export type Result = {
  id: string | null;
  translated_text: string;
  model_version: string;
  latency_ms: number;
  cached: boolean;
};
export type HistoryItem = {
  id: string;
  source_lang: string;
  target_lang: string;
  source_text: string;
  translated_text: string;
  created_at: string;
};

const BASE = "/api/v1";
let token: string | null = localStorage.getItem("token");

export const getToken = () => token;
export function setToken(t: string | null) {
  token = t;
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Check your input and try again.");
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  languages: () => req<Lang[]>("/languages"),
  translate: (text: string, source_language: string, target_language: string, save: boolean) =>
    req<Result>("/translations", {
      method: "POST",
      body: JSON.stringify({ text, source_language, target_language, save }),
    }),
  history: () => req<{ items: HistoryItem[]; total: number }>("/translations?limit=30"),
  remove: (id: string) => req<void>(`/translations/${id}`, { method: "DELETE" }),
  auth: (mode: "login" | "register", email: string, password: string) =>
    req<{ access_token: string }>(`/auth/${mode}`, { method: "POST", body: JSON.stringify({ email, password }) }),
};
