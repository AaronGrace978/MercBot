import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FixedSizeList as VirtualList, ListChildComponentProps } from "react-window";
import {
  buildFromTemplate,
  compileOperatingPack,
  fetchMercuryState,
  launchBuiltApp,
  reinforceCards,
  runContrastSmackdown,
  runFrontierAgent,
  subscribeMercurySSE,
} from "./api";
import {
  AgentTrace,
  AppTemplate,
  BuiltAppArtifact,
  ContrastResponse,
  FrontierModelSpec,
  MercuryState,
  PackResponse,
  StreamChunkEvent,
} from "./types";

export interface VirtualTerminalLine {
  id: string;
  badge: string;
  kind: "user" | "assistant" | "tool" | "system" | "stream" | "error" | "spec";
  text: string;
}

const VirtualTerminalRow: React.FC<ListChildComponentProps<VirtualTerminalLine[]>> = ({
  index,
  style,
  data,
}) => {
  const row = data[index];
  if (!row) return null;
  const colorMap: Record<VirtualTerminalLine["kind"], string> = {
    user: "#f5ff00",
    assistant: "#39ff14",
    tool: "#9dff00",
    system: "#8ab896",
    stream: "#00ffa3",
    error: "#ff007f",
    spec: "#ff4da6",
  };
  return (
    <div
      style={{
        ...style,
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "0 12px",
        borderBottom: "1px solid rgba(57, 255, 20, 0.14)",
        fontFamily: "var(--font-mono)",
        fontSize: "12px",
        background:
          row.kind === "error"
            ? "rgba(255, 0, 127, 0.12)"
            : index % 2 === 0
            ? "rgba(6, 17, 10, 0.85)"
            : "rgba(10, 26, 15, 0.85)",
        overflow: "hidden",
        whiteSpace: "nowrap",
        textOverflow: "ellipsis",
      }}
      title={row.text}
    >
      <span
        style={{
          color: colorMap[row.kind],
          fontWeight: 800,
          minWidth: "130px",
          flexShrink: 0,
        }}
      >
        {row.badge}
      </span>
      <span
        style={{
          color: row.kind === "error" ? "#ff4da6" : "#ecfff0",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {row.text}
      </span>
    </div>
  );
};

const MISSION_PRESETS = [
  {
    label: "BUILD ACID 303 SYNTH",
    task: "Build an interactive Acid 303 Bassline Synthesizer & 16-Step Sequencer with WebAudio resonance filter and live oscilloscope.",
  },
  {
    label: "BUILD CYBER KANBAN",
    task: "Build a Cyber-Zine Incident Command Kanban board with BACKLOG, IN FLIGHT, and VERIFIED lanes.",
  },
  {
    label: "BUILD NEON VAULT API",
    task: "Build a Neon Vault REST API & SQLite storage service with full CRUD and tag filtering verification.",
  },
  {
    label: "AUTH SAMESITE LOOP",
    task: "Login keeps redirecting back to /login after a successful password check. Localize the cookie fault and verify.",
  },
  {
    label: "FLAKY BILLING PYTEST",
    task: "Fix the flaky test that fails with AssertionError in test_billing.py by freezing clock instead of mutating prod.",
  },
];

export default function App() {
  const [state, setState] = useState<MercuryState | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>("all");
  const [selectedModelId, setSelectedModelId] = useState<string>("gemini-4-argon-high");
  const [activeTab, setActiveTab] = useState<
    "runtime" | "forge" | "deck" | "pack" | "moshpit"
  >("runtime");
  const [scanlines, setScanlines] = useState<boolean>(true);
  const [showKeyVault, setShowKeyVault] = useState<boolean>(false);

  // App Forge / Build Templates state
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("auto");
  const [forgeProjectName, setForgeProjectName] = useState<string>("Acid Pulse 303");
  const [forgeCustomPrompt, setForgeCustomPrompt] = useState<string>(
    "Build an interactive TB-303 acid bassline synthesizer with resonance filter modulation, distortion drive, and 16-step sequencer."
  );
  const [isForging, setIsForging] = useState<boolean>(false);
  const [forgedApp, setForgedApp] = useState<BuiltAppArtifact | null>(null);
  const [selectedForgedFile, setSelectedForgedFile] = useState<string>("");
  const [stageViewMode, setStageViewMode] = useState<"live" | "code">("live");

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
  const [streamLines, setStreamLines] = useState<VirtualTerminalLine[]>([]);
  const virtualListRef = useRef<VirtualList>(null);

  const handleStreamChunk = useCallback((chunk: StreamChunkEvent) => {
    if (!chunk || chunk.type === "connected" || chunk.type === "complete") return;
    setStreamLines((prev) => {
      const nextId = `stream-${prev.length + 1}-${Date.now()}`;
      if (chunk.type === "token" && chunk.content) {
        return [
          ...prev,
          {
            id: nextId,
            badge: `[TOKEN S${chunk.step ?? 0}]`,
            kind: "stream",
            text: chunk.content.replace(/\s+/g, " ").trim() || chunk.content,
          },
        ];
      }
      if (chunk.type === "terminal_chunk" && chunk.content) {
        return [
          ...prev,
          {
            id: nextId,
            badge: `[${(chunk.tool_name || "TERM").toUpperCase()}]`,
            kind: chunk.is_error ? "error" : "tool",
            text: chunk.content,
          },
        ];
      }
      if (chunk.type === "spec_check") {
        return [
          ...prev,
          {
            id: nextId,
            badge: chunk.passed ? "[SPEC.MD PASS]" : "[SPEC.MD FAIL]",
            kind: "spec",
            text: chunk.summary || "SPEC.md architectural manifest verified",
          },
        ];
      }
      if (chunk.type === "trace_event") {
        const tcText =
          chunk.tool_calls && chunk.tool_calls.length > 0
            ? chunk.tool_calls.map((tc) => `${tc.name}(${JSON.stringify(tc.arguments)})`).join(", ")
            : chunk.content || "";
        return [
          ...prev,
          {
            id: nextId,
            badge: `[STEP ${chunk.step ?? 0} ${(chunk.event_type || "EVENT").toUpperCase()}]`,
            kind: chunk.is_error ? "error" : "assistant",
            text: tcText,
          },
        ];
      }
      return prev;
    });
  }, []);

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
        if (data.built_apps && data.built_apps.length > 0) {
          const latest = data.built_apps[0];
          setForgedApp(latest);
          setSelectedForgedFile(latest.files_written?.[0] || "");
        }
      })
      .catch((err) => {
        setStatusBanner(`BRIDGE WARNING: ${err.message}`);
      });

    const unsubscribeSSE = subscribeMercurySSE(handleStreamChunk);
    return () => {
      unsubscribeSSE();
    };
  }, [handleStreamChunk]);

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
    setStreamLines([]);
    setStatusBanner(`IGNITING FRONTIER AGENT // ${selectedModelId.toUpperCase()} ...`);
    try {
      const nonEmptyKeys = Object.fromEntries(
        Object.entries(apiKeys).filter(([_, v]) => v.trim().length > 0)
      );
      const res = await runFrontierAgent(
        {
          task: taskInput,
          model: selectedModelId,
          mode: execMode,
          api_keys: nonEmptyKeys,
        },
        handleStreamChunk
      );
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
      if (res.run.built_app) {
        setForgedApp(res.run.built_app);
        setSelectedForgedFile(res.run.built_app.files_written?.[0] || "");
        setStageViewMode("live");
        setStatusBanner(
          `APP FORGED & VERIFIED // ${res.run.built_app.project_name.toUpperCase()} -> ${res.run.built_app.output_dir} — READY TO LAUNCH BELOW`
        );
      } else {
        if (res.state.built_apps && res.state.built_apps.length > 0) {
          const refreshed =
            (forgedApp &&
              res.state.built_apps.find((a) => a.project_slug === forgedApp.project_slug)) ||
            res.state.built_apps[0];
          setForgedApp(refreshed);
        }
        setStatusBanner(
          `RUN COMPLETE // ${res.run.model.name.toUpperCase()} (${res.run.mode_used.toUpperCase()}) — GRADE ${Math.round(
            res.run.grade.score * 100
          )}% — DISTILLED ${res.run.distilled_cards.length} CARDS`
        );
      }
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

  const activeTemplate: AppTemplate | undefined = useMemo(() => {
    const list = state?.templates || [];
    if (selectedTemplateId === "auto") return undefined;
    return list.find((t) => t.id === selectedTemplateId) || list[0];
  }, [state, selectedTemplateId]);

  async function handleForgeApplication(options?: {
    launchExternal?: boolean;
    overridePrompt?: string;
    overrideName?: string;
    overrideTemplate?: string;
  }) {
    if (isForging) return;
    setIsForging(true);
    setStreamLines([]);
    const tplToUse = options?.overrideTemplate ?? selectedTemplateId;
    const promptToUse = options?.overridePrompt ?? forgeCustomPrompt;
    const nameToUse = options?.overrideName ?? forgeProjectName;
    setStatusBanner(
      `FORGING APPLICATION // '${(nameToUse || tplToUse).toUpperCase()}' WITH ${selectedModelId.toUpperCase()} ...`
    );
    try {
      const nonEmptyKeys = Object.fromEntries(
        Object.entries(apiKeys).filter(([_, v]) => v.trim().length > 0)
      );
      const res = await buildFromTemplate(
        {
          template_id: tplToUse,
          project_name: nameToUse,
          custom_prompt: promptToUse,
          model: selectedModelId,
          launch: Boolean(options?.launchExternal),
          api_keys: nonEmptyKeys,
        },
        handleStreamChunk
      );
      setState(res.state);
      setForgedApp(res.build);
      setStageViewMode("live");
      const firstFile = res.build.files_written[0] || "";
      setSelectedForgedFile(firstFile);
      const enriched =
        res.state.traces.find((t) => t.id === res.trace.id) || {
          ...res.trace,
          grade: res.grade,
          phases: [],
        };
      setActiveTrace(enriched);
      setStatusBanner(
        `APPLICATION FORGED // ${res.build.project_name.toUpperCase()} -> ${
          res.build.output_dir
        } (${res.build.verification_passed ? "SPEC.MD + VERIFIED PASS" : "CHECK OUTPUT"})`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusBanner(`FORGE ERROR // ${msg}`);
    } finally {
      setIsForging(false);
    }
  }

  async function handleLaunchApp(slug: string, target: "window" | "folder" = "window") {
    try {
      setStatusBanner(
        target === "folder"
          ? `OPENING WORKSPACE DIRECTORY // ${slug.toUpperCase()} ...`
          : `LAUNCHING APPLICATION IN OS WINDOW // ${slug.toUpperCase()} ...`
      );
      const res = await launchBuiltApp({ project_slug: slug, target });
      setState(res.state);
      const syncedApp = res.state.built_apps?.find((a) => a.project_slug === slug);
      if (syncedApp) {
        setForgedApp(syncedApp);
      }
      setStatusBanner(`LAUNCHED // ${res.launch.message.toUpperCase()}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setStatusBanner(`LAUNCH ERROR // ${msg}`);
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

  const virtualTerminalLines = useMemo<VirtualTerminalLine[]>(() => {
    const rows: VirtualTerminalLine[] = [];
    if (streamLines.length > 0) {
      rows.push(...streamLines);
    }
    if (activeTrace?.events) {
      activeTrace.events.forEach((ev, idx) => {
        const stepBadge = `STEP ${idx + 1} // ${ev.type.toUpperCase()}${
          ev.tool_name ? `(${ev.tool_name})` : ""
        }`;
        if (ev.tool_calls && ev.tool_calls.length > 0) {
          ev.tool_calls.forEach((tc, tci) => {
            rows.push({
              id: `ev-${idx}-tc-${tci}`,
              badge: stepBadge,
              kind: ev.is_error ? "error" : "tool",
              text: `[TOOL] ${tc.name}(${JSON.stringify(tc.arguments)})`,
            });
          });
        }
        if (ev.content) {
          const contentLines = ev.content.split(/\r?\n/).filter((l) => l.trim().length > 0);
          contentLines.forEach((line, li) => {
            rows.push({
              id: `ev-${idx}-ln-${li}`,
              badge: li === 0 ? stepBadge : `  ↳ LINE ${li + 1}`,
              kind: ev.is_error ? "error" : ev.type,
              text: line,
            });
          });
        }
      });
    }
    return rows;
  }, [streamLines, activeTrace]);

  useEffect(() => {
    if (virtualListRef.current && virtualTerminalLines.length > 0) {
      virtualListRef.current.scrollToItem(virtualTerminalLines.length - 1, "end");
    }
  }, [virtualTerminalLines.length]);

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
            <div className="brain-tag">ACID CORE v0.3</div>
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
              className={`rack-tab ${activeTab === "forge" ? "active" : ""}`}
              onClick={() => setActiveTab("forge")}
            >
              02 // APP FORGE & TEMPLATES ({state?.templates?.length ?? 5})
            </button>
            <button
              className={`rack-tab ${activeTab === "deck" ? "active" : ""}`}
              onClick={() => setActiveTab("deck")}
            >
              03 // DISTILLED CORTEX DECK ({state?.stats.cards ?? 0})
            </button>
            <button
              className={`rack-tab ${activeTab === "moshpit" ? "active" : ""}`}
              onClick={() => setActiveTab("moshpit")}
            >
              04 // CONTRAST MOSH PIT
            </button>
            <button
              className={`rack-tab ${activeTab === "pack" ? "active" : ""}`}
              onClick={() => setActiveTab("pack")}
            >
              05 // OPERATING PACK COMPILER
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

                    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                      <button
                        className="punk-btn acid-launch"
                        onClick={() =>
                          handleForgeApplication({
                            overrideTemplate: "auto",
                            overridePrompt: taskInput,
                            overrideName: "",
                          })
                        }
                        disabled={isForging || isRunning}
                      >
                        {isForging ? "FORGING APPLICATION..." : "FORGE & LAUNCH APP"}
                      </button>

                      <button
                        className="punk-btn primary-ignite"
                        onClick={handleIgniteRun}
                        disabled={isRunning || isForging}
                      >
                        {isRunning
                          ? "EXECUTING FRONTIER LOOP..."
                          : `IGNITE ${selectedModelId.toUpperCase()}`}
                      </button>
                    </div>
                  </div>
                </section>

                {/* ACTIVE FORGED APP LAUNCHER & LIVE STAGE ON TAB 01 */}
                {forgedApp && (
                  <section className="zine-panel">
                    <div className="panel-header">
                      <div className="panel-title">
                        <span className="slash">//</span> BUILT APPLICATION READY:{" "}
                        {forgedApp.project_name} ({forgedApp.project_slug})
                      </div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <span className="punk-sticker sticker-acid">
                          {forgedApp.verification_passed ? "VERIFIED PASS" : "BUILT"}
                        </span>
                        <span className="micro-tag" style={{ color: "#9dff00" }}>
                          {forgedApp.output_dir}
                        </span>
                      </div>
                    </div>

                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "10px",
                        marginBottom: "12px",
                      }}
                    >
                      <div className="provider-pills" style={{ marginBottom: 0 }}>
                        <button
                          className={`provider-pill ${stageViewMode === "live" ? "active" : ""}`}
                          onClick={() => setStageViewMode("live")}
                        >
                          LIVE INTERACTIVE STAGE
                        </button>
                        <button
                          className={`provider-pill ${stageViewMode === "code" ? "active" : ""}`}
                          onClick={() => setStageViewMode("code")}
                        >
                          SOURCE FILES ({forgedApp.files_written.length})
                        </button>
                      </div>

                      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                        <button
                          className="punk-btn acid-launch"
                          onClick={() => handleLaunchApp(forgedApp.project_slug, "window")}
                        >
                          LAUNCH IN OS WINDOW
                        </button>
                        <button
                          className="punk-btn yellow-volt"
                          onClick={() => handleLaunchApp(forgedApp.project_slug, "folder")}
                        >
                          OPEN WORKSPACE DIR
                        </button>
                        <button
                          className="punk-btn"
                          onClick={() => setActiveTab("forge")}
                        >
                          OPEN FULL APP FORGE
                        </button>
                      </div>
                    </div>

                    {stageViewMode === "live" && forgedApp.preview_html ? (
                      <div className="live-stage-frame">
                        <div className="live-stage-header">
                          <span>
                            <strong style={{ color: "#39ff14" }}>[LIVE STAGE]</strong>{" "}
                            {forgedApp.project_name} — {forgedApp.verification_output}
                          </span>
                          <span style={{ color: "#ff4da6" }}>
                            ENGINE: {forgedApp.model} // {forgedApp.files_written.join(", ")}
                          </span>
                        </div>
                        <iframe
                          key={`stage1-${forgedApp.project_slug}-${forgedApp.trace_id || ""}-${forgedApp.preview_html.length}`}
                          title={`Live Stage: ${forgedApp.project_name}`}
                          className="live-stage-iframe"
                          srcDoc={forgedApp.preview_html}
                          sandbox="allow-scripts allow-same-origin"
                        />
                      </div>
                    ) : (
                      <div>
                        <div className="provider-pills" style={{ marginBottom: "10px" }}>
                          {forgedApp.files_written.map((relPath) => (
                            <button
                              key={relPath}
                              className={`provider-pill ${
                                selectedForgedFile === relPath ? "active" : ""
                              }`}
                              onClick={() => setSelectedForgedFile(relPath)}
                            >
                              {relPath}
                            </button>
                          ))}
                        </div>
                        <pre className="code-preview" style={{ maxHeight: "360px" }}>
                          {forgedApp.file_contents[selectedForgedFile] ||
                            "// Select a file above to inspect its source"}
                        </pre>
                      </div>
                    )}
                  </section>
                )}

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

                    {/* VIRTUALIZED ACID-PUNK TERMINAL STAGE (react-window) */}
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "8px",
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "#9dff00",
                      }}
                    >
                      <span>
                        DOM VIRTUALIZATION ACTIVE (<code>react-window</code>) //{" "}
                        {virtualTerminalLines.length} LOG LINES BUFFERED (CONSTANT DOM MEMORY)
                      </span>
                      <span>
                        SSE CHUNK STREAM:{" "}
                        <strong style={{ color: "#39ff14" }}>
                          {streamLines.length} LIVE CHUNKS
                        </strong>
                      </span>
                    </div>

                    <div
                      className="trace-stream"
                      style={{
                        padding: 0,
                        border: "2px solid #39ff14",
                        background: "#050d08",
                      }}
                    >
                      <VirtualList
                        ref={virtualListRef}
                        height={320}
                        width="100%"
                        itemCount={virtualTerminalLines.length}
                        itemSize={30}
                        itemData={virtualTerminalLines}
                      >
                        {VirtualTerminalRow}
                      </VirtualList>
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

            {/* ── TAB 02: APP FORGE & BUILD TEMPLATES ────────────────────── */}
            {activeTab === "forge" && (
              <>
                {/* PANEL 1: PROMPT-TO-APP & BLUEPRINT FORGE CONSOLE */}
                <section className="zine-panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <span className="slash">//</span> TELL MERCBOT WHAT TO BUILD — APPLICATION FORGE
                    </div>
                    <span className="punk-sticker sticker-acid">
                      ENGINE: {activeModelSpec?.name || selectedModelId}
                    </span>
                  </div>

                  {/* Blueprint Mode Selector Pills */}
                  <div className="provider-pills" style={{ marginBottom: "14px" }}>
                    <button
                      className={`provider-pill ${selectedTemplateId === "auto" ? "active" : ""}`}
                      onClick={() => setSelectedTemplateId("auto")}
                    >
                      AUTO DETECT FROM PROMPT
                    </button>
                    {(state?.templates || []).map((tpl) => (
                      <button
                        key={tpl.id}
                        className={`provider-pill ${selectedTemplateId === tpl.id ? "active" : ""}`}
                        onClick={() => {
                          setSelectedTemplateId(tpl.id);
                          if (tpl.id === "custom-prompt-app") {
                            setForgeProjectName("");
                            setForgeCustomPrompt("");
                          } else {
                            setForgeProjectName(tpl.name);
                            setForgeCustomPrompt(tpl.tagline);
                          }
                        }}
                      >
                        {tpl.id.toUpperCase()}
                      </button>
                    ))}
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 2fr",
                      gap: "12px",
                      marginBottom: "12px",
                    }}
                  >
                    <div>
                      <label
                        style={{
                          display: "block",
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          color: "#9dff00",
                          marginBottom: "6px",
                        }}
                      >
                        PROJECT NAME (OPTIONAL — AUTO-NAMED IF BLANK)
                      </label>
                      <input
                        className="punk-input"
                        value={forgeProjectName}
                        onChange={(e) => setForgeProjectName(e.target.value)}
                        placeholder="e.g. Acid Pulse 303, Cyber Kanban, Neon Vault..."
                      />
                    </div>

                    <div>
                      <label
                        style={{
                          display: "block",
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          color: "#ff4da6",
                          marginBottom: "6px",
                        }}
                      >
                        SELECTED BLUEPRINT MODE
                      </label>
                      <div
                        className="punk-input"
                        style={{
                          color: "#ecfff0",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <span>
                          {selectedTemplateId === "auto"
                            ? "AUTO-DETECT BLUEPRINT FROM YOUR PROMPT BELOW"
                            : `${activeTemplate?.name} (${activeTemplate?.files.length} files)`}
                        </span>
                        <span style={{ color: "#f5ff00", fontSize: "11px" }}>
                          {activeTemplate ? activeTemplate.verify_command : "python verify_*.py"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <label
                    style={{
                      display: "block",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "#39ff14",
                      marginBottom: "6px",
                    }}
                  >
                    DESCRIBE WHAT YOU WANT MERCBOT TO BUILD (ARCHITECTURE, FEATURES, UI, OR TASK)
                  </label>
                  <textarea
                    className="punk-textarea"
                    value={forgeCustomPrompt}
                    onChange={(e) => setForgeCustomPrompt(e.target.value)}
                    placeholder="Tell MercBot what to build in plain English (e.g. 'Build a 303 acid bassline synthesizer with resonance filter', 'Build a cyberpunk incident Kanban board', 'Build a SQLite REST API vault', or any custom interactive app)..."
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
                      QUICK BUILD PROMPTS:
                    </span>
                    {[
                      {
                        label: "303 ACID SYNTH & SEQUENCER",
                        tpl: "acid-synth-web",
                        name: "Acid Pulse 303",
                        prompt:
                          "Build an interactive 16-step TB-303 acid bassline synthesizer with WebAudio sawtooth/square oscillator, resonant filter, distortion rack, and live oscilloscope.",
                      },
                      {
                        label: "CYBER KANBAN COMMAND BOARD",
                        tpl: "cyber-kanban-board",
                        name: "Cyber Incident Board",
                        prompt:
                          "Build a brutalist neon Kanban & incident command board with BACKLOG, IN FLIGHT, and VERIFIED lanes.",
                      },
                      {
                        label: "NEON VAULT SQLITE API",
                        tpl: "neon-vault-api",
                        name: "Neon Vault Service",
                        prompt:
                          "Build a zero-dependency Python REST microservice & SQLite storage engine with full CRUD and tag filtering.",
                      },
                      {
                        label: "CUSTOM TELEMETRY MATRIX STUDIO",
                        tpl: "custom-prompt-app",
                        name: "Argon Telemetry Matrix",
                        prompt:
                          "Build an interactive neural node matrix visualizer and command execution deck with real-time particle physics.",
                      },
                    ].map((item) => (
                      <button
                        key={item.label}
                        className="preset-chip"
                        onClick={() => {
                          setSelectedTemplateId(item.tpl);
                          setForgeProjectName(item.name);
                          setForgeCustomPrompt(item.prompt);
                        }}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>

                  <div className="launch-bar">
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "#8ab896",
                      }}
                    >
                      OUTPUT TARGET: <strong style={{ color: "#39ff14" }}>workspaces/&lt;slug&gt;/</strong>{" "}
                      • AUTO-RUNS PYTHON VERIFICATION SUITE & DISTILLS CARDS
                    </div>

                    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                      <button
                        className="punk-btn acid-launch"
                        onClick={() => handleForgeApplication({ launchExternal: true })}
                        disabled={isForging}
                      >
                        {isForging
                          ? "FORGING & LAUNCHING..."
                          : "FORGE + LAUNCH IN OS WINDOW"}
                      </button>

                      <button
                        className="punk-btn primary-ignite"
                        onClick={() => handleForgeApplication({ launchExternal: false })}
                        disabled={isForging}
                      >
                        {isForging
                          ? "FORGING APPLICATION..."
                          : `FORGE APPLICATION // ${selectedModelId.toUpperCase()}`}
                      </button>
                    </div>
                  </div>
                </section>

                {/* PANEL 2: LIVE APPLICATION RUNNER & LAUNCH DECK */}
                {forgedApp && (
                  <section className="zine-panel magenta-frame">
                    <div className="panel-header">
                      <div className="panel-title">
                        <span className="slash">//</span> LIVE APPLICATION STAGE & LAUNCHER:{" "}
                        {forgedApp.project_name}
                      </div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <span className="punk-sticker sticker-acid">
                          {forgedApp.verification_passed ? "VERIFIED PASS (100%)" : "BUILT"}
                        </span>
                        <span className="punk-sticker sticker-magenta">{forgedApp.model}</span>
                      </div>
                    </div>

                    {/* Telemetry VU Cards */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                        gap: "12px",
                        marginBottom: "14px",
                      }}
                    >
                      <div className="vu-card">
                        <div className="vu-header">
                          <span>FORGED WORKSPACE</span>
                          <strong style={{ color: "#39ff14" }}>{forgedApp.project_slug}</strong>
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "#ecfff0",
                            wordBreak: "break-all",
                          }}
                        >
                          {forgedApp.output_dir}
                        </div>
                      </div>

                      <div className="vu-card">
                        <div className="vu-header">
                          <span>VERIFICATION SUITE</span>
                          <strong
                            style={{
                              color: forgedApp.verification_passed ? "#39ff14" : "#ff007f",
                            }}
                          >
                            {forgedApp.verification_passed ? "PASS" : "CHECK"}
                          </strong>
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "#9dff00",
                          }}
                        >
                          {forgedApp.verification_output}
                        </div>
                      </div>

                      <div className="vu-card">
                        <div className="vu-header">
                          <span>GENERATED FILES</span>
                          <strong style={{ color: "#f5ff00" }}>
                            {forgedApp.files_written.length}
                          </strong>
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "#ecfff0",
                          }}
                        >
                          {forgedApp.files_written.join(", ")}
                        </div>
                      </div>
                    </div>

                    {/* Launch & View Mode Bar */}
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "10px",
                        marginBottom: "12px",
                      }}
                    >
                      <div className="provider-pills" style={{ marginBottom: 0 }}>
                        <button
                          className={`provider-pill ${stageViewMode === "live" ? "active" : ""}`}
                          onClick={() => setStageViewMode("live")}
                        >
                          VIEW: LIVE RUNNING APP
                        </button>
                        <button
                          className={`provider-pill ${stageViewMode === "code" ? "active" : ""}`}
                          onClick={() => setStageViewMode("code")}
                        >
                          VIEW: SOURCE CODE ({forgedApp.files_written.length} FILES)
                        </button>
                      </div>

                      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                        <button
                          className="punk-btn acid-launch"
                          onClick={() => handleLaunchApp(forgedApp.project_slug, "window")}
                        >
                          LAUNCH IN OS WINDOW
                        </button>
                        <button
                          className="punk-btn yellow-volt"
                          onClick={() => handleLaunchApp(forgedApp.project_slug, "folder")}
                        >
                          OPEN WORKSPACE DIR
                        </button>
                      </div>
                    </div>

                    {stageViewMode === "live" && forgedApp.preview_html ? (
                      <div className="live-stage-frame">
                        <div className="live-stage-header">
                          <span>
                            <strong style={{ color: "#39ff14" }}>[INTERACTIVE STAGE]</strong>{" "}
                            {forgedApp.project_name} ({forgedApp.template_name})
                          </span>
                          <span style={{ color: "#9dff00" }}>
                            INTERACT DIRECTLY BELOW OR CLICK &ldquo;LAUNCH IN OS WINDOW&rdquo;
                          </span>
                        </div>
                        <iframe
                          key={`stage2-${forgedApp.project_slug}-${forgedApp.trace_id || ""}-${forgedApp.preview_html.length}`}
                          title={`MercBot Live App: ${forgedApp.project_name}`}
                          className="live-stage-iframe"
                          srcDoc={forgedApp.preview_html}
                          sandbox="allow-scripts allow-same-origin"
                        />
                      </div>
                    ) : (
                      <div>
                        <div className="provider-pills" style={{ marginBottom: "10px" }}>
                          {forgedApp.files_written.map((relPath) => (
                            <button
                              key={relPath}
                              className={`provider-pill ${
                                selectedForgedFile === relPath ? "active" : ""
                              }`}
                              onClick={() => setSelectedForgedFile(relPath)}
                            >
                              {relPath}
                            </button>
                          ))}
                        </div>
                        <pre className="code-preview" style={{ maxHeight: "460px" }}>
                          {forgedApp.file_contents[selectedForgedFile] ||
                            "// Select a forged file above to inspect its source code"}
                        </pre>
                      </div>
                    )}
                  </section>
                )}

                {/* PANEL 3: FORGED WORKSPACES LIBRARY & BLUEPRINT CATALOG */}
                <section className="zine-panel">
                  {state?.built_apps && state.built_apps.length > 0 && (
                    <div style={{ marginBottom: "22px" }}>
                      <div className="panel-header">
                        <div className="panel-title">
                          <span className="slash">//</span> FORGED WORKSPACES LIBRARY (
                          {state.built_apps.length} BUILT APPS IN WORKSPACES/)
                        </div>
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "#8ab896",
                          }}
                        >
                          CLICK ANY FORGED APP TO RUN IN STAGE OR LAUNCH IN OS WINDOW
                        </span>
                      </div>

                      <div className="built-apps-shelf">
                        {state.built_apps.map((app) => {
                          const isCurrent = forgedApp?.project_slug === app.project_slug;
                          return (
                            <div
                              key={app.project_slug}
                              className={`built-app-card ${isCurrent ? "active" : ""}`}
                            >
                              <div className="model-card-top">
                                <span className="model-name">{app.project_name}</span>
                                <span className="kind-stamp">
                                  {app.verification_passed ? "VERIFIED" : "BUILT"}
                                </span>
                              </div>
                              <div className="model-slug">
                                slug: {app.project_slug} • model: {app.model}
                              </div>
                              <div className="model-tagline">{app.output_dir}</div>
                              <div
                                style={{
                                  display: "flex",
                                  gap: "6px",
                                  flexWrap: "wrap",
                                  marginTop: "auto",
                                }}
                              >
                                <button
                                  className="punk-btn"
                                  style={{ padding: "5px 10px", fontSize: "11px" }}
                                  onClick={() => {
                                    setForgedApp(app);
                                    setSelectedForgedFile(app.files_written?.[0] || "");
                                    setStageViewMode("live");
                                  }}
                                >
                                  RUN IN STAGE
                                </button>
                                <button
                                  className="punk-btn acid-launch"
                                  style={{ padding: "5px 10px", fontSize: "11px" }}
                                  onClick={() => handleLaunchApp(app.project_slug, "window")}
                                >
                                  LAUNCH WINDOW
                                </button>
                                <button
                                  className="punk-btn yellow-volt"
                                  style={{ padding: "5px 10px", fontSize: "11px" }}
                                  onClick={() => handleLaunchApp(app.project_slug, "folder")}
                                >
                                  OPEN DIR
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="panel-header">
                    <div className="panel-title">
                      <span className="slash">//</span> APPLICATION BLUEPRINT CATALOG (
                      {state?.templates?.length ?? 6} STARTER ARCHITECTURES)
                    </div>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "#39ff14",
                      }}
                    >
                      SELECT A BLUEPRINT TO LOAD INTO THE FORGE CONSOLE ABOVE
                    </span>
                  </div>

                  <div className="forge-template-grid">
                    {(state?.templates || []).map((tpl) => {
                      const isSelected = tpl.id === selectedTemplateId;
                      return (
                        <div
                          key={tpl.id}
                          className={`forge-template-card ${isSelected ? "selected" : ""}`}
                          onClick={() => {
                            setSelectedTemplateId(tpl.id);
                            if (tpl.id === "custom-prompt-app") {
                              setForgeProjectName("");
                              setForgeCustomPrompt("");
                            } else {
                              setForgeProjectName(tpl.name);
                              setForgeCustomPrompt(tpl.tagline);
                            }
                          }}
                        >
                          <div className="model-card-top">
                            <span className="kind-stamp">{tpl.category}</span>
                            <span className="micro-tag" style={{ color: "#9dff00" }}>
                              {tpl.files.length} FILES
                            </span>
                          </div>
                          <div className="model-name" style={{ fontSize: "15px" }}>
                            {tpl.name}
                          </div>
                          <div className="model-slug">id: {tpl.id}</div>
                          <div className="model-tagline">{tpl.tagline}</div>
                          <div className="model-tags" style={{ marginTop: "auto" }}>
                            {tpl.stack.map((tech) => (
                              <span key={tech} className="micro-tag">
                                {tech}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              </>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
