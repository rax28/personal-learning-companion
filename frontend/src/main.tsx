// @ts-nocheck
import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:4000";
const apiFetch = (input: any, init: any = {}) =>
  fetch(input, { ...init, credentials: "include" });
type Mode = "education" | "self" | "interview";
type View = "chat" | "map" | "source";
type Msg = { role: "user" | "assistant"; content: string };

const modes = [
  {
    id: "education",
    label: "Learn",
    sub: "understand things without losing the thread",
  },
  {
    id: "self",
    label: "Understand me",
    sub: "notice patterns in how you learn",
  },
  {
    id: "interview",
    label: "Interview",
    sub: "reason through technical questions",
  },
] as const;
const starter = {
  education: "What are you working on?",
  self: "What have you noticed about how you learn?",
  interview: "What do you want to practise?",
};

function Cat({ active }: { active: boolean }) {
  const [i, setI] = useState(0);
  const frames = active
    ? ["/cat/listen.png", "/cat/jump.png"]
    : ["/cat/idle.png", "/cat/sleep.png"];
  useEffect(() => {
    const t = setInterval(
      () => setI((x) => (x + 1) % frames.length),
      active ? 520 : 2200,
    );
    return () => clearInterval(t);
  }, [active]);
  return <img className="cat" src={frames[i]} alt="learning companion" />;
}
function pct(v: number) {
  return Math.round((v || 0) * 100);
}
function inferTopic(text: string) {
  const low = text.toLowerCase();
  const pairs = [
    ["two pointers", "Two Pointers"],
    ["sliding window", "Sliding Window"],
    ["binary search", "Binary Search"],
    ["hashmap", "Hash Maps"],
    ["hash map", "Hash Maps"],
    ["recursion", "Recursion"],
    ["dynamic programming", "Dynamic Programming"],
    ["linked list", "Linked Lists"],
    ["integration", "Integration"],
    ["probability", "Probability"],
    ["statistics", "Statistics"],
    ["democracy", "Democracy"],
    ["history", "History"],
    ["geography", "Geography"],
    ["economics", "Economics"],
    ["graph", "Graphs"],
    ["array", "Arrays"],
    ["java", "Java"],
  ];
  return pairs.find(([k]) => low.includes(k))?.[1];
}

