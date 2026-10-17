/**
 * Parent-side Asynchronous IPC Worker Delegator (`child_process.fork`).
 * Delegates Python bridge calls to a forked background Node worker process
 * so the main UI / host thread never blocks on scaffolding or model execution.
 */
import { fork } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKER_SCRIPT = path.join(__dirname, "ipcBridgeWorker.mjs");

export class AsyncPythonBridgeDelegator {
  constructor() {
    this.worker = null;
    this.nextId = 1;
    this.pending = new Map();
    this.streamListeners = new Set();
  }

  ensureWorker() {
    if (this.worker && !this.worker.killed) {
      return this.worker;
    }
    this.worker = fork(WORKER_SCRIPT, [], {
      stdio: ["pipe", "pipe", "pipe", "ipc"],
    });

    this.worker.on("message", (msg) => {
      if (!msg || typeof msg !== "object") return;
      if (msg.type === "stream_chunk") {
        const entry = this.pending.get(msg.id);
        if (entry?.onChunk) {
          entry.onChunk(msg.chunk);
        }
        for (const listener of this.streamListeners) {
          listener(msg.chunk);
        }
        return;
      }
      if (msg.type === "response") {
        const entry = this.pending.get(msg.id);
        if (!entry) return;
        this.pending.delete(msg.id);
        if (msg.ok) {
          entry.resolve(msg.result);
        } else {
          entry.reject(new Error(msg.error || "IPC worker error"));
        }
      }
    });

    this.worker.on("exit", (code) => {
      for (const [, entry] of this.pending.entries()) {
        entry.reject(new Error(`IPC bridge worker exited unexpectedly (${code})`));
      }
      this.pending.clear();
      this.worker = null;
    });

    return this.worker;
  }

  onStreamChunk(listener) {
    this.streamListeners.add(listener);
    return () => this.streamListeners.delete(listener);
  }

  dispatch(action, payload = {}, onChunk = null) {
    const worker = this.ensureWorker();
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, onChunk });
      worker.send({ id, action, payload });
    });
  }

  shutdown() {
    if (this.worker) {
      this.worker.kill();
      this.worker = null;
    }
  }
}
