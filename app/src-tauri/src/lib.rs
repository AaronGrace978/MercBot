use serde_json::Value;
use std::env;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{mpsc, Arc, Mutex};
use std::thread;
use tauri::{AppHandle, Emitter, State};

static NEXT_REQ_ID: AtomicU64 = AtomicU64::new(1);

fn repo_root() -> PathBuf {
    if let Ok(cwd) = env::current_dir() {
        if cwd.join("mercury").is_dir() {
            return cwd;
        }
        if let Some(parent) = cwd.parent() {
            if parent.join("mercury").is_dir() {
                return parent.to_path_buf();
            }
        }
    }
    if let Ok(exe) = env::current_exe() {
        let mut cur = exe.parent();
        while let Some(dir) = cur {
            if dir.join("mercury").is_dir() {
                return dir.to_path_buf();
            }
            cur = dir.parent();
        }
    }
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| PathBuf::from("."))
}

struct PersistentPythonProcess {
    _child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

impl PersistentPythonProcess {
    fn spawn(root: &PathBuf) -> Result<Self, String> {
        let mut child = Command::new("uv")
            .args(["run", "python", "-m", "mercury", "bridge-worker"])
            .current_dir(root)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .or_else(|_| {
                Command::new("python")
                    .args(["-m", "mercury", "bridge-worker"])
                    .current_dir(root)
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .stderr(Stdio::null())
                    .spawn()
            })
            .map_err(|e| format!("Failed to spawn persistent Python bridge-worker: {e}"))?;

        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "Failed to open stdin on Python bridge-worker".to_string())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "Failed to open stdout on Python bridge-worker".to_string())?;

        Ok(Self {
            _child: child,
            stdin,
            stdout: BufReader::new(stdout),
        })
    }

    fn execute(
        &mut self,
        action: &str,
        payload: &Value,
        app: Option<&AppHandle>,
    ) -> Result<Value, String> {
        let req_id = NEXT_REQ_ID.fetch_add(1, Ordering::SeqCst);
        let req = serde_json::json!({
            "id": req_id,
            "action": action,
            "payload": payload,
            "stream": true,
        });
        let mut line = serde_json::to_string(&req).map_err(|e| e.to_string())?;
        line.push('\n');
        self.stdin
            .write_all(line.as_bytes())
            .and_then(|_| self.stdin.flush())
            .map_err(|e| format!("Failed writing to Python bridge-worker: {e}"))?;

        let mut buf = String::new();
        loop {
            buf.clear();
            let bytes = self
                .stdout
                .read_line(&mut buf)
                .map_err(|e| format!("Failed reading from Python bridge-worker: {e}"))?;
            if bytes == 0 {
                return Err("Python bridge-worker closed stdout unexpectedly".to_string());
            }
            let trimmed = buf.trim();
            if trimmed.is_empty() {
                continue;
            }
            let msg: Value = serde_json::from_str(trimmed)
                .map_err(|e| format!("Invalid JSON from bridge-worker: {e} ({trimmed})"))?;

            if let Some(chunk) = msg.get("stream_chunk") {
                if let Some(handle) = app {
                    let _ = handle.emit("mercury://stream", chunk.clone());
                }
                continue;
            }

            if msg.get("ok").and_then(|v| v.as_bool()).unwrap_or(false) {
                return Ok(msg.get("result").cloned().unwrap_or(Value::Null));
            } else {
                let err_msg = msg
                    .get("error")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown bridge-worker error");
                return Err(err_msg.to_string());
            }
        }
    }
}

fn call_mercury_bridge_oneshot(
    action: &str,
    payload: &Value,
    app: Option<&AppHandle>,
) -> Result<Value, String> {
    let root = repo_root();
    let payload_str = serde_json::to_string(payload).map_err(|e| e.to_string())?;

    let mut child = Command::new("uv")
        .args([
            "run",
            "python",
            "-m",
            "mercury",
            "bridge",
            action,
            "--payload",
            &payload_str,
            "--stream",
        ])
        .current_dir(&root)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .or_else(|_| {
            Command::new("python")
                .args([
                    "-m",
                    "mercury",
                    "bridge",
                    action,
                    "--payload",
                    &payload_str,
                    "--stream",
                ])
                .current_dir(&root)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
        })
        .map_err(|e| format!("Failed to spawn Python Mercury bridge: {e}"))?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "Missing stdout pipe from Python bridge".to_string())?;
    let reader = BufReader::new(stdout);
    let mut final_json: Option<Value> = None;

    for line_res in reader.lines() {
        let line = line_res.map_err(|e| format!("Stdout read error: {e}"))?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Ok(parsed) = serde_json::from_str::<Value>(trimmed) {
            if let Some(chunk) = parsed.get("stream_chunk") {
                if let Some(handle) = app {
                    let _ = handle.emit("mercury://stream", chunk.clone());
                }
                continue;
            }
            final_json = Some(parsed);
        }
    }

    let status = child.wait().map_err(|e| e.to_string())?;
    if !status.success() {
        return Err(format!("Mercury bridge exited with status {status}"));
    }

    final_json.ok_or_else(|| "No JSON result emitted by Mercury bridge".to_string())
}

