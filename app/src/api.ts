import {
  BuildAppResponse,
  ContrastResponse,
  LaunchAppResponse,
  MercuryState,
  PackResponse,
  RunAgentResponse,
  StreamChunkEvent,
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
  payload?: Record<string, unknown>,
  onStreamChunk?: (chunk: StreamChunkEvent) => void
): Promise<T> {
  if (isTauriRuntime()) {
    const { invoke } = await import("@tauri-apps/api/core");
    let unlisten: (() => void) | null = null;
    if (onStreamChunk) {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<StreamChunkEvent>("mercury://stream", (event) => {
          onStreamChunk(event.payload);
        });
      } catch {
        // Event listener optional fallback
      }
    }
    try {
      return await invoke<T>(tauriCmd, payload ? { payload } : {});
    } finally {
      if (unlisten) {
        unlisten();
      }
    }
  }

  // When streaming is requested over HTTP, use SSE chunked event streaming
  if (onStreamChunk && method === "POST" && (httpPath === "/api/run" || httpPath === "/api/build")) {
    return callBackendSSE<T>(`${httpPath}/stream`, payload || {}, onStreamChunk);
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

async function callBackendSSE<T>(
  streamPath: string,
  payload: Record<string, unknown>,
  onStreamChunk: (chunk: StreamChunkEvent) => void
): Promise<T> {
  const res = await fetch(streamPath, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `SSE HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let finalResult: T | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawFrame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");

      const dataLines = rawFrame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim());

      if (dataLines.length === 0) continue;
      const jsonStr = dataLines.join("\n");
      try {
        const parsed = JSON.parse(jsonStr) as StreamChunkEvent;
        onStreamChunk(parsed);
        if (parsed.type === "complete" && parsed.result) {
          finalResult = parsed.result as T;
        } else if (parsed.type === "error") {
          throw new Error(parsed.error || "SSE stream error");
        }
      } catch (err) {
        if (err instanceof Error && err.message !== "Unexpected end of JSON input") {
          throw err;
        }
      }
    }
  }

  if (!finalResult) {
    throw new Error("SSE stream ended without a completion payload");
  }
  return finalResult;
}

export function subscribeMercurySSE(
  onChunk: (chunk: StreamChunkEvent) => void
): () => void {
  if (typeof window === "undefined" || isTauriRuntime() || typeof EventSource === "undefined") {
    return () => {};
  }
  const source = new EventSource("/api/stream");
  const handler = (ev: MessageEvent) => {
    try {
      const parsed = JSON.parse(ev.data) as StreamChunkEvent;
      onChunk(parsed);
    } catch {
      // Ignore heartbeat / malformed frames
    }
  };
  source.addEventListener("token", handler);
  source.addEventListener("terminal_chunk", handler);
  source.addEventListener("trace_event", handler);
  source.addEventListener("spec_check", handler);
  source.onmessage = handler;
  return () => {
    source.close();
  };
}

export function fetchMercuryState(): Promise<MercuryState> {
  return callBackend<MercuryState>("mercury_state", "/api/state", "GET");
}

export function runFrontierAgent(
  params: {
    task: string;
    model: string;
    mode: "auto" | "synth" | "live";
    api_keys?: Record<string, string>;
  },
  onStreamChunk?: (chunk: StreamChunkEvent) => void
): Promise<RunAgentResponse> {
  return callBackend<RunAgentResponse>("mercury_run", "/api/run", "POST", params, onStreamChunk);
}

export function buildFromTemplate(
  params: {
    template_id: string;
    project_name?: string;
    custom_prompt?: string;
    model: string;
    launch?: boolean;
  },
  onStreamChunk?: (chunk: StreamChunkEvent) => void
): Promise<BuildAppResponse> {
  return callBackend<BuildAppResponse>("mercury_build", "/api/build", "POST", params, onStreamChunk);
}

export function launchBuiltApp(params: {
  project_slug: string;
  target?: "window" | "folder";
}): Promise<LaunchAppResponse> {
  return callBackend<LaunchAppResponse>("mercury_launch", "/api/launch", "POST", params);
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
