import React, { useEffect, useMemo, useState } from "react";
import {
  compileOperatingPack,
  fetchMercuryState,
  reinforceCards,
  runContrastSmackdown,
  runFrontierAgent,
} from "./api";
import {
  AgentTrace,
  ContrastResponse,
  FrontierModelSpec,
  MercuryState,
  PackResponse,
} from "./types";

const MISSION_PRESETS = [
  {
    label: "AUTH SAMESITE LOOP",
    task: "Login keeps redirecting back to /login after a successful password check. Localize the cookie fault and verify.",
  },
  {
    label: "FLAKY BILLING PYTEST",
    task: "Fix the flaky test that fails with AssertionError in test_billing.py by freezing clock instead of mutating prod.",
  },
  {
    label: "ARGON TIER AUDIT",
    task: "Audit mercury/tiers.py to verify gemini-4-argon-high and Ollama Cloud flagships classify as FRONTIER.",
  },
];

export default function App() {
  const [state, setState] = useState<MercuryState | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>("all");
  const [selectedModelId, setSelectedModelId] = useState<string>("gemini-4-argon-high");
  const [activeTab, setActiveTab] = useState<"runtime" | "deck" | "pack" | "moshpit">("runtime");
  const [scanlines, setScanlines] = useState<boolean>(true);
  const [showKeyVault, setShowKeyVault] = useState<boolean>(false);

  // Runtime state
  const [taskInput, setTaskInput] = useState<string>(MISSION_PRESETS[0].task);
  const [execMode, setExecMode] = useState<"auto" | "synth" | "live">("auto");
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [activeTrace, setActiveTrace] = useState<AgentTrace | null>(null);
  const [recoveryNotes, setRecoveryNotes] = useState<string[]>([]);
  const [lastModeUsed, setLastModeUsed] = useState<string>("synth");
  const [lastDurationMs, setLastDurationMs] = useState<number>(0);
  const [statusBanner, setStatusBanner] = useState<string>(
    "SYSTEM ARMED // GEMINI 4 ARGON & OLLAMA CLOUD FRONTIER ENGINES READY"
  );

  // Gatekeeper test input
  const [bouncerInput, setBouncerInput] = useState<string>("gpt-4o-mini");
  const [bouncerVerdict, setBouncerVerdict] = useState<string | null>(null);

  // API keys drawer
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({
    GEMINI_API_KEY: "",
    OLLAMA_API_KEY: "",
    OLLAMA_HOST: "https://ollama.com",
    ANTHROPIC_API_KEY: "",
    OPENAI_API_KEY: "",
    XAI_API_KEY: "",
  });

  // Deck filter
  const [cardKindFilter, setCardKindFilter] = useState<string>("all");

  // Pack compiler state
  const [packTask, setPackTask] = useState<string>(
    "Users bounce back to /login after authenticating. Fix the redirect bug."
  );
  const [packStudentModel, setPackStudentModel] = useState<string>("gpt-4o-mini");
  const [packErrorSig, setPackErrorSig] = useState<string>(
    "AssertionError: expected '/login' to be '/dashboard'"
  );
  const [packFormat, setPackFormat] = useState<"markdown" | "cursor" | "dpo" | "sft">("markdown");
  const [compiledPack, setCompiledPack] = useState<PackResponse | null>(null);

  // Contrast state
  const [contrastResult, setContrastResult] = useState<ContrastResponse | null>(null);

  useEffect(() => {
    fetchMercuryState()
      .then((data) => {
        setState(data);
        if (data.traces.length > 0) {
          setActiveTrace(data.traces[0]);
        }
      })
      .catch((err) => {
        setStatusBanner(`BRIDGE WARNING: ${err.message}`);
      });
  }, []);

  const filteredModels = useMemo(() => {
    if (!state) return [];
    if (selectedProvider === "all") return state.models;
    return state.models.filter((m) => m.provider === selectedProvider);
  }, [state, selectedProvider]);

  const activeModelSpec: FrontierModelSpec | undefined = useMemo(() => {
    return state?.models.find((m) => m.id === selectedModelId) || state?.models[0];
  }, [state, selectedModelId]);

  const filteredCards = useMemo(() => {
    if (!state) return [];
    if (cardKindFilter === "all") return state.cards;
    return state.cards.filter((c) => c.kind === cardKindFilter);
  }, [state, cardKindFilter]);

  async function handleIgniteRun() {
    if (!taskInput.trim() || isRunning) return;
    setIsRunning(true);
    setStatusBanner(`IGNITING FRONTIER AGENT // ${selectedModelId.toUpperCase()} ...`);
    try {
      const nonEmptyKeys = Object.fromEntries(
        Object.entries(apiKeys).filter(([_, v]) => v.trim().length > 0)
      );
      const res = await runFrontierAgent({
        task: taskInput,
        model: selectedModelId,
        mode: execMode,
        api_keys: nonEmptyKeys,
      });
      setState(res.state);
      const enriched =
        res.state.traces.find((t) => t.id === res.run.trace.id) || {
          ...res.run.trace,
          grade: res.run.grade,
          phases: res.run.phases,
        };
      setActiveTrace(enriched);
      setRecoveryNotes(res.run.recovery_injections || []);
      setLastModeUsed(res.run.mode_used);
      setLastDurationMs(res.run.duration_ms);
      setStatusBanner(
        `RUN COMPLETE // ${res.run.model.name.toUpperCase()} (${res.run.mode_used.toUpperCase()}) — GRADE ${Math.round(
          res.run.grade.score * 100
        )}% — DISTILLED ${res.run.distilled_cards.length} CARDS`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusBanner(`RUNTIME ERROR // ${msg}`);
    } finally {
      setIsRunning(false);
    }
  }

  async function handleTestGatekeeper() {
    const candidate = bouncerInput.trim();
    if (!candidate) return;
    try {
      await runFrontierAgent({
        task: "Gatekeeper tier verification",
        model: candidate,
        mode: "synth",
      });
      setBouncerVerdict(`VERIFIED FRONTIER // '${candidate}' ALLOWED INTO RUNTIME`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setBouncerVerdict(`BOUNCED AT THE DOOR // ${msg}`);
    }
  }

  async function handleCompilePack() {
    try {
      const res = await compileOperatingPack({
        task: packTask,
        model: packStudentModel,
        error_signature: packErrorSig || undefined,
      });
      setCompiledPack(res);
      setStatusBanner(
        `PACK COMPILED FOR ${packStudentModel.toUpperCase()} (${res.cards.length} CARDS, ~${res.estimated_tokens} TOKENS)`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusBanner(`PACK ERROR // ${msg}`);
    }
  }

  async function handleRunContrast() {
    try {
      const res = await runContrastSmackdown(selectedModelId);
      setContrastResult(res);
      setState(res.state);
      setStatusBanner(
        `CONTRAST SMACKDOWN // ${selectedModelId.toUpperCase()} vs GPT-4O-MINI — MINTED ${res.contrast_cards.length} CARDS`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusBanner(`CONTRAST ERROR // ${msg}`);
    }
  }

  async function handleReinforce(cardId: string, succeeded: boolean) {
    try {
      const res = await reinforceCards([cardId], succeeded);
      setState(res.state);
      setStatusBanner(
        `CARD ${cardId} ${succeeded ? "REINFORCED (+WIN)" : "DECAYED (-FAIL)"}`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusBanner(`REINFORCE ERROR // ${msg}`);
    }
  }

  useEffect(() => {
    if (activeTab === "pack" && !compiledPack) {
      handleCompilePack();
    }
    if (activeTab === "moshpit" && !contrastResult) {
      handleRunContrast();
    }
  }, [activeTab]);

  const firedPhaseNames = useMemo(() => {
    return new Set((activeTrace?.phases || []).map((p) => p.name));
  }, [activeTrace]);

  return (
    <div className={scanlines ? "scanlines" : ""}>
      <div className="hazard-bar" />
      <div className="app-shell">
        {/* ── PUNK AMPLIFIER HEADER ───────────────────────────────────────── */}
        <header className="punk-header">
          <div className="brain-emblem-wrap" title="MercBot Melting Frontier Brain">
            <img
              src="/melting-brain.png"
              alt="MercBot Acid Brain Emblem"
              className="brain-emblem"
            />
            <div className="brain-tag">ACID CORE v0.1</div>
          </div>

          <div className="header-copy">
            <div className="sticker-row">
              <span className="punk-sticker sticker-acid">FRONTIER ONLY // NO POSERS</span>
              <span className="punk-sticker sticker-magenta">GEMINI 4 ARGON ARMED</span>
              <span className="punk-sticker sticker-yellow">OLLAMA CLOUD TITANS</span>
              <span className="punk-sticker sticker-purple">TAURI v2 + MERCURY HARNESS</span>
            </div>
            <h1 className="hero-title">MERCBOT // ACID-HARNESS RUNTIME</h1>
            <p className="hero-subtitle">
              Execute tasks exclusively with <strong>Frontier Teacher Models</strong> (
              <strong>Google Gemini 4 Argon</strong>, <strong>Ollama Cloud</strong> flagships,{" "}
              <strong>Claude Fable/Opus</strong>, <strong>GPT-5.6 Sol</strong>,{" "}
              <strong>Grok 4.7</strong>) — automatically distilling their operational cortex into
              the local <code>.mercury</code> SQLite vault.
            </p>
          </div>

          <div className="header-telemetry">
            <div className="stat-brick">
              <div className="stat-brick-label">FRONTIER ROSTER</div>
              <div className="stat-brick-value">{state?.models.length ?? 18}</div>
            </div>
            <div className="stat-brick magenta">
              <div className="stat-brick-label">OLLAMA CLOUD</div>
              <div className="stat-brick-value">
                {state?.models.filter((m) => m.is_ollama_cloud).length ?? 9}
              </div>
            </div>
            <div className="stat-brick">
              <div className="stat-brick-label">CAPTURED TRACES</div>
              <div className="stat-brick-value">{state?.stats.traces ?? 0}</div>
            </div>
            <div className="stat-brick magenta">
              <div className="stat-brick-label">DISTILLED CARDS</div>
              <div className="stat-brick-value">{state?.stats.cards ?? 0}</div>
            </div>
          </div>
        </header>

        {/* ── STATUS TICKER & RACK TABS ───────────────────────────────────── */}
        <div
          style={{
            background: "#06110a",
            border: "2px solid #39ff14",
            padding: "8px 14px",
            marginBottom: "16px",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            boxShadow: "3px 3px 0px #ff007f",
          }}
        >
          <span>
            <strong style={{ color: "#ff007f" }}>[TELEMETRY]</strong> {statusBanner}
          </span>
          <span style={{ color: "#9dff00" }}>
            ACTIVE ENGINE: <strong>{activeModelSpec?.name || selectedModelId}</strong>
          </span>
        </div>

        <nav className="rack-nav">
          <div className="rack-tabs">
            <button
              className={`rack-tab ${activeTab === "runtime" ? "active" : ""}`}
              onClick={() => setActiveTab("runtime")}
            >
              01 // AGENT RUNTIME STAGE
            </button>
            <button
              className={`rack-tab ${activeTab === "deck" ? "active" : ""}`}
              onClick={() => setActiveTab("deck")}
            >
              02 // DISTILLED CORTEX DECK ({state?.stats.cards ?? 0})
            </button>
            <button
              className={`rack-tab ${activeTab === "moshpit" ? "active" : ""}`}
              onClick={() => setActiveTab("moshpit")}
            >
              03 // CONTRAST MOSH PIT
            </button>
            <button
              className={`rack-tab ${activeTab === "pack" ? "active" : ""}`}
              onClick={() => setActiveTab("pack")}
            >
              04 // OPERATING PACK COMPILER
            </button>
          </div>

          <div className="rack-actions">
            <button
              className="punk-btn"
              onClick={() => setShowKeyVault((v) => !v)}
            >
              {showKeyVault ? "HIDE KEY VAULT" : "API KEYS & OLLAMA CLOUD"}
            </button>
            <button
              className="punk-btn"
              onClick={() => setScanlines((s) => !s)}
            >
              CRT: {scanlines ? "ON" : "OFF"}
            </button>
          </div>
        </nav>

        {/* ── OPTIONAL API KEY & OLLAMA CLOUD VAULT ───────────────────────── */}
        {showKeyVault && (
          <section
            className="zine-panel magenta-frame"
            style={{ marginBottom: "20px" }}
          >
            <div className="panel-header">
              <div className="panel-title">
                <span className="slash">//</span> PROVIDER CREDENTIALS & OLLAMA CLOUD ENDPOINT
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "#8ab896" }}>
                Leave blank to run deterministic local workspace trajectories; add keys for live REST calls
              </span>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: "12px",
              }}
            >
              {Object.entries(apiKeys).map(([key, val]) => (
                <div key={key}>
                  <label
                    style={{
                      display: "block",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "#9dff00",
                      marginBottom: "4px",
                    }}
                  >
                    {key}
                  </label>
                  <input
                    className="punk-input"
                    type={key.includes("KEY") ? "password" : "text"}
                    placeholder={key.includes("HOST") ? "https://ollama.com" : `Enter ${key}...`}
                    value={val}
                    onChange={(e) =>
                      setApiKeys((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── MAIN STAGE GRID ─────────────────────────────────────────────── */}
        <div className="stage-grid">
          {/* LEFT COLUMN: STRICTLY FRONTIER MODEL ROSTER */}
          <aside className="zine-panel">
            <div className="panel-header">
              <div className="panel-title">
                <span className="slash">//</span> FRONTIER ROSTER ONLY
              </div>
              <span className="punk-sticker sticker-acid" style={{ fontSize: "10px" }}>
                {filteredModels.length} MODELS
              </span>
            </div>

            <div className="provider-pills">
              {[
                { id: "all", label: "ALL FRONTIER" },
                { id: "google", label: "GOOGLE ARGON" },
                { id: "ollama_cloud", label: "OLLAMA CLOUD" },
                { id: "anthropic", label: "ANTHROPIC" },
                { id: "openai", label: "OPENAI" },
                { id: "xai", label: "XAI" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  className={`provider-pill ${selectedProvider === tab.id ? "active" : ""}`}
                  onClick={() => setSelectedProvider(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="model-roster-list">
              {filteredModels.map((model) => {
                const isSelected = model.id === selectedModelId;
                return (
                  <div
                    key={model.id}
                    className={`model-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedModelId(model.id)}
                  >
                    <div className="model-card-top">
                      <span className="model-name">{model.name}</span>
                      <span className={`provider-badge provider-${model.provider}`}>
                        {model.is_ollama_cloud ? "OLLAMA CLOUD" : model.provider_label}
                      </span>
                    </div>
                    <div className="model-slug">
                      id: {model.id} • {Math.round(model.context_window / 1000)}K ctx
                    </div>
                    <div className="model-tagline">{model.tagline}</div>
                    <div className="model-tags">
                      <span
                        className="micro-tag"
                        style={{ color: "#39ff14", borderColor: "#39ff14" }}
                      >
                        TIER: FRONTIER
                      </span>
                      {model.specialties.map((tag) => (
                        <span key={tag} className="micro-tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* FRONTIER BOUNCER / GATEKEEPER TEST */}
            <div className="gatekeeper-box">
              <div className="gatekeeper-title">
                FRONTIER GATEKEEPER // TEST MODEL TIER BOUNCER
              </div>
              <div className="gatekeeper-row">
                <input
                  className="punk-input"
                  value={bouncerInput}
                  onChange={(e) => setBouncerInput(e.target.value)}
                  placeholder="Try gpt-4o-mini or gemini-3.5-flash..."
                />
                <button className="punk-btn" onClick={handleTestGatekeeper}>
                  TEST
                </button>
              </div>
              {bouncerVerdict && (
                <div
                  style={{
                    marginTop: "8px",
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: bouncerVerdict.startsWith("BOUNCED") ? "#ff4da6" : "#39ff14",
                    fontWeight: 700,
                  }}
                >
                  {bouncerVerdict}
                </div>
              )}
            </div>
          </aside>

          {/* RIGHT COLUMN: ACTIVE RACK VIEW */}
          <main style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {activeTab === "runtime" && (
              <>
                {/* MISSION LAUNCHPAD */}
                <section className="zine-panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <span className="slash">//</span> MISSION DISPATCH —{" "}
                      {activeModelSpec?.name || selectedModelId}
                    </div>
                    <span
                      className={`provider-badge provider-${
                        activeModelSpec?.provider || "google"
                      }`}
                    >
                      {activeModelSpec?.provider_label || "Google Gemini"} • {selectedModelId}
                    </span>
                  </div>

                  <textarea
                    className="punk-textarea"
                    value={taskInput}
                    onChange={(e) => setTaskInput(e.target.value)}
                    placeholder="Describe the engineering mission for the Frontier Agent Runtime..."
                  />

                  <div className="preset-chips">
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "#8ab896",
                        alignSelf: "center",
                      }}
                    >
                      PRESETS:
                    </span>
                    {MISSION_PRESETS.map((preset) => (
                      <button
                        key={preset.label}
                        className="preset-chip"
                        onClick={() => setTaskInput(preset.task)}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>

                  <div className="launch-bar">
                    <div className="mode-selector">
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          color: "#8ab896",
                        }}
                      >
                        MODE:
                      </span>
                      {(["auto", "synth", "live"] as const).map((m) => (
                        <button
                          key={m}
                          className={`provider-pill ${execMode === m ? "active" : ""}`}
                          onClick={() => setExecMode(m)}
                        >
                          {m === "auto"
                            ? "AUTO (LIVE / SYNTH)"
                            : m === "synth"
                            ? "WORKSPACE SYNTH"
                            : "STRICT LIVE API"}
                        </button>
                      ))}
                    </div>

                    <button
                      className="punk-btn primary-ignite"
                      onClick={handleIgniteRun}
                      disabled={isRunning}
                    >
                      {isRunning
                        ? "EXECUTING FRONTIER LOOP..."
                        : `IGNITE ${selectedModelId.toUpperCase()}`}
                    </button>
                  </div>
                </section>

                {/* PHASE SEQUENCER & TRACE FEED */}
                {activeTrace && (
                  <section className="zine-panel magenta-frame">
                    <div className="panel-header">
                      <div className="panel-title">
                        <span className="slash">//</span> LIVE TRAJECTORY & PHASE SEQUENCER:{" "}
                        {activeTrace.model}
                      </div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <span className="micro-tag" style={{ color: "#9dff00" }}>
                          mode: {lastModeUsed}
                        </span>
                        {lastDurationMs > 0 && (
                          <span className="micro-tag">{lastDurationMs}ms</span>
                        )}
                        <span className="punk-sticker sticker-acid" style={{ fontSize: "10px" }}>
                          {activeTrace.outcome.status.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    {/* 5-STAGE FRONTIER PHASE SEQUENCER */}
                    <div className="phase-pipeline">
                      {[
                        { key: "explore", label: "01. EXPLORE", hint: "grep / glob" },
                        { key: "localize", label: "02. LOCALIZE", hint: "read site + test" },
                        { key: "recover", label: "03. RECOVER", hint: "pivot on error" },
                        { key: "edit", label: "04. EDIT", hint: "focused patch" },
                        { key: "verify", label: "05. VERIFY", hint: "re-run test" },
                      ].map((stage) => {
                        const fired = firedPhaseNames.has(stage.key);
                        const isRec = stage.key === "recover" && fired;
                        return (
                          <div
                            key={stage.key}
                            className={`phase-node ${
                              isRec ? "recover-fired" : fired ? "fired" : ""
                            }`}
                          >
                            <div className="phase-node-name">{stage.label}</div>
                            <div className="phase-node-tools">
                              {fired ? "ACTIVE // LOCKED" : stage.hint}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {recoveryNotes.length > 0 && (
                      <div
                        style={{
                          background: "rgba(255, 0, 127, 0.16)",
                          border: "2px solid #ff007f",
                          padding: "10px 14px",
                          marginBottom: "14px",
                          fontFamily: "var(--font-mono)",
                          fontSize: "12px",
                          color: "#ff4da6",
                        }}
                      >
                        <strong>[MERCURY MID-RUN RECOVERY INJECTION]</strong>{" "}
                        {recoveryNotes.join(" | ")}
                      </div>
                    )}

                    {/* TRACE EVENTS */}
                    <div className="trace-stream">
                      {activeTrace.events.map((ev, idx) => (
                        <div
                          key={idx}
                          className={`event-row event-${ev.type} ${
                            ev.is_error ? "event-error" : ""
                          }`}
                        >
                          <div className="event-meta">
                            <span>
                              STEP {idx + 1} // {ev.type.toUpperCase()}
                              {ev.tool_name ? ` (${ev.tool_name})` : ""}
                            </span>
                            <span>{ev.is_error ? "ERROR SIGNAL DETECTED" : "OK"}</span>
                          </div>
                          {ev.content && (
                            <div style={{ whiteSpace: "pre-wrap", color: "#ecfff0" }}>
                              {ev.content}
                            </div>
                          )}
                          {ev.tool_calls && ev.tool_calls.length > 0 && (
                            <div>
                              {ev.tool_calls.map((tc, tci) => (
                                <span key={tci} className="tool-call-badge">
                                  ⚡ {tc.name}({JSON.stringify(tc.arguments)})
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* DETERMINISTIC BEHAVIOR GRADER */}
                {activeTrace?.grade && (
                  <section className="zine-panel">
                    <div className="panel-header">
                      <div className="panel-title">
                        <span className="slash">//</span> DETERMINISTIC BEHAVIOR GRADE (NO LLM
                        JUDGE)
                      </div>
                      <span className="punk-sticker sticker-acid">
                        OVERALL: {Math.round(activeTrace.grade.score * 100)}%
                      </span>
                    </div>

                    <div className="grade-bars">
                      <div className="vu-card">
                        <div className="vu-header">
                          <span>COMBINED SCORE</span>
                          <strong style={{ color: "#39ff14" }}>
                            {Math.round(activeTrace.grade.score * 100)}%
                          </strong>
                        </div>
                        <div className="vu-track">
                          <div
                            className="vu-fill"
                            style={{ width: `${activeTrace.grade.score * 100}%` }}
                          />
                        </div>
                      </div>

                      <div className="vu-card">
                        <div className="vu-header">
                          <span>POLICY FLOOR</span>
                          <strong style={{ color: "#39ff14" }}>
                            {Math.round(activeTrace.grade.policy_score * 100)}%
                          </strong>
                        </div>
                        <div className="vu-track">
                          <div
                            className="vu-fill"
                            style={{ width: `${activeTrace.grade.policy_score * 100}%` }}
                          />
                        </div>
                      </div>

                      <div className="vu-card">
                        <div className="vu-header">
                          <span>COMPETENCE CEILING</span>
                          <strong style={{ color: "#ff4da6" }}>
                            {Math.round(activeTrace.grade.competence_score * 100)}%
                          </strong>
                        </div>
                        <div className="vu-track">
                          <div
                            className="vu-fill"
                            style={{ width: `${activeTrace.grade.competence_score * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="checks-grid">
                      {activeTrace.grade.checks.map((chk) => (
                        <div
                          key={chk.name}
                          className={`check-pill ${chk.passed ? "pass" : "fail"}`}
                        >
                          <span
                            style={{
                              color: chk.passed ? "#39ff14" : "#ff007f",
                              fontWeight: 800,
                            }}
                          >
                            {chk.passed ? "[PASS]" : "[FAIL]"}
                          </span>
                          <div>
                            <div style={{ color: "#ecfff0", fontWeight: 700 }}>
                              {chk.name}{" "}
                              <span style={{ color: "#8ab896", fontSize: "10px" }}>
                                ({chk.band})
                              </span>
                            </div>
                            {chk.detail && (
                              <div style={{ color: "#8ab896", fontSize: "10px" }}>
                                {chk.detail}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </>
            )}

            {/* ── TAB 02: DISTILLED OPERATIONAL CORTEX DECK ──────────────── */}
            {activeTab === "deck" && (
              <section className="zine-panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <span className="slash">//</span> DISTILLED OPERATIONAL CARDS (
                    {filteredCards.length})
                  </div>
                  <div className="provider-pills" style={{ marginBottom: 0 }}>
                    {[
                      "all",
                      "standing_order",
                      "playbook",
                      "decision",
                      "contrast",
                      "recovery",
                      "tool_policy",
                      "heuristic",
                      "anti_pattern",
                    ].map((kind) => (
                      <button
                        key={kind}
                        className={`provider-pill ${cardKindFilter === kind ? "active" : ""}`}
                        onClick={() => setCardKindFilter(kind)}
                      >
                        {kind.replace("_", " ")}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="cards-deck-grid">
                  {filteredCards.map((card) => (
                    <div key={card.id} className={`op-card kind-${card.kind}`}>
                      <div className="op-card-header">
                        <span className={`kind-stamp ${card.kind}`}>
                          {card.kind.replace("_", " ")}
                        </span>
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "#9dff00",
                          }}
                        >
                          conf: {Math.round(card.effective_confidence * 100)}% •{" "}
                          {card.source_model}
                        </span>
                      </div>

                      <div className="op-card-title">{card.title}</div>
                      <div className="op-card-body">{card.procedure}</div>

                      {(card.chose || (card.rejected && card.rejected.length > 0)) && (
                        <div className="branch-box">
                          {card.chose && (
                            <div className="branch-chose">✓ CHOSE: {card.chose}</div>
                          )}
                          {card.rejected && card.rejected.length > 0 && (
                            <div className="branch-rejected">
                              ✗ REJECTED: {card.rejected.join("; ")}
                            </div>
                          )}
                        </div>
                      )}

                      <div className="op-card-footer">
                        <span>
                          uses: {card.uses} (W:{card.successes} / L:{card.failures})
                        </span>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button
                            className="preset-chip"
                            onClick={() => handleReinforce(card.id, true)}
                          >
                            +1 WIN
                          </button>
                          <button
                            className="preset-chip"
                            onClick={() => handleReinforce(card.id, false)}
                          >
                            -1 DECAY
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* ── TAB 03: CONTRAST MOSH PIT ──────────────────────────────── */}
            {activeTab === "moshpit" && (
              <section className="zine-panel magenta-frame">
                <div className="panel-header">
                  <div className="panel-title">
                    <span className="slash">//</span> CONTRASTIVE DISTILLATION MOSH PIT
                  </div>
                  <button className="punk-btn" onClick={handleRunContrast}>
                    PIT {selectedModelId.toUpperCase()} VS FAILED STUDENT
                  </button>
                </div>

                <p
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "12px",
                    color: "#8ab896",
                    marginBottom: "16px",
                  }}
                >
                  Negative knowledge is the highest-signal operational transfer: contrast a
                  failed lesser-model run (<code>gpt-4o-mini</code> editing{" "}
                  <code>login.tsx</code> first) against your selected Frontier teacher (
                  <code>{selectedModelId}</code>) to mint explicit{" "}
                  <strong>CHOSE vs REJECTED</strong> cards.
                </p>

                {contrastResult && (
                  <>
                    <div className="grade-bars">
                      <div className="vu-card">
                        <div className="vu-header">
                          <span>STUDENT BEFORE (GPT-4O-MINI)</span>
                          <strong style={{ color: "#ff4da6" }}>
                            {Math.round(contrastResult.delta.before.score * 100)}%
                          </strong>
                        </div>
                        <div className="vu-track">
                          <div
                            className="vu-fill"
                            style={{
                              width: `${contrastResult.delta.before.score * 100}%`,
                            }}
                          />
                        </div>
                      </div>

                      <div className="vu-card">
                        <div className="vu-header">
                          <span>TEACHER ({selectedModelId})</span>
                          <strong style={{ color: "#39ff14" }}>
                            {Math.round(contrastResult.delta.after.score * 100)}%
                          </strong>
                        </div>
                        <div className="vu-track">
                          <div
                            className="vu-fill"
                            style={{
                              width: `${contrastResult.delta.after.score * 100}%`,
                            }}
                          />
                        </div>
                      </div>

                      <div className="vu-card">
                        <div className="vu-header">
                          <span>OPERATIONAL DELTA</span>
                          <strong style={{ color: "#f5ff00" }}>
                            +{Math.round(contrastResult.delta.score_delta * 100)}%
                          </strong>
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "#39ff14",
                          }}
                        >
                          Newly passed: {contrastResult.delta.newly_passed.join(", ")}
                        </div>
                      </div>
                    </div>

                    <div className="cards-deck-grid">
                      {contrastResult.contrast_cards.slice(0, 6).map((card) => (
                        <div key={card.id} className={`op-card kind-${card.kind}`}>
                          <div className="op-card-header">
                            <span className={`kind-stamp ${card.kind}`}>
                              {card.kind.replace("_", " ")}
                            </span>
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "11px",
                                color: "#9dff00",
                              }}
                            >
                              {card.source_model}
                            </span>
                          </div>
                          <div className="op-card-title">{card.title}</div>
                          <div className="op-card-body">{card.procedure}</div>
                          {(card.chose || card.rejected.length > 0) && (
                            <div className="branch-box">
                              {card.chose && (
                                <div className="branch-chose">✓ CHOSE: {card.chose}</div>
                              )}
                              {card.rejected.length > 0 && (
                                <div className="branch-rejected">
                                  ✗ REJECTED: {card.rejected.join("; ")}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </section>
            )}

            {/* ── TAB 04: OPERATING PACK COMPILER ────────────────────────── */}
            {activeTab === "pack" && (
              <section className="zine-panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <span className="slash">//</span> FRONTIER OPERATING PACK COMPILER
                  </div>
                  <div className="provider-pills" style={{ marginBottom: 0 }}>
                    {(["markdown", "cursor", "dpo", "sft"] as const).map((fmt) => (
                      <button
                        key={fmt}
                        className={`provider-pill ${packFormat === fmt ? "active" : ""}`}
                        onClick={() => setPackFormat(fmt)}
                      >
                        {fmt === "cursor" ? ".cursor/rules/mercury.mdc" : fmt.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr auto",
                    gap: "10px",
                    marginBottom: "14px",
                  }}
                >
                  <input
                    className="punk-input"
                    value={packTask}
                    onChange={(e) => setPackTask(e.target.value)}
                    placeholder="Upcoming task..."
                  />
                  <input
                    className="punk-input"
                    value={packStudentModel}
                    onChange={(e) => setPackStudentModel(e.target.value)}
                    placeholder="Target student model (e.g. gpt-4o-mini)"
                  />
                  <input
                    className="punk-input"
                    value={packErrorSig}
                    onChange={(e) => setPackErrorSig(e.target.value)}
                    placeholder="Optional error signature..."
                  />
                  <button className="punk-btn" onClick={handleCompilePack}>
                    COMPILE PACK
                  </button>
                </div>

                {compiledPack && (
                  <pre className="code-preview">
                    {packFormat === "markdown"
                      ? compiledPack.markdown
                      : packFormat === "cursor"
                      ? compiledPack.cursor_rule
                      : packFormat === "dpo"
                      ? JSON.stringify(compiledPack.dpo, null, 2)
                      : JSON.stringify(compiledPack.sft, null, 2)}
                  </pre>
                )}
              </section>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