struct WorkerTask {
    action: String,
    payload: Value,
    app: Option<AppHandle>,
    reply_tx: mpsc::Sender<Result<Value, String>>,
}

/// Dedicated background command worker thread + persistent child process bridge
/// keeping all Python IPC execution completely off the main Tauri UI thread.
pub struct MercuryBackgroundBridge {
    sender: Mutex<mpsc::Sender<WorkerTask>>,
}

impl MercuryBackgroundBridge {
    pub fn new() -> Self {
        let (tx, rx) = mpsc::channel::<WorkerTask>();
        thread::Builder::new()
            .name("mercury-ipc-worker".to_string())
            .spawn(move || {
                let root = repo_root();
                let mut worker_proc: Option<PersistentPythonProcess> =
                    PersistentPythonProcess::spawn(&root).ok();

                while let Ok(task) = rx.recv() {
                    let app_ref = task.app.as_ref();
                    let result = if let Some(ref mut proc) = worker_proc {
                        match proc.execute(&task.action, &task.payload, app_ref) {
                            Ok(val) => Ok(val),
                            Err(_) => {
                                // Respawn persistent worker or fall back to oneshot streaming child process
                                worker_proc = PersistentPythonProcess::spawn(&root).ok();
                                call_mercury_bridge_oneshot(&task.action, &task.payload, app_ref)
                            }
                        }
                    } else {
                        worker_proc = PersistentPythonProcess::spawn(&root).ok();
                        call_mercury_bridge_oneshot(&task.action, &task.payload, app_ref)
                    };
                    let _ = task.reply_tx.send(result);
                }
            })
            .expect("Failed to spawn mercury-ipc-worker background thread");

        Self {
            sender: Mutex::new(tx),
        }
    }

    pub async fn dispatch(
        &self,
        action: &str,
        payload: Value,
        app: Option<AppHandle>,
    ) -> Result<Value, String> {
        let tx = self
            .sender
            .lock()
            .map_err(|e| format!("Worker mutex poisoned: {e}"))?
            .clone();
        let action_owned = action.to_string();

        tauri::async_runtime::spawn_blocking(move || {
            let (reply_tx, reply_rx) = mpsc::channel();
            tx.send(WorkerTask {
                action: action_owned.clone(),
                payload: payload.clone(),
                app: app.clone(),
                reply_tx,
            })
            .map_err(|_| "Mercury background worker channel closed".to_string())?;

            reply_rx
                .recv()
                .map_err(|e| format!("Mercury background worker recv error: {e}"))?
        })
        .await
        .map_err(|e| format!("Async task join error: {e}"))?
    }
}

#[tauri::command]
async fn mercury_state(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
) -> Result<Value, String> {
    bridge
        .dispatch("state", serde_json::json!({}), Some(app))
        .await
}

#[tauri::command]
async fn mercury_run(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
    payload: Value,
) -> Result<Value, String> {
    bridge.dispatch("run", payload, Some(app)).await
}

#[tauri::command]
async fn mercury_build(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
    payload: Value,
) -> Result<Value, String> {
    bridge.dispatch("build", payload, Some(app)).await
}

#[tauri::command]
async fn mercury_launch(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
    payload: Value,
) -> Result<Value, String> {
    bridge.dispatch("launch", payload, Some(app)).await
}

#[tauri::command]
async fn mercury_contrast(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
    payload: Value,
) -> Result<Value, String> {
    bridge.dispatch("contrast", payload, Some(app)).await
}

#[tauri::command]
async fn mercury_pack(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
    payload: Value,
) -> Result<Value, String> {
    bridge.dispatch("pack", payload, Some(app)).await
}

#[tauri::command]
async fn mercury_reinforce(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
    payload: Value,
) -> Result<Value, String> {
    bridge.dispatch("reinforce", payload, Some(app)).await
}

#[tauri::command]
async fn mercury_seed(
    app: AppHandle,
    bridge: State<'_, Arc<MercuryBackgroundBridge>>,
) -> Result<Value, String> {
    bridge
        .dispatch("seed", serde_json::json!({}), Some(app))
        .await
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let background_bridge = Arc::new(MercuryBackgroundBridge::new());
    tauri::Builder::default()
        .manage(background_bridge)
        .invoke_handler(tauri::generate_handler![
            mercury_state,
            mercury_run,
            mercury_build,
            mercury_launch,
            mercury_contrast,
            mercury_pack,
            mercury_reinforce,
            mercury_seed
        ])
        .run(tauri::generate_context!())
        .expect("error while running MercBot Tauri application");
}
