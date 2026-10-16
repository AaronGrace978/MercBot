import {
  ContrastResponse,
  MercuryState,
  PackResponse,
  RunAgentResponse,
} from "./types";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && Boolean(window.__TAURI_INTERNALS__);
}

async function callBackend<T>(
  tauriCmd: string,
  httpPath: string,
  method: "GET" | "POST" = "GET",
  payload?: Record<string, unknown>
): Promise<T> {
  if (isTauriRuntime()) {
    const { invoke } = await import("@tauri-apps/api/core");
    return invoke<T>(tauriCmd, payload ? { payload } : {});
  }

  const res = await fetch(httpPath, {
    method,
    headers: method === "POST" ? { "Content-Type": "application/json" } : undefined,
    body: method === "POST" ? JSON.stringify(payload || {}) : undefined,
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data as T;
}

export function fetchMercuryState(): Promise<MercuryState> {
  return callBackend<MercuryState>("mercury_state", "/api/state", "GET");
}

export function runFrontierAgent(params: {
  task: string;
  model: string;
  mode: "auto" | "synth" | "live";
  api_keys?: Record<string, string>;
}): Promise<RunAgentResponse> {
  return callBackend<RunAgentResponse>("mercury_run", "/api/run", "POST", params);
}

export function runContrastSmackdown(teacherModel: string): Promise<ContrastResponse> {
  return callBackend<ContrastResponse>("mercury_contrast", "/api/contrast", "POST", {
    teacher_model: teacherModel,
  });
}

export function compileOperatingPack(params: {
  task: string;
  model: string;
  error_signature?: string;
  token_budget?: number;
}): Promise<PackResponse> {
  return callBackend<PackResponse>("mercury_pack", "/api/pack", "POST", params);
}

export function reinforceCards(
  cardIds: string[],
  succeeded: boolean
): Promise<{ updated: number; state: MercuryState }> {
  return callBackend<{ updated: number; state: MercuryState }>(
    "mercury_reinforce",
    "/api/reinforce",
    "POST",
    { card_ids: cardIds, succeeded }
  );
}