function Login() {
  const [view, setView] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(e: any) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await apiFetch(
        `${API}/auth/${view === "register" ? "register" : "login"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
        },
      );
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Authentication failed");
      window.location.reload();
    } catch (e: any) {
      setError(e.message || "Could not connect to the backend.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <div className="login-mark">◌</div>
        <span className="kicker">personal learning companion</span>
        <h1>
          {view === "login"
            ? "Your learning, tied to you."
            : "Create your learning space."}
        </h1>
        <p>
          {view === "login"
            ? "Sign in to continue to your private conversations, mastery, gaps, sources, and learning graph."
            : "Create an account to save your own learner model and learning history."}
        </p>
        {view === "register" && (
          <label className="auth-field">
            Name
            <input
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              maxLength={100}
            />
          </label>
        )}
        <label className="auth-field">
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>
        <label className="auth-field">
          Password
          <input
            type="password"
            autoComplete={
              view === "login" ? "current-password" : "new-password"
            }
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </label>
        {error && (
          <p className="auth-error" role="alert">
            {error}
          </p>
        )}
        <button className="google-login" type="submit" disabled={busy}>
          {busy
            ? "Please wait…"
            : view === "login"
              ? "Sign in"
              : "Create account"}
        </button>
        <small>
          {view === "login"
            ? "Don't have an account?"
            : "Already have an account?"}{" "}
          <button
            className="auth-switch"
            type="button"
            onClick={() => {
              setView(view === "login" ? "register" : "login");
              setError("");
            }}
          >
            {view === "login" ? "Create one" : "Sign in"}
          </button>
        </small>
        <small>
          Google is only used if you separately choose to connect Google
          Classroom.
        </small>
      </form>
    </div>
  );
}

function App() {
  const [auth, setAuth] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);
  useEffect(() => {
    apiFetch(`${API}/auth/me`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setAuth)
      .catch(() => setAuth(null))
      .finally(() => setAuthLoading(false));
  }, []);
  if (authLoading)
    return (
      <div className="login-screen">
        <div className="login-card">
          <h1>Loading companion…</h1>
        </div>
      </div>
    );
  return auth?.authenticated ? <AuthenticatedApp /> : <Login />;
}

function AuthenticatedApp() {
  const [mode, setMode] = useState<Mode>("education");
  const [view, setView] = useState<View>("chat");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: starter.education },
  ]);
  const [conversationIds, setConversationIds] = useState<any>({
    education: "plc-education",
    self: "plc-self",
    interview: "plc-interview",
  });
  const [threads, setThreads] = useState<any>({
    education: {},
    self: {},
    interview: {},
  });
  const [graph, setGraph] = useState<any>({
    concepts: [],
    connections: [],
    evidence: [],
    conversationStates: [],
  });
  const [state, setState] = useState<any>({});
  const [gaps, setGaps] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [offline, setOffline] = useState(!navigator.onLine);
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("plc-source-ids") || "[]");
    } catch {
      return [];
    }
  });
  const [sourceText, setSourceText] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceBusy, setSourceBusy] = useState(false);
  const [sourceStatus, setSourceStatus] = useState(
    "Add a PDF, text file, URL, or Google Classroom material.",
  );
  const [compression, setCompression] = useState<any>(null);
  const [classroom, setClassroom] = useState<any>({
    connected: false,
    configured: false,
    courses: [],
    materials: [],
    courseId: "",
  });
  const current = modes.find((x) => x.id === mode)!;

  useEffect(() => {
    try {
      const x = JSON.parse(
        localStorage.getItem("plc-conversation-ids") || "{}",
      );
      setConversationIds((v) => ({ ...v, ...x }));
      const t = JSON.parse(localStorage.getItem("plc-topic-threads") || "{}");
      setThreads((v) => ({ ...v, ...t }));
    } catch {}
    refresh();
    refreshSources();
    refreshClassroom();
    const on = () => setOffline(false),
      off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  useEffect(() => {
    void loadConversation(mode);
  }, [mode]);
  useEffect(() => {
    localStorage.setItem("plc-source-ids", JSON.stringify(selectedSources));
  }, [selectedSources]);
  async function loadConversation(m: Mode) {
    try {
      const id = conversationIds[m];
      const r = await apiFetch(`${API}/conversation/${encodeURIComponent(id)}`);
      if (!r.ok) return;
      const d = await r.json();
      setMessages(
        d.length
          ? d.map((x: any) => ({ role: x.role, content: x.content }))
          : [{ role: "assistant", content: starter[m] }],
      );
    } catch {
      setMessages([{ role: "assistant", content: starter[m] }]);
    }
  }
  async function refresh() {
    try {
      const [a, b] = await Promise.all([
        apiFetch(`${API}/learning/graph`),
        apiFetch(`${API}/learning/gaps`),
      ]);
      if (a.ok) setGraph(await a.json());
      if (b.ok) setGaps((await b.json()).gaps || []);
    } catch {}
  }
  async function refreshSources() {
    try {
      const r = await apiFetch(`${API}/source/cache`);
      if (r.ok) setSources((await r.json()).sources || []);
    } catch {}
  }
  async function refreshClassroom() {
    try {
      const r = await apiFetch(`${API}/integrations/google/classroom/status`);
      if (r.ok) {
        const d = await r.json();
        setClassroom((x: any) => ({ ...x, ...d }));
      }
    } catch {}
  }
  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    if (offline) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "The local companion is offline." },
      ]);
      return;
    }
    setLoading(true);
    try {
      const topic = inferTopic(text);
      const key = topic?.toLowerCase();
      const id = (key && threads[mode]?.[key]) || conversationIds[mode];
      const r = await apiFetch(`${API}/conversation/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          mode,
          conversationId: id,
          topicHint: topic,
          sourceId: selectedSources[0],
          sourceIds: selectedSources,
        }),
      });
      const raw = await r.text();
      if (!r.ok) throw new Error(raw);
      const d = JSON.parse(raw);
      if (d.conversationId) {
        const next = { ...conversationIds, [mode]: d.conversationId };
        setConversationIds(next);
        localStorage.setItem("plc-conversation-ids", JSON.stringify(next));
        if (d.topic) {
          const nt = {
            ...threads,
            [mode]: {
              ...(threads[mode] || {}),
              [d.topic.toLowerCase()]: d.conversationId,
            },
          };
          setThreads(nt);
          localStorage.setItem("plc-topic-threads", JSON.stringify(nt));
        }
      }
      setMessages((m) => [...m, { role: "assistant", content: d.response }]);
      setState(d.learnerState?.current || d.learningState || {});
      await refresh();
    } catch (e) {
      console.error(e);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "I can’t reach the local companion. Check the 4000 and 8000 services.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }
  async function uploadFile(file: File) {
    setSourceBusy(true);
    setSourceStatus(`Reading ${file.name}…`);
    try {
      const buf = await file.arrayBuffer();
      let binary = "";
      const bytes = new Uint8Array(buf);
      const chunk = 0x8000;
      for (let i = 0; i < bytes.length; i += chunk)
        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
      const b64 = btoa(binary);
      const r = await apiFetch(`${API}/source/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          contentBase64: b64,
          mimeType: file.type,
          sourceUrl: `file://${file.name}`,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.error || "Upload failed");
      setSources((x) => [
        d,
        ...x.filter((s: any) => s.source_id !== d.source_id),
      ]);
      setSelectedSources((x) => [
        d.source_id,
        ...x.filter((y) => y !== d.source_id),
      ]);
      setSourceName(file.name);
      setSourceStatus(
        `Cached ${file.name} · ${d.chunks} chunks. It stays in the persistent source library.`,
      );
      setCompression(d);
    } catch (e) {
      setSourceStatus(`Couldn’t add file: ${e}`);
    } finally {
      setSourceBusy(false);
    }
  }
  async function cacheText() {
    if (!sourceText.trim() || sourceBusy) return;
    setSourceBusy(true);
    setSourceStatus("Building the persistent lossless source cache…");
    try {
      const r = await apiFetch(`${API}/source/cache`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: sourceText,
          sourceUrl: sourceUrl.trim() || `manual://${sourceName || "notes"}`,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.error);
      setSources((x) => [
        d,
        ...x.filter((s: any) => s.source_id !== d.source_id),
      ]);
      setSelectedSources((x) => [
        d.source_id,
        ...x.filter((y) => y !== d.source_id),
      ]);
      setCompression(d);
      setSourceStatus(
        `Cached ${d.label} · ${d.chunks} chunks. It remains available when another source is added.`,
      );
    } catch (e) {
      setSourceStatus(`Cache failed: ${e}`);
    } finally {
      setSourceBusy(false);
    }
  }
  async function loadUrl() {
    if (!sourceUrl.trim() || sourceBusy) return;
    setSourceBusy(true);
    setSourceStatus("Loading source…");
    try {
      const r = await apiFetch(`${API}/compression/load-source`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sourceUrl: sourceUrl.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Load failed");
      setSourceText(d.text || "");
      setSourceName(sourceUrl);
      setSourceStatus(
        `Loaded ${d.kind || "source"} · ${(d.text || "").length.toLocaleString()} characters. Click cache to persist it.`,
      );
    } catch (e) {
      setSourceStatus(`Couldn’t load source: ${e}`);
    } finally {
      setSourceBusy(false);
    }
  }
  async function loadClassroomCourses() {
    try {
      const r = await apiFetch(`${API}/integrations/google/classroom/courses`);
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Not connected");
      setClassroom((x) => ({ ...x, courses: d.courses || [] }));
    } catch (e) {
      setSourceStatus(String(e));
    }
  }
  async function loadMaterials(courseId: string) {
    setClassroom((x) => ({ ...x, courseId, materials: [] }));
    try {
      const r = await apiFetch(
        `${API}/integrations/google/classroom/courses/${encodeURIComponent(courseId)}/materials`,
      );
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Could not load materials");
      setClassroom((x) => ({ ...x, materials: d.materials || [] }));
    } catch (e) {
      setSourceStatus(String(e));
    }
  }
  async function importClassroom(item: any) {
    setSourceBusy(true);
    setSourceStatus(`Importing ${item.title} from Classroom…`);
    try {
      const r = await apiFetch(`${API}/integrations/google/classroom/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fileId: item.id }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || d.detail || "Import failed");
      setSources((x) => [
        d,
        ...x.filter((s: any) => s.source_id !== d.source_id),
      ]);
      setSelectedSources((x) => [
        d.source_id,
        ...x.filter((y) => y !== d.source_id),
      ]);
      setSourceStatus(`Imported ${item.title}. It is now a persistent source.`);
    } catch (e) {
      setSourceStatus(String(e));
    } finally {
      setSourceBusy(false);
    }
  }
  function toggleSource(id: string) {
    setSelectedSources((x) =>
      x.includes(id) ? x.filter((y) => y !== id) : [...x, id],
    );
  }
  const concepts = useMemo(
    () => graph.concepts.filter((x: any) => x.mode === mode),
    [graph, mode],
  );
  const modeGaps = gaps.filter((x) => x.mode === mode).slice(0, 7);
  const recent = graph.evidence.filter((x: any) => x.mode === mode).slice(0, 7);
  const active = (graph.conversationStates || []).find(
    (x: any) => x.mode === mode && x.status === "active",
  );

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={() => setView("chat")}>
          <span className="brand-mark">◌</span>
          <span>
            <b>Companion</b>
            <small>learner-aware · source-grounded · local</small>
          </span>
        </button>
        <div className="top-center">
          {modes.map((m) => (
            <button
              key={m.id}
              className={mode === m.id ? "mode-active" : ""}
              onClick={() => {
                setMode(m.id);
                setView("chat");
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
        <div className="top-right">
          <span className={offline ? "status off" : "status"}>
            <i /> {offline ? "offline" : "local"}
          </span>
          <button onClick={() => setView("map")}>Learning map</button>
          <button onClick={() => setView("source")}>Sources</button>
          <button
            onClick={async () => {
              await apiFetch(`${API}/auth/logout`, { method: "POST" });
              window.location.reload();
            }}
          >
            Log out
          </button>
        </div>
      </header>
      {view === "chat" && (
        <section className="chat-view">
          <div className="companion-rail">
            <div className="cat-card">
              <Cat active={loading} />
              <span className="cat-caption">your companion</span>
            </div>
            <div className="rail-note">
              <span>current</span>
              <b>{state.topic || active?.topic || "No topic yet"}</b>
              {(state.gap || active?.current_gap) && (
                <small>gap · {state.gap || active.current_gap}</small>
              )}
            </div>
          </div>
          <section className="chat-card">
            <div className="chat-head">
              <div>
                <span className="kicker">{current.label}</span>
                <h1>{state.topic || "Talk it through"}</h1>
                <p>{current.sub}</p>
              </div>
              <span className="state-pill">
                {selectedSources.length} source
                {selectedSources.length === 1 ? "" : "s"} active
              </span>
            </div>
            <div className="messages">
              {messages.map((m, i) => (
                <div className={`message ${m.role}`} key={i}>
                  <span className="message-who">
                    {m.role === "user" ? "you" : "companion"}
                  </span>
                  <div className="message-text">{m.content}</div>
                </div>
              ))}
              {loading && (
                <div className="message assistant">
                  <span className="message-who">companion</span>
                  <div className="typing">
                    <i />
                    <i />
                    <i />
                  </div>
                </div>
              )}
            </div>
            <div className="composer">
              <input
                autoFocus
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Ask it naturally…"
                disabled={loading}
              />
              <button onClick={send} disabled={loading || !input.trim()}>
                Send
              </button>
            </div>
            <div className="chat-footer">
              <span>
                {selectedSources.length
                  ? `${selectedSources.length} persistent source${selectedSources.length === 1 ? "" : "s"}`
                  : "no source attached"}
              </span>
              <span>
                {state.gap ? "following a gap" : "following the conversation"}
              </span>
            </div>
          </section>
        </section>
      )}
      {view === "map" && (
        <section className="page">
          <div className="page-head">
            <div>
              <span className="kicker">learner model</span>
              <h1>What the companion knows about your learning</h1>
              <p>
                Messages stay as evidence. Concepts, gaps and mastery become
                durable state.
              </p>
            </div>
            <div className="headline-stats">
              <b>{concepts.length}</b>
              <span>concepts</span>
              <b>{recent.length}</b>
              <span>recent signals</span>
            </div>
          </div>
          <div className="state-panel">
            <div>
              <span>topic</span>
              <b>{active?.topic || state.topic || "—"}</b>
            </div>
            <div>
              <span>stage</span>
              <b>{active?.stage || state.stage || "—"}</b>
            </div>
            <div>
              <span>gap</span>
              <b>{active?.current_gap || state.gap || "—"}</b>
            </div>
            <div>
              <span>next</span>
              <b>
                {active?.waiting_for_answer ? "your answer" : "conversation"}
              </b>
            </div>
          </div>
          <div className="map-grid">
            <section className="panel">
              <div className="panel-head">
                <div>
                  <span className="kicker">mastery</span>
                  <h2>Concept state</h2>
                </div>
                <span>{concepts.length} nodes</span>
              </div>
              {concepts.length ? (
                concepts
                  .slice()
                  .sort((a: any, b: any) => a.understanding - b.understanding)
                  .map((c: any) => (
                    <div className="concept-row" key={c.id}>
                      <div>
                        <b>{c.name}</b>
                        <small>{c.topic}</small>
                      </div>
                      <div className="bar">
                        <i style={{ width: `${pct(c.understanding)}%` }} />
                      </div>
                      <strong>{pct(c.understanding)}%</strong>
                    </div>
                  ))
              ) : (
                <p className="empty">
                  Start a learning exchange and the model will build state from
                  evidence.
                </p>
              )}
            </section>
            <section className="panel dark">
              <div className="panel-head">
                <div>
                  <span className="kicker">gap detector</span>
                  <h2>Where to work next</h2>
                </div>
              </div>
              {modeGaps.length ? (
                modeGaps.map((g) => (
                  <div className="gap-item" key={g.id}>
                    <b>{g.name}</b>
                    <span>{g.topic}</span>
                    <strong>{pct(g.understanding)}%</strong>
                  </div>
                ))
              ) : (
                <p className="empty">
                  No evidence-backed gap for this mode yet.
                </p>
              )}
            </section>
          </div>
          <section className="panel">
            <div className="panel-head">
              <div>
                <span className="kicker">evidence</span>
                <h2>Recent learning signals</h2>
              </div>
              <span>not raw chat nodes</span>
            </div>
            {recent.length ? (
              recent.map((e: any) => (
                <div className="evidence-row" key={e.id}>
                  <span>{e.type}</span>
                  <p>{e.message}</p>
                  <small>{e.concept}</small>
                </div>
              ))
            ) : (
              <p className="empty">Nothing recorded yet.</p>
            )}
          </section>
          <div className="architecture">
            <div>
              <span>01 · source side</span>
              <b>
                ingest → chunk → predictability → lossless cache → relevant
                retrieval
              </b>
            </div>
            <div>
              <span>02 · learner side</span>
              <b>
                conversation → evidence → prerequisite gap → teaching →
                assessment → mastery → graph
              </b>
            </div>
          </div>
        </section>
      )}
      {view === "source" && (
        <section className="page source-page">
          <div className="page-head">
            <div>
              <span className="kicker">source library</span>
              <h1>Bring your learning material in once. Keep it.</h1>
              <p>
                PDFs, text files, URLs and Classroom materials become persistent
                source records. Adding a new source does not delete the old one.
              </p>
            </div>
            <span className="source-live">{sources.length} CACHED</span>
          </div>
          <div className="source-grid">
            <section className="panel source-input">
              <label>PDF / text file</label>
              <input
                className="file-input"
                type="file"
                accept=".pdf,.txt,text/plain,application/pdf"
                disabled={sourceBusy}
                onChange={(e) =>
                  e.target.files?.[0] && uploadFile(e.target.files[0])
                }
              />
              <label>source URL</label>
              <div className="url-row">
                <input
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  placeholder="https://…"
                />
                <button onClick={loadUrl} disabled={sourceBusy}>
                  Load
                </button>
              </div>
              <label>notes / text</label>
              <textarea
                value={sourceText}
                onChange={(e) => setSourceText(e.target.value)}
                placeholder="Paste notes or course material…"
              />
              <div className="actions">
                <button
                  onClick={cacheText}
                  disabled={sourceBusy || !sourceText.trim()}
                >
                  {sourceBusy ? "Working…" : "Cache text"}
                </button>
                <button
                  className="secondary"
                  onClick={() => {
                    setSourceText("");
                    setSourceUrl("");
                    setCompression(null);
                  }}
                >
                  Clear
                </button>
              </div>
              <p className="status-line">{sourceStatus}</p>
            </section>
            <section className="panel result">
              <div className="panel-head">
                <div>
                  <span className="kicker">persistent sources</span>
                  <h2>Source library</h2>
                </div>
                <span>{selectedSources.length} active</span>
              </div>
              {sources.length ? (
                sources.map((s: any) => (
                  <div className="source-row" key={s.source_id}>
                    <label className="source-check">
                      <input
                        type="checkbox"
                        checked={selectedSources.includes(s.source_id)}
                        onChange={() => toggleSource(s.source_id)}
                      />
                      <span>
                        <b>{s.label}</b>
                        <small>
                          {s.chunks} chunks ·{" "}
                          {Math.round((s.original_bytes || 0) / 1024)} KB ·{" "}
                          {s.source_url || "local file"}
                        </small>
                      </span>
                    </label>
                  </div>
                ))
              ) : (
                <div className="empty steps">
                  <p>
                    <b>1</b> Add a PDF or text file.
                  </p>
                  <p>
                    <b>2</b> Cache it.
                  </p>
                  <p>
                    <b>3</b> Add another source — the first remains here.
                  </p>
                </div>
              )}
              {compression && (
                <div className="source-proof">
                  <b>Persistent retrieval</b>
                  <p>
                    selected sources → relevant chunks → decompression →
                    companion context
                  </p>
                </div>
              )}
            </section>
          </div>
          <section className="panel classroom">
            <div className="panel-head">
              <div>
                <span className="kicker">google classroom</span>
                <h2>Bring course PDFs in directly</h2>
              </div>
              <span>{classroom.connected ? "CONNECTED" : "OPTIONAL"}</span>
            </div>
            <p className="classroom-copy">
              Connect Google Classroom, choose a course, then import an
              accessible PDF/text attachment. Imported files join the same
              persistent source library.
            </p>
            <div className="actions">
              <button
                onClick={() =>
                  (window.location.href = `${API}/integrations/google/classroom/start`)
                }
                disabled={!classroom.configured}
              >
                Connect Google Classroom
              </button>
              <button
                className="secondary"
                onClick={loadClassroomCourses}
                disabled={!classroom.connected}
              >
                Refresh courses
              </button>
            </div>
            {!classroom.configured && (
              <p className="status-line">
                Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and
                GOOGLE_REDIRECT_URI in the backend environment to enable this.
              </p>
            )}
            {classroom.connected && (
              <div className="classroom-grid">
                <select
                  value={classroom.courseId}
                  onChange={(e) => loadMaterials(e.target.value)}
                >
                  <option value="">Choose a course…</option>
                  {classroom.courses.map((c: any) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <div className="class-materials">
                  {classroom.materials.map((m: any) => (
                    <div className="material-row" key={m.id}>
                      <span>
                        <b>{m.title}</b>
                        <small>{m.mimeType || "file"}</small>
                      </span>
                      <button
                        onClick={() => importClassroom(m)}
                        disabled={sourceBusy}
                      >
                        Import
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
          <div className="architecture wide">
            <div>
              <span>source knowledge</span>
              <b>persistent and independently addressable</b>
            </div>
            <div>
              <span>learner knowledge</span>
              <b>built from interaction evidence, not source presence</b>
            </div>
            <div>
              <span>multiple sources</span>
              <b>adding Source B leaves Source A retrievable</b>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
