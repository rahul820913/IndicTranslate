import { useEffect, useState } from "react";
import { api, getToken, setToken, HistoryItem, Lang, Result } from "./api";

const MAX_CHARS = 2000;

export default function App() {
  const [langs, setLangs] = useState<Lang[]>([]);
  const [src, setSrc] = useState("eng_Latn");
  const [tgt, setTgt] = useState("hin_Deva");
  const [text, setText] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [signedIn, setSignedIn] = useState(!!getToken());
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const nameOf = (code: string) => langs.find((l) => l.code === code)?.name ?? code;

  useEffect(() => {
    api.languages().then(setLangs).catch(() => setError("Can't reach the server. Is the API running?"));
  }, []);

  const loadHistory = () =>
    api.history().then((h) => setHistory(h.items)).catch(() => {
      setToken(null);
      setSignedIn(false);
    });

  useEffect(() => {
    if (signedIn) loadHistory();
    else setHistory([]);
  }, [signedIn]);

  // The model only translates to or from English, so keep one side English.
  const changeSrc = (v: string) => {
    setSrc(v);
    if (v !== "eng_Latn" && tgt !== "eng_Latn") setTgt("eng_Latn");
    if (v === tgt) setTgt(src);
  };
  const changeTgt = (v: string) => {
    setTgt(v);
    if (v !== "eng_Latn" && src !== "eng_Latn") setSrc("eng_Latn");
    if (v === src) setSrc(tgt);
  };
  const swap = () => {
    setSrc(tgt);
    setTgt(src);
    if (result) {
      setText(result.translated_text);
      setResult(null);
    }
  };

  async function run() {
    setBusy(true);
    setError("");
    try {
      const r = await api.translate(text, src, tgt, signedIn);
      setResult(r);
      if (signedIn) loadHistory();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!result) return;
    await navigator.clipboard.writeText(result.translated_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
          <h1 className="font-display text-2xl">IndicTranslate</h1>
          {signedIn ? (
            <button className="text-sm underline" onClick={() => { setToken(null); setSignedIn(false); }}>
              Sign out
            </button>
          ) : (
            <span className="text-sm text-ink/60">Sign in below to save your translations</span>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-8">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <LangSelect value={src} onChange={changeSrc} langs={langs} label="Translate from" />
          <button onClick={swap} aria-label="Swap languages" className="rounded border border-line bg-white px-3 py-2 hover:border-ink focus-visible:outline-2 focus-visible:outline-saffron">
            ⇄
          </button>
          <LangSelect value={tgt} onChange={changeTgt} langs={langs} label="Translate to" />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-line bg-white p-4">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
              placeholder={`Type or paste ${nameOf(src)} text`}
              aria-label="Text to translate"
              className="h-56 w-full resize-none text-lg outline-none"
            />
            <div className="flex items-center justify-between pt-2 text-sm text-ink/60">
              <span>{text.length} / {MAX_CHARS}</span>
              <button
                onClick={run}
                disabled={busy || !text.trim()}
                className="rounded bg-ink px-5 py-2 font-medium text-white disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-saffron"
              >
                {busy ? "Translating…" : "Translate"}
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-line bg-white p-4" aria-live="polite">
            <div className="h-56 overflow-auto whitespace-pre-wrap text-lg">
              {result ? result.translated_text : <span className="text-ink/40">Your translation appears here.</span>}
            </div>
            <div className="flex items-center justify-between pt-2 text-sm text-ink/60">
              <span>
                {result && `${result.latency_ms} ms${result.cached ? " · from cache" : ""} · ${result.model_version}`}
              </span>
              {result && (
                <button onClick={copy} className="rounded border border-line px-3 py-1 text-ink hover:border-ink">
                  {copied ? "Copied" : "Copy"}
                </button>
              )}
            </div>
          </div>
        </div>

        {error && <p role="alert" className="mt-4 rounded border border-red-300 bg-red-50 px-4 py-2 text-red-800">{error}</p>}

        <section className="mt-10 grid gap-8 md:grid-cols-[1fr_320px]">
          <div>
            <h2 className="mb-3 font-display text-xl">History</h2>
            {!signedIn ? (
              <p className="text-ink/60">Sign in to keep a history of your translations.</p>
            ) : history.length === 0 ? (
              <p className="text-ink/60">Nothing saved yet. Translate something and it will show up here.</p>
            ) : (
              <ul className="divide-y divide-line rounded-lg border border-line bg-white">
                {history.map((h) => (
                  <li key={h.id} className="flex items-start justify-between gap-4 p-4">
                    <div className="min-w-0">
                      <p className="text-xs text-ink/60">
                        {nameOf(h.source_lang)} → {nameOf(h.target_lang)} · {new Date(h.created_at).toLocaleString()}
                      </p>
                      <p className="truncate">{h.source_text}</p>
                      <p className="truncate font-medium">{h.translated_text}</p>
                    </div>
                    <button
                      onClick={() => api.remove(h.id).then(loadHistory)}
                      className="shrink-0 text-sm text-red-700 underline"
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {!signedIn && <AuthForm onDone={() => setSignedIn(true)} />}
        </section>
      </main>
    </div>
  );
}

function LangSelect(props: { value: string; onChange: (v: string) => void; langs: Lang[]; label: string }) {
  return (
    <label className="flex flex-col text-sm text-ink/70">
      {props.label}
      <select
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        className="mt-1 rounded border border-line bg-white px-3 py-2 text-base text-ink"
      >
        {props.langs.map((l) => (
          <option key={l.code} value={l.code}>{l.name}</option>
        ))}
      </select>
    </label>
  );
}

function AuthForm({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  async function submit() {
    setErr("");
    try {
      const { access_token } = await api.auth(mode, email, password);
      setToken(access_token);
      onDone();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="h-fit rounded-lg border border-line bg-white p-4">
      <h2 className="mb-3 font-display text-xl">{mode === "login" ? "Sign in" : "Create account"}</h2>
      <input className="mb-2 w-full rounded border border-line px-3 py-2" placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input className="mb-3 w-full rounded border border-line px-3 py-2" placeholder="Password (8+ characters)" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {err && <p role="alert" className="mb-2 text-sm text-red-700">{err}</p>}
      <button onClick={submit} className="w-full rounded bg-ink py-2 font-medium text-white">
        {mode === "login" ? "Sign in" : "Create account"}
      </button>
      <button className="mt-3 text-sm underline" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
      </button>
    </div>
  );
}
