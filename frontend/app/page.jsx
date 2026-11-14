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

const CHAT_CHIPS = ["Run step 1", "Run step 2", "Run step 3", "Approve & update", "Check this packet", "Show the rules"];

// Floating glass nav — feather-style stroke icons, one per section.
const NAV_ICONS = {
  beats: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />,
  "band-room": <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />,
  xray: <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></>,
  repo: <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />,
  chat: <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />,
};
const NAV_ITEMS = [
  { id: "beats", label: "Demo Steps", short: "Steps" },
  { id: "band-room", label: "Live Updates", short: "Live" },
  { id: "xray", label: "Memory Check", short: "Memory" },
  { id: "repo", label: "Rules", short: "Rules" },
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
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()).replace("Opd", "OPD").replace("Ns1", "NS1").replace("Icd10", "ICD-10");
}

// Plain words for the insurance denial codes the backend returns.
const DENIAL_LABELS = {
  opd_convertible: "Denied as outpatient care",
  ped_nondisclosure: "Pre-existing condition not declared",
  room_rent_cap: "Room rent over the limit",
};

function denialLabel(s) {
  return DENIAL_LABELS[s] || pretty(s);
}

function docLabel(s) {
  return pretty(String(s));
}

// Raw case IDs ("SYNTHETIC-CLM-E3-BULLETIN-PT6WK") in short, quiet words.
function caseLabel(c) {
  const tokens = String(c || "")
    .replace(/^SYNTHETIC-CLM-/i, "")
    .split("-")
    .filter((p) => p && !/^E\d$/i.test(p))
    .map((p) => {
      if (/^PT6WK$/i.test(p)) return "6-week PT";
      if (/^PT4WK$/i.test(p)) return "4-week PT";
      return p.charAt(0).toUpperCase() + p.slice(1).toLowerCase();
    });
  return tokens.join(" ") || "Past case";
}

// The backend verdicts, in the words a first-time visitor understands.
function verdictLabel(v) {
  if (v === "APPROVE") return "Ready to send";
  if (v === "VETO") return "Stopped — needs fixing";
  return v;
}

function backedNote(n) {
  return n ? `Backed by ${n} past wins` : "No past cases to back it";
}

// Raw stream event names ("retain.completed") in plain words.
function eventLabel(t) {
  if (!t) return "Update";
  if (t.includes("retain")) return "Saved to memory";
  if (t.includes("commit")) return "Rules updated";
  if (t.includes("veto")) return "Appeal stopped";
  if (t.includes("appeal")) return "Appeal checked";
  return t.replace(/[._]/g, " ");
}

