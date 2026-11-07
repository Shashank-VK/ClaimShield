"use client";

import { useEffect, useState } from "react";
import LilacDuskCanopy from "./canopy-background";

// NEXT_PUBLIC_API_URL points the cockpit at a deployed API (e.g. Render).
// A bare host is treated as https://<host>; unset means local dev.
const _apiEnv = (process.env.NEXT_PUBLIC_API_URL || "").trim();
const API = _apiEnv
  ? _apiEnv.startsWith("http")
    ? _apiEnv
    : `https://${_apiEnv}`
  : "http://127.0.0.1:8000";
const DISCLAIMER = "Draft for human review, not legal/medical advice. All cases SYNTHETIC.";

const DENGUE_CLAIM = {
  claim_id: "SYNTHETIC-CLM-DEMO-DENGUE",
  insurer: "star_health",
  diagnosis_group: "dengue",
  denial_reason: "opd_convertible",
  claim_type: "reimbursement",
  amount: "₹1,45,000",
  argument:
    "Inpatient admission was medically necessary; NS1 antigen positive with platelet count 42000 and continuous IV fluid administration.",
  documents: ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
};

const PT_CLAIM = {
  claim_id: "SYNTHETIC-CLM-DEMO-PT",
  insurer: "star_health",
  diagnosis_group: "osteoarthritis",
  denial_reason: "ped_nondisclosure",
  claim_type: "cashless",
  amount: "₹2,10,000",
  argument: "4-week conservative physiotherapy completed; appeal on medical necessity for knee surgery.",
  documents: ["discharge_summary"],
};

const V4_PATCH = {
  family: "star_health_dengue_opd",
  insurer: "star_health",
  diagnosis_group: "dengue",
  denial_reason: "opd_convertible",
  requires: ["discharge_summary", "ns1_antigen_report", "final_bill_icd10", "platelet_report"],
  blocks_when_missing: ["discharge_summary", "platelet_report"],
  warn_when_missing: ["ns1_antigen_report"],
  source_obs: "obs_304",
  proof_count: 6,
};

const COMPLETE_DENGUE_PACKET = {
  insurer: "star_health",
  diagnosis_group: "dengue",
  denial_reason: "opd_convertible",
  documents: ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
};

const BEAT_NOTES = {
  1: "Day-1 appeal",
  2: "SSN intake",
  3: "Stale PT veto",
  4: "Commit patch",
};

const CHAT_CHIPS = ["Run beat 1", "Run beat 2", "Run beat 3", "Commit patch", "Check packet", "Rules"];

// Floating glass nav — feather-style stroke icons, one per section.
const NAV_ICONS = {
  beats: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />,
  "band-room": <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />,
  xray: <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></>,
  repo: <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />,
  outcomes: <><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></>,
  chat: <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />,
};
const NAV_ITEMS = [
  { id: "beats", label: "Beats", short: "Beats" },
  { id: "band-room", label: "Band Room", short: "Band" },
  { id: "xray", label: "Hindsight X-Ray", short: "X-Ray" },
  { id: "repo", label: "Repo Viewer", short: "Repo" },
  { id: "outcomes", label: "Outcomes", short: "Outcomes" },
];
const navIcon = (id) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{NAV_ICONS[id]}</svg>
);

async function post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { status: res.status, data: await res.json() };
}

function pretty(s) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()).replace("Opd", "OPD");
}

