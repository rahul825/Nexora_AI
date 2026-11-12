import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";   // tables, strikethrough, task lists
import { api } from "./api.js";

const SOURCES = {
  document: { label: "Document", hint: "Answers from the GK PDF document" },
  database: { label: "Database", hint: "Answers from the MySQL database" },
};

const SUGGESTIONS = {
  document: ["Which is the largest state in India?", "In which year did Delhi become the capital?"],
  database: ["How many users are there?", "Which employees took leave in September 2024?"],
};

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);      // null = new, unsaved chat
  const [messages, setMessages] = useState([]);
  const [source, setSource] = useState("document");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Load the session list once, and reopen the last chat
  useEffect(() => {
    api.listSessions()
      .then((list) => {
        setSessions(list);
        const last = localStorage.getItem("activeSession");
        if (last && list.some((s) => s.id === last)) openSession(last);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    try {
      activeId ? localStorage.setItem("activeSession", activeId) : localStorage.removeItem("activeSession");
    } catch { /* storage blocked: just don't remember */ }
  }, [activeId]);

  async function openSession(id) {
    setError("");
    setSidebarOpen(false);
    try {
      const s = await api.getSession(id);
      setActiveId(s.id);
      setSource(s.source);
      setMessages(s.messages);
    } catch (e) {
      setError(e.message);
    }
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setError("");
    setSidebarOpen(false);
    inputRef.current?.focus();
  }

  async function changeSource(next) {
    setSource(next);
    if (activeId) {
      const updated = await api.updateSession(activeId, { source: next }).catch(() => null);
      if (updated) setSessions((list) => list.map((s) => (s.id === activeId ? { ...s, source: next } : s)));
    }
  }

  async function send(text) {
    const question = (text ?? input).trim();
    if (!question || sending) return;
    setError("");
    setInput("");
    setSending(true);
    // Show the question right away; the server returns the saved copy
    const tempId = `temp-${Date.now()}`;
    setMessages((m) => [...m, { id: tempId, role: "user", content: question }]);

    try {
      let id = activeId;
      if (!id) {   // a session is only created when the first question is sent
        const created = await api.createSession(source);
        id = created.id;
        setActiveId(id);
      }
      const res = await api.ask(id, question, source);
      setMessages((m) => [...m.filter((x) => x.id !== tempId), ...res.messages]);
      setSessions((list) => [res.session, ...list.filter((s) => s.id !== res.session.id)]);
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== tempId));
      setInput(question);
      setError(e.message);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  async function saveTitle(id) {
    const title = editTitle.trim();
    setEditingId(null);
    if (!title) return;
    try {
      await api.updateSession(id, { title });
      setSessions((list) => list.map((s) => (s.id === id ? { ...s, title } : s)));
    } catch (e) {
      setError(e.message);
    }
  }

  async function removeSession(id) {
    if (!window.confirm("Delete this chat and its history?")) return;
    try {
      await api.deleteSession(id);
      setSessions((list) => list.filter((s) => s.id !== id));
      if (id === activeId) newChat();
    } catch (e) {
      setError(e.message);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  const activeTitle = sessions.find((s) => s.id === activeId)?.title || "New chat";

  return (
    <div className="app">
      {sidebarOpen && <div className="backdrop" onClick={() => setSidebarOpen(false)} />}

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <button className="new-chat" onClick={newChat}>＋ New chat</button>
        <div className="session-heading">Chats</div>
        <nav className="session-list">
          {sessions.length === 0 && <p className="muted small">No chats yet</p>}
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session ${s.id === activeId ? "active" : ""}`}
              onClick={() => editingId !== s.id && openSession(s.id)}
            >
              <span className={`dot ${s.source}`} title={SOURCES[s.source]?.label} />
              {editingId === s.id ? (
                <input
                  className="rename"
                  autoFocus
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={() => saveTitle(s.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveTitle(s.id);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span className="session-title">{s.title}</span>
              )}
              <span className="session-actions">
                <button
                  title="Rename"
                  onClick={(e) => { e.stopPropagation(); setEditingId(s.id); setEditTitle(s.title); }}
                >✎</button>
                <button
                  title="Delete"
                  onClick={(e) => { e.stopPropagation(); removeSession(s.id); }}
                >🗑</button>
              </span>
            </div>
          ))}
        </nav>
      </aside>

      <main className="main">
        <header className="topbar">
          <button className="menu" onClick={() => setSidebarOpen(true)} aria-label="Open chats">☰</button>
          <h1 className="title">{"Nexora AI"}</h1>
          <div className="source-toggle" role="tablist">
            {Object.entries(SOURCES).map(([key, s]) => (
              <button
                key={key}
                className={source === key ? "selected" : ""}
                onClick={() => changeSource(key)}
                title={s.hint}
                disabled={sending}
              >{s.label}</button>
            ))}
          </div>
        </header>

        <section className="messages">
          {messages.length === 0 && !sending ? (
            <div className="empty">
              <h2>Ask me anything</h2>
              <p className="muted">{SOURCES[source].hint}</p>
              <div className="suggestions">
                {SUGGESTIONS[source].map((q) => (
                  <button key={q} onClick={() => send(q)}>{q}</button>
                ))}
              </div>
            </div>
          ) : (
            <div className="thread">
              {messages.map((m) => (
                <div key={m.id} className={`row ${m.role}`}>
                  <div className={`avatar ${m.role}`}>{m.role === "user" ? "You" : "AI"}</div>
                  <div className={`bubble ${m.is_error ? "error" : ""}`}>
                    {m.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown> : m.content}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="row assistant">
                  <div className="avatar assistant">AI</div>
                  <div className="bubble typing"><span /><span /><span /></div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </section>

        <footer className="composer-wrap">
          {error && <div className="error-bar">{error}</div>}
          <div className="composer">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              placeholder={`Ask the ${SOURCES[source].label.toLowerCase()}...`}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={sending}
            />
            <button className="send" onClick={() => send()} disabled={sending || !input.trim()} aria-label="Send">
              ➤
            </button>
          </div>
          <p className="muted small center">Enter to send · Shift+Enter for a new line</p>
        </footer>
      </main>
    </div>
  );
}