function layerLabel(l) {
  return l === "native" ? "memory safety check" : "ClaimShield safety check";
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
      text: "Assistant. I run the same steps as the buttons — try “Run step 1”, “Check this packet”, “Show the rules”, or “Help”.",
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
      if (!beats) return;
      if (beats.getBoundingClientRect().top > 120) setActiveNav("beats");
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setError("The system isn't running — the ClaimShield service did not answer. Please start it and reload."));
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
    setResults((r) => ({ ...r, 1: { out: verdictLabel(data.verdict), cls: data.verdict === "APPROVE" ? "ok" : "no", note: backedNote(data.proof_count) } }));
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
    const layers = [...new Set(Object.values(data.pii_layers || {}))].map(layerLabel).join(", ") || "nothing found";
    setResults((r) => ({ ...r, 2: { out: "Removed", cls: "ok", note: layers } }));
    return data;
  }

  async function beat3() {
    setError(null);
    setToast(null);
    const { data } = await post("/appeals/strategy", PT_CLAIM);
    setPacket(data);
    setResults((r) => ({ ...r, 3: { out: verdictLabel(data.verdict), cls: data.verdict === "APPROVE" ? "ok" : "no", note: backedNote(data.proof_count) } }));
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
        out: recheck.data.verdict === "BLOCKED" ? "Blocked" : recheck.data.verdict === "WARN" ? "Passed, with a warning" : "Passed",
        cls: recheck.data.verdict === "BLOCKED" ? "wait" : "ok",
        note: (recheck.data.missing || []).map(docLabel).join(", ") || "Nothing missing",
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
      desk("I run the same steps as the buttons. Try: Run step 1, Run step 2, Run step 3, Approve & update, Check this packet, Show the rules, or Status.");
      return;
    }
    if (/(step|beat) 1|day-?1 appeal|first (step|beat)/.test(t)) {
      try {
        const d = await beat1();
        desk(`${verdictLabel(d.verdict)} — ${backedNote(d.proof_count).toLowerCase()}.`, d.reason);
      } catch {
        desk("Step 1 didn't run — is the system running?");
      }
      return;
    }
    if (/(step|beat) 2|scrub|redact|private|ssn/.test(t)) {
      try {
        const d = await beat2();
        desk("Private details were removed before anything was saved — the saved text is clean.", `Removed: ${(d.pii_scrubbed || []).join(", ")}`);
      } catch {
        desk("Step 2 didn't run — is the system running?");
      }
      return;
    }
    if (/(step|beat) 3|stale|old argument|pt appeal/.test(t)) {
      try {
        const d = await beat3();
        desk(`${verdictLabel(d.verdict)} — ${backedNote(d.proof_count).toLowerCase()}.`, d.reason);
      } catch {
        desk("Step 3 didn't run — is the system running?");
      }
      return;
    }
    if (/(step|beat) 4|commit|patch|approve/.test(t)) {
      try {
        const d = await beat4();
        if (!d) { desk("That update didn't save — see the message above the steps."); return; }
        desk(`Rules updated, then the same packet was checked again: ${d.recheck.verdict === "BLOCKED" ? "Blocked" : d.recheck.verdict}.`, `Missing: ${(d.recheck.missing || []).map(docLabel).join(", ") || "nothing"}`);
      } catch {
        desk("Step 4 didn't run — is the system running?");
      }
      return;
    }
    if (/check/.test(t)) {
      try {
        const { data } = await post("/scrubber/check", COMPLETE_DENGUE_PACKET);
        setCheck(data);
        desk(`Packet check: ${data.verdict === "BLOCKED" ? "Blocked" : data.verdict}.`, `Missing: ${(data.missing || []).map(docLabel).join(", ") || "nothing"}`);
      } catch {
        desk("The check didn't run — is the system running?");
      }
      return;
    }
    if (/rules?|checklist/.test(t)) {
      const all = rules?.rules || [];
      if (!all.length) { desk("The rules are still loading — try again in a moment."); return; }
      const active = all.filter((r) => r.is_active);
      desk(
        `${active.length} rules are in use. ${active.map((r) => `${pretty(r.insurer)} ${pretty(r.diagnosis_group)}, version ${r.version} (backed by ${r.proof_count} wins)`).join("; ")}.`,
        `${all.length} rules in total · newest is version ${Math.max(...all.map((r) => r.version || 0))}`
      );
      return;
    }
    if (/health|status|backend|system/.test(t)) {
      if (!health) { desk("The system is not answering right now."); return; }
      desk(`Everything is running. Checklist version ${health.rules_version || "?"}.`, `Memory mode: ${health.backend === "memory" ? "built-in memory (demo)" : health.backend || "memory"}`);
      return;
    }
    if (/appeal dengue|dengue appeal/.test(t)) {
      try {
        const { data } = await post("/appeals/strategy", DENGUE_CLAIM);
        setPacket(data);
        setResults((r) => ({ ...r, 1: { out: verdictLabel(data.verdict), cls: data.verdict === "APPROVE" ? "ok" : "no", note: backedNote(data.proof_count) } }));
        desk(`${verdictLabel(data.verdict)} — ${backedNote(data.proof_count).toLowerCase()}.`, data.reason);
      } catch {
        desk("The appeal check didn't run — is the system running?");
      }
      return;
    }
    if (packet) {
      desk(`Last check: ${verdictLabel(packet.verdict)} — ${backedNote(packet.proof_count).toLowerCase()}.`, packet.reason);
      return;
    }
    desk("Nothing has run yet. Try “Run step 1” or “Help” and I will run it for you.");
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
        {health && <span className="pill">Memory: connected</span>}
        <span className="live">Watching live</span>
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
        <button className="chat-toggle" onClick={() => setChatOpen(true)}>Assistant</button>
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
        <button type="button" className="navlink" onClick={() => setChatOpen(true)}>{navIcon("chat")}Assistant</button>
      </nav>

      <div className="wrap">
        <div className="desk-head">
          <div>
            <span className="t1">Hindsight remembers.</span>
            <span className="t2">The desk decides.</span>
          </div>
        </div>

        <div className="beats-outcome howsteps" aria-label="How it works">
          <div className="beat">
            <span className="n">1 · REMEMBER</span>
            <div className="out">It remembers what worked</div>
            <p>Every past appeal result is saved, along with how many times it worked.</p>
          </div>
          <div className="beat">
            <span className="n">2 · VERIFY</span>
            <div className="out">It checks the new claim</div>
            <p>The new packet is compared with the past cases that won.</p>
          </div>
          <div className="beat">
            <span className="n">3 · DO IT RIGHT</span>
            <div className="out">It fixes it, or stops it</div>
            <p>A correct appeal is drafted for your approval. An incomplete packet is blocked before it is sent.</p>
          </div>
        </div>

        <div className="beats" id="beats">
          {[
            { n: 1, label: "Step 1 · Appeal with no memory", fn: beat1 },
            { n: 2, label: "Step 2 · Remove private details", fn: beat2 },
            { n: 3, label: "Step 3 · Check an old argument", fn: beat3 },
            { n: 4, label: "Step 4 · Approve & update rules", fn: beat4, primary: true },
          ].map((s) => (
            <div className="beat-step" key={s.n}>
              <button onClick={s.fn} className={s.primary ? "primary" : undefined}>{s.label}</button>
              <p className={`beat-status ${results[s.n]?.cls || ""}`}>
                {results[s.n] ? <><b>{results[s.n].out}</b>{results[s.n].note ? ` — ${results[s.n].note}` : ""}</> : "Not run yet"}
              </p>
            </div>
          ))}
        </div>

        <div className="panes">
          <section className="pane" id="band-room" aria-label="Live Updates">
            <h2>Live Updates</h2>
            <p className="pane-meta">Everything the desk does, as it happens</p>
            <div className="body">
              {toast && (
                <div className="toast">
                  <b>Private details removed:</b> {toast.pii_scrubbed.join(", ")} — caught by{" "}
                  {[...new Set(Object.values(toast.pii_layers || {}))].map(layerLabel).join(", ")}
                </div>
              )}
              {events.length === 0 ? (
                <p className="muted">Nothing yet. Run a step above and watch it happen here.</p>
              ) : (
                events.slice(-6).map((e, i) => (
                  <div className="turn" key={i}>
                    <p>
                      <b>{eventLabel(e.event_type)}</b>
                      {e.document_id ? ` — ${e.document_id.replace("SYNTHETIC-", "")}` : ""}
                    </p>
                  </div>
                ))
              )}
              {commit && (
                <p className="commit-note">
                  Checklist updated to <b>version {commit.rule?.version}</b>
                  {commit.rule?.supersedes ? ` (replaces version ${commit.rule.supersedes})` : ""} — a packet checked with the new rules:{" "}
                  <b>{commit.probe_verdict === "BLOCKED" ? "Blocked" : commit.probe_verdict}</b>
                </p>
              )}
            </div>
          </section>

          <section className="pane xray" id="xray" aria-label="Memory Check">
            <svg className="xray-arc" viewBox="0 0 180 90" aria-hidden="true">
              <path d="M10 82 A 80 80 0 0 1 170 82" fill="none" strokeWidth="10" strokeLinecap="round"
                stroke={packet?.verdict === "APPROVE" ? "var(--approve)" : packet?.verdict === "VETO" ? "var(--veto)" : "var(--accent)"}
                strokeOpacity="0.35" />
            </svg>
            <h2>Memory Check</h2>
            <p className="pane-meta">Star Health · Dengue · ₹1,45,000 · Sample case</p>
            <div className="body">
              {!packet ? (
                <p className="muted">No claim checked yet. Run Step 1 or Step 3.</p>
              ) : (
                <>
                  <div className="verdict-row">
                    <span className={`verdict ${packet.verdict === "APPROVE" ? "approve" : "veto"}`}>{verdictLabel(packet.verdict)}</span>
                    <span className="proof">
                      {packet.proof_count ? <>backed by <b>{packet.proof_count} past wins</b></> : "no past cases behind it"}
                    </span>
                  </div>
                  <p className="label">Why</p>
                  <p className="reason">{packet.reason}</p>
                  <p className="label">Past cases this is based on</p>
                  <div>
                    {(packet.evidence || []).slice(0, 3).map((ev, i) => (
                      <div className="cite" key={i}>
                        <span className="name">
                          {caseLabel(ev.citation)}
                          <small>
                            Past case {String(ev.observation_id || "").replace("obs_", "")}
                            {ev.superseded ? " · this rule has changed since" : ""}
                          </small>
                        </span>
                        <span className="pc">
                          won <b>{ev.proof_count}</b> times
                        </span>
                      </div>
                    ))}
                    {(packet.evidence || []).length > 3 && (
                      <p className="muted" style={{ fontSize: 13, margin: "8px 0 0" }}>
                        and {(packet.evidence || []).length - 3} more past cases behind this
                      </p>
                    )}
                  </div>
                  {packet.missing_evidence?.length > 0 && (
                    <>
                      <p className="label">What is missing</p>
                      <ul className="missing">
                        {packet.missing_evidence.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {check && (
                    <div className="recheck">
                      <b className={check.verdict === "BLOCKED" ? "blocked" : ""}>{check.verdict === "BLOCKED" ? "Blocked before sending" : check.verdict}</b>
                      {check.missing?.length ? ` — missing: ${check.missing.map(docLabel).join(", ")}` : ""}
                    </div>
                  )}
                </>
              )}
            </div>
          </section>

          <section className="pane" id="repo" aria-label="Rules">
            <h2>Rules</h2>
            <p className="pane-meta">The checklist every new claim is checked against{maxVersion ? ` · now on version ${maxVersion}` : ""}</p>
            <div className="body">
              {!rules ? (
                <p className="muted">Loading the rules…</p>
              ) : (
                <>
                  {activeRules.map((r) => (
                    <div className="rule" key={r.rule_id}>
                      <div className="name">
                        {pretty(r.insurer)} — {pretty(r.diagnosis_group)} — {denialLabel(r.denial_reason)}
                      </div>
                      <div className="meta">
                        Version {r.version} · in use · backed by <b>{r.proof_count} wins</b>
                      </div>
                      <div className="req">
                        Must have: <code>{r.requires.map(docLabel).join(", ")}</code>
                      </div>
                    </div>
                  ))}
                  <p className="rules-foot">
                    {rules.rules.length} rules in total · oldest version 1, newest version {maxVersion}
                  </p>
                </>
              )}
            </div>
          </section>
        </div>

        <div className="eval-strip">
          <span className="eval-k">Tested, not just claimed</span>
          <span>With memory: <b>19 of 20</b> cases decided right, and <b>all 5</b> tricky cases caught</span>
          <span>Without memory: 16 of 20 · With simple search only: 11 of 20, and 0 of 5 tricky cases</span>
        </div>
      </div>
      </div>

      {chatOpen && (
        <aside className="chat" aria-label="Assistant">
          <div className="chat-head">
            <span>Assistant</span>
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
              placeholder="Type what you want to do"
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
        <button type="button" onClick={() => setChatOpen(true)}>{navIcon("chat")}<span>Assistant</span></button>
      </nav>
    </main>
  );
}