export default function Cockpit() {
  const [health, setHealth] = useState(null);
  const [rules, setRules] = useState(null);
  const [events, setEvents] = useState([]);
  const [packet, setPacket] = useState(null);
  const [toast, setToast] = useState(null);
  const [check, setCheck] = useState(null);
  const [commit, setCommit] = useState(null);
  const [error, setError] = useState(null);
  const [results, setResults] = useState({});
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState([
    {
      from: "desk",
      text: "Desk chat. I run the same work as the buttons — try “Run beat 1”, “Check packet”, “Rules”, or “Help”.",
    },
  ]);

  // Theme: stored choice wins, default dark (the approved first impression).
  const [theme, setTheme] = useState("dark");
  useEffect(() => {
    let stored = "dark";
    try { stored = localStorage.getItem("claimshield-theme") || "dark"; } catch {}
    if (stored !== "light" && stored !== "dark") stored = "dark";
    setTheme(stored);
    document.documentElement.dataset.theme = stored;
  }, []);
  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("claimshield-theme", next); } catch {}
  };

  // Active nav pill: click sets it at once; scrolling updates it at the
  // stacked regions (Beats at the top, Outcomes at the bottom). The three
  // panes share one row, so a pane keeps the last clicked highlight.
  const [activeNav, setActiveNav] = useState("beats");
  useEffect(() => {
    const onScroll = () => {
      const beats = document.getElementById("beats");
      const outcomes = document.getElementById("outcomes");
      if (!beats || !outcomes) return;
      const oTop = outcomes.getBoundingClientRect().top;
      const bTop = beats.getBoundingClientRect().top;
      if (oTop < window.innerHeight * 0.6) setActiveNav("outcomes");
      else if (bTop > 120) setActiveNav("beats");
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setError(`Backend not reachable at ${API} — start it with uvicorn backend.main:app`));
    fetch(`${API}/scrubber/rules`)
      .then((r) => r.json())
      .then(setRules)
      .catch(() => {});
    const source = new EventSource(`${API}/sse/stream`);
    // Named SSE events do NOT fire onmessage (that fires only for unnamed
    // events). The backend sends `event: retain.completed`, so without the
    // listener below the Band Room never received a single event.
    const onEvent = (e) => {
      try {
        setEvents((prev) => [...prev.slice(-49), JSON.parse(e.data)]);
      } catch {}
    };
    source.onmessage = onEvent;
    source.addEventListener("retain.completed", onEvent);
    source.onerror = () => {};
    return () => source.close();
  }, []);

  async function beat1() {
    setError(null);
    setToast(null);
    // Day-1 generic appeal: a pattern with no history has no evidence to cite.
    const { data } = await post("/appeals/strategy", {
      ...DENGUE_CLAIM,
      claim_id: "SYNTHETIC-CLM-DAY1",
      insurer: "care_health",
      argument: "Please approve this claim.",
    });
    setPacket(data);
    setResults((r) => ({ ...r, 1: { out: data.verdict, cls: data.verdict === "APPROVE" ? "ok" : "no", note: `proof ×${data.proof_count}` } }));
    return data;
  }

  async function beat2() {
    setError(null);
    const { data } = await post("/webhooks/claim-intake", {
      document_id: "SYNTHETIC-CLM-SSN-01",
      content: "Claim packet: SSN 123-45-6789 in the document. Star Health dengue claim.",
      tags: ["insurer:star_health", "synthetic"],
    });
    setToast(data);
    const layers = Object.keys(data.pii_layers || {}).join(", ") || "none";
    setResults((r) => ({ ...r, 2: { out: "Redacted", cls: "ok", note: layers } }));
    return data;
  }

  async function beat3() {
    setError(null);
    setToast(null);
    const { data } = await post("/appeals/strategy", PT_CLAIM);
    setPacket(data);
    setResults((r) => ({ ...r, 3: { out: data.verdict, cls: data.verdict === "APPROVE" ? "ok" : "no", note: `proof ×${data.proof_count}` } }));
    return data;
  }

  async function beat4() {
    setError(null);
    const { status, data } = await post("/scrubber/commit", {
      claim_id: DENGUE_CLAIM.claim_id,
      approved: true,
      rule: V4_PATCH,
      probe_packet: COMPLETE_DENGUE_PACKET,
    });
    if (status !== 200) {
      setError(`Commit failed (${status}): ${data.detail || "unknown error"}`);
      return null;
    }
    setCommit(data);
    const recheck = await post("/scrubber/check", COMPLETE_DENGUE_PACKET);
    setCheck(recheck.data);
    const r = await fetch(`${API}/scrubber/rules`).then((x) => x.json());
    setRules(r);
    setResults((prev) => ({
      ...prev,
      4: {
        out: recheck.data.verdict,
        cls: recheck.data.verdict === "BLOCKED" ? "wait" : "ok",
        note: (recheck.data.missing || []).join(", ") || "all documents present",
      },
    }));
    return { commit: data, recheck: recheck.data };
  }

  function desk(text, detail) {
    setMessages((m) => [...m, { from: "desk", text, detail }]);
  }

  async function sendChat(rawText) {
    const text = rawText.trim();
    if (!text) return;
    setMessages((m) => [...m, { from: "user", text }]);
    setChatInput("");
    const t = text.toLowerCase();

    if (/help|what can you/.test(t)) {
      desk("I run the cockpit's work. Try: Run beat 1, Run beat 2, Run beat 3, Commit patch, Check packet, Rules, or Health.");
      return;
    }
    if (/beat 1|day-?1 appeal|first beat/.test(t)) {
      try {
        const d = await beat1();
        desk(`${d.verdict} — proof ×${d.proof_count}.`, d.reason);
      } catch {
        desk("Beat 1 failed — is the backend running?");
      }
      return;
    }
    if (/beat 2|scrub|redact|ssn/.test(t)) {
      try {
        const d = await beat2();
        desk("Packet scrubbed before it was stored — the stored text is clean.", `Redacted: ${(d.pii_scrubbed || []).join(", ")}`);
      } catch {
        desk("Beat 2 failed — is the backend running?");
      }
      return;
    }
    if (/beat 3|stale|pt appeal/.test(t)) {
      try {
        const d = await beat3();
        desk(`${d.verdict} — proof ×${d.proof_count}.`, d.reason);
      } catch {
        desk("Beat 3 failed — is the backend running?");
      }
      return;
    }
    if (/beat 4|commit|patch/.test(t)) {
      try {
        const d = await beat4();
        if (!d) { desk("Commit failed — see the error bar above the beats."); return; }
        desk(`Patch committed, then rechecked: ${d.recheck.verdict}.`, `Missing: ${(d.recheck.missing || []).join(", ") || "none"} · rule ${d.recheck.rule_id}`);
      } catch {
        desk("Beat 4 failed — is the backend running?");
      }
      return;
    }
    if (/check packet|check the packet|verify packet/.test(t)) {
      try {
        const { data } = await post("/scrubber/check", COMPLETE_DENGUE_PACKET);
        setCheck(data);
        desk(`Packet check: ${data.verdict}.`, `Missing: ${(data.missing || []).join(", ") || "none"} · rule ${data.rule_id}`);
      } catch {
        desk("Check failed — is the backend running?");
      }
      return;
    }
    if (/rules?/.test(t)) {
      const all = rules?.rules || [];
      if (!all.length) { desk("Rules are still loading — try again in a moment."); return; }
      const active = all.filter((r) => r.is_active);
      desk(
        `${active.length} active rules. ${active.map((r) => `${pretty(r.insurer)} ${pretty(r.diagnosis_group)} v${r.version} (proof ×${r.proof_count})`).join("; ")}.`,
        `${all.length} rules · history v1 → v${Math.max(...all.map((r) => r.version || 0))}`
      );
      return;
    }
    if (/health|status|backend/.test(t)) {
      if (!health) { desk("Backend is not answering right now."); return; }
      desk(`Backend ${health.status || "ok"} — band ${health.band || "local"}, rules v${health.rules_version || "?"}`, `Adapter: ${health.backend || health.adapter || "memory"}`);
      return;
    }
    if (/appeal dengue|dengue appeal/.test(t)) {
      try {
        const { data } = await post("/appeals/strategy", DENGUE_CLAIM);
        setPacket(data);
        setResults((r) => ({ ...r, 1: { out: data.verdict, cls: data.verdict === "APPROVE" ? "ok" : "no", note: `proof ×${data.proof_count}` } }));
        desk(`${data.verdict} — proof ×${data.proof_count}.`, data.reason);
      } catch {
        desk("Appeal failed — is the backend running?");
      }
      return;
    }
    if (packet) {
      desk(`Last packet: ${packet.verdict}, proof ×${packet.proof_count}.`, packet.reason);
      return;
    }
    desk("Nothing run yet. Try “Run beat 1” or “Help” and I will run it for you.");
  }

  const activeRules = (rules?.rules || []).filter((r) => r.is_active);
  const maxVersion = (rules?.rules || []).reduce((m, r) => Math.max(m, r.version || 0), 0);

  return (
    <main>
      {/* Canopy is the background now (moonlit dark / noon-plaster light — the
          lilac-dusk preset is one word away). The synapse network file stays
          in the codebase, unmounted: two animated backdrops would fight. */}
      <div className="canopy-bg">
        <LilacDuskCanopy preset={theme === "dark" ? "moonlit" : "noon-plaster"} height="100%" />
      </div>
      {/* SVG displacement lens for the frosted glass (research:
          design/frosted-glass-research.md). Chromium-only: the url() in
          backdrop-filter is gated by @supports in CSS, so other browsers
          keep the plain frost. */}
      <svg width="0" height="0" aria-hidden="true" style={{ position: "absolute" }}>
        <defs>
          <filter id="glass-refract" x="-20%" y="-20%" width="140%" height="140%">
            <feTurbulence type="fractalNoise" baseFrequency="0.008 0.012" numOctaves="2" seed="9" result="noise" />
            <feGaussianBlur in="noise" stdDeviation="1.4" result="soft" />
            <feDisplacementMap in="SourceGraphic" in2="soft" scale="60" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>
      <div className="grain" aria-hidden="true" />
      <header className="topbar">
        <div className="brand">
          <svg width="26" height="26" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <path d="M16 3.5 26.5 7.5V16c0 6.5-4.5 11.5-10.5 12.5C10 27.5 5.5 22.5 5.5 16V7.5L16 3.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
            <path d="M11 16.5 14.8 20.2 21.5 12.5" style={{ stroke: "var(--accent)" }} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="wordmark">ClaimShield Desk</span>
        </div>
        <span className="spacer" />
        {health && <span className="pill">backend: {health.backend}</span>}
        <span className="live">Band room · live</span>
        <button className="theme-toggle" onClick={toggleTheme} aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"} title={theme === "dark" ? "Light theme" : "Dark theme"}>
          {theme === "dark" ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>
        <button className="chat-toggle" onClick={() => setChatOpen(true)}>Chat</button>
      </header>
      {error && <div className="errorbar">{error}</div>}

      <div className="shell">
      <nav className="sidenav" aria-label="Desk sections">
        {NAV_ITEMS.map((item) => (
          <a key={item.id} href={`#${item.id}`} className={activeNav === item.id ? "active" : ""} onClick={() => setActiveNav(item.id)}>
            {navIcon(item.id)}
            {item.label}
          </a>
        ))}
        <button type="button" className="navlink" onClick={() => setChatOpen(true)}>{navIcon("chat")}Chat</button>
        <div className="side-card">
          <div className="side-card-k">On the desk</div>
          <div className="side-card-v">Star Health · Dengue</div>
          <div className="side-card-s">₹1,45,000 · SYNTHETIC</div>
          <div className="side-card-s">Backend: {health?.backend ?? "…"} · Rules v{health?.rules_version ?? (maxVersion || "…")}</div>
        </div>
      </nav>

      <div className="wrap">
        <div className="desk-head">
          <div>
            <span className="t1">Hindsight remembers.</span>
            <span className="t2">The desk decides.</span>
          </div>
          <div className="desk-stats">
            <div className="stat"><div className="v"><b>19</b>/20</div><div className="k">Eval set</div></div>
            <div className="stat"><div className="v"><b>5</b>/5</div><div className="k">Adversarial</div></div>
            <div className="stat"><div className="v">v{health?.rules_version ?? (maxVersion || "…")}</div><div className="k">Scrubber rules</div></div>
            <div className="stat"><div className="v">{health?.backend ?? "…"}</div><div className="k">Backend</div></div>
          </div>
        </div>

        <div className="beats" id="beats">
          <button onClick={beat1}>Beat 1 · Day-1 appeal</button>
          <button onClick={beat2}>Beat 2 · SSN intake</button>
          <button onClick={beat3}>Beat 3 · Stale PT veto</button>
          <button className="primary" onClick={beat4}>Beat 4 · Commit patch</button>
        </div>

        <div className="panes">
          <section className="pane" id="band-room" aria-label="Band Room">
            <h2>Band Room</h2>
            <div className="body">
              {toast && (
                <div className="toast">
                  <b>Redacted:</b> {toast.pii_scrubbed.join(", ")} — layers:{" "}
                  {Object.entries(toast.pii_layers || {}).map(([t, l]) => `${t} (${l})`).join(", ")}
                </div>
              )}
              {events.length === 0 ? (
                <p className="muted">No events yet. Run a beat to drive the room.</p>
              ) : (
                events.slice(-6).map((e, i) => (
                  <div className="turn" key={i}>
                    <p>
                      <b>{e.event_type}</b>
                      {e.document_id ? ` — ${e.document_id}` : ""}
                      {e.event_id ? ` — ${e.event_id}` : ""}
                    </p>
                  </div>
                ))
              )}
              {commit && (
                <p className="commit-note">
                  Committed <b>{commit.rule?.rule_id}</b> (v{commit.rule?.version}
                  {commit.rule?.supersedes ? `, supersedes v${commit.rule.supersedes}` : ""}) — probe:{" "}
                  <b>{commit.probe_verdict}</b>
                </p>
              )}
            </div>
          </section>

          <section className="pane xray" id="xray" aria-label="Hindsight X-Ray">
            <svg className="xray-arc" viewBox="0 0 180 90" aria-hidden="true">
              <path d="M10 82 A 80 80 0 0 1 170 82" fill="none" strokeWidth="10" strokeLinecap="round"
                stroke={packet?.verdict === "APPROVE" ? "var(--approve)" : packet?.verdict === "VETO" ? "var(--veto)" : "var(--accent)"}
                strokeOpacity="0.35" />
            </svg>
            <h2>Hindsight X-Ray</h2>
            <p className="pane-meta">Star Health · Dengue · ₹1,45,000 · SYNTHETIC</p>
            <div className="body">
              {!packet ? (
                <p className="muted">No appeal packet yet. Run Beat 1 or Beat 3.</p>
              ) : (
                <>
                  <div className="verdict-row">
                    <span className={`verdict ${packet.verdict === "APPROVE" ? "approve" : "veto"}`}>{packet.verdict}</span>
                    <span className="proof">
                      proof <b>×{packet.proof_count}</b>
                    </span>
                  </div>
                  <p className="reason">{packet.reason}</p>
                  <p className="label">Evidence</p>
                  <div>
                    {(packet.evidence || []).map((ev, i) => (
                      <div className="cite" key={i}>
                        <span className="name">
                          {ev.citation}
                          <small>
                            obs {ev.observation_id}
                            {ev.superseded ? " · superseded" : ""}
                          </small>
                        </span>
                        <span className="pc">
                          proof <b>×{ev.proof_count}</b>
                        </span>
                      </div>
                    ))}
                  </div>
                  {packet.missing_evidence?.length > 0 && (
                    <>
                      <p className="label">Missing evidence</p>
                      <ul className="missing">
                        {packet.missing_evidence.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {check && (
                    <div className="recheck">
                      <b className={check.verdict === "BLOCKED" ? "blocked" : ""}>{check.verdict}</b>
                      {check.missing?.length ? ` — missing: ${check.missing.join(", ")}` : ""} (rule {check.rule_id})
                    </div>
                  )}
                </>
              )}
            </div>
          </section>

          <section className="pane" id="repo" aria-label="Repo Viewer">
            <h2>Repo Viewer</h2>
            <p className="pane-meta">scrubber_rules.json{maxVersion ? ` · v${maxVersion}` : ""}</p>
            <div className="body">
              {!rules ? (
                <p className="muted">Loading rules…</p>
              ) : (
                <>
                  {activeRules.map((r) => (
                    <div className="rule" key={r.rule_id}>
                      <div className="name">
                        {pretty(r.insurer)} — {pretty(r.diagnosis_group)} — {pretty(r.denial_reason)}
                      </div>
                      <div className="meta">
                        v{r.version} · active · proof <b>×{r.proof_count}</b>
                      </div>
                      <div className="req">
                        Requires: <code>{r.requires.join(", ")}</code>
                      </div>
                    </div>
                  ))}
                  <p className="rules-foot">
                    {rules.rules.length} rules · history v1 → v{maxVersion}
                  </p>
                </>
              )}
            </div>
          </section>
        </div>

        <div className="beats-outcome" id="outcomes" aria-label="Beat outcomes">
          {[1, 2, 3, 4].map((n) => (
            <div className="beat" key={n}>
              <span className="n">BEAT {n}</span>
              <div className={`out ${results[n]?.cls || ""}`}>{results[n]?.out || "Not run"}</div>
              <p>{results[n]?.note || BEAT_NOTES[n]}</p>
            </div>
          ))}
        </div>
        <div className="eval-strip">
          <span className="eval-k">Measured, not claimed</span>
          <span>Hindsight <b>19/20</b> · Adversarial <b>5/5</b></span>
          <span>Stateless 16/20 · Plain RAG 11/20 · Adversarial 0/5</span>
        </div>
      </div>
      </div>

      {chatOpen && (
        <aside className="chat" aria-label="Desk chat">
          <div className="chat-head">
            <span>Desk chat</span>
            <button className="chat-close" onClick={() => setChatOpen(false)}>Close</button>
          </div>
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.from}`}>
                <p>{m.text}</p>
                {m.detail && <p className="msg-detail">{m.detail}</p>}
              </div>
            ))}
          </div>
          <div className="chips">
            {CHAT_CHIPS.map((c) => (
              <button key={c} className="chip" onClick={() => sendChat(c)}>{c}</button>
            ))}
          </div>
          <form
            className="chat-input"
            onSubmit={(e) => { e.preventDefault(); sendChat(chatInput); }}
          >
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Type a command or question"
              aria-label="Chat input"
            />
            <button type="submit">Send</button>
          </form>
        </aside>
      )}

      <footer className="disclaimer">{DISCLAIMER}</footer>
      <nav className="tabbar" aria-label="Desk sections">
        {NAV_ITEMS.map((item) => (
          <a key={item.id} href={`#${item.id}`} className={activeNav === item.id ? "active" : ""} onClick={() => setActiveNav(item.id)}>
            {navIcon(item.id)}
            <span>{item.short}</span>
          </a>
        ))}
        <button type="button" onClick={() => setChatOpen(true)}>{navIcon("chat")}<span>Chat</span></button>
      </nav>
    </main>
  );
}
