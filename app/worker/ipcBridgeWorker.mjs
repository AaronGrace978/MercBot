/**
 * Asynchronous IPC Child Worker (`child_process.fork` target).
 * Moves the Python execution bridge completely out of the main desktop UI thread
 * and streams bit-by-bit chunk events (`mercury:stream`) back to the parent process.
 */
import fs from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..");

function resolvePythonLauncher() {
  const winVenv = path.join(repoRoot, ".venv", "Scripts", "python.exe");
  if (fs.existsSync(winVenv)) {
    return { cmd: winVenv, prefixArgs: [] };
  }
  const unixVenv = path.join(repoRoot, ".venv", "bin", "python");
  if (fs.existsSync(unixVenv)) {
    return { cmd: unixVenv, prefixArgs: [] };
  }
  return { cmd: "uv", prefixArgs: ["run", "python"] };
}

function runPythonBridge(action, payload, reqId) {
  const payloadStr = JSON.stringify(payload ?? {});
  const { cmd, prefixArgs } = resolvePythonLauncher();
  const args = [
    ...prefixArgs,
    "-m",
    "mercury",
    "bridge",
    action,
    "--payload",
    payloadStr,
    "--stream",
  ];

  const child = spawn(cmd, args, {
    cwd: repoRoot,
    stdio: ["ignore", "pipe", "pipe"],
  });

  const rl = readline.createInterface({ input: child.stdout });
  let finalResult = null;
  let stderrBuf = "";

  child.stderr.on("data", (chunk) => {
    stderrBuf += chunk.toString();
  });

  rl.on("line", (line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed && parsed.stream_chunk) {
        if (process.send) {
          process.send({
            type: "stream_chunk",
            id: reqId,
            chunk: parsed.stream_chunk,
          });
        }
        return;
      }
      finalResult = parsed;
    } catch {
      // Non-JSON diagnostic line
    }
  });

  child.on("close", (code) => {
    if (!process.send) return;
    if (code === 0 && finalResult !== null) {
      process.send({ type: "response", id: reqId, ok: true, result: finalResult });
    } else {
      process.send({
        type: "response",
        id: reqId,
        ok: false,
        error: stderrBuf || `Python bridge exited with code ${code}`,
      });
    }
  });
}

process.on("message", (msg) => {
  if (!msg || typeof msg !== "object") return;
  const { id, action, payload } = msg;
  if (!action) return;
  runPythonBridge(action, payload, id);
});
