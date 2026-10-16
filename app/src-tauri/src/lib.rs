use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| PathBuf::from("."))
}

fn call_mercury_bridge(action: &str, payload: &Value) -> Result<Value, String> {
    let root = repo_root();
    let payload_str = serde_json::to_string(payload).map_err(|e| e.to_string())?;

    // Prefer `uv run python -m mercury bridge <action> --payload <json>`
    // with fallback to `python -m mercury bridge <action> --payload <json>`
    let output = Command::new("uv")
        .args([
            "run",
            "python",
            "-m",
            "mercury",
            "bridge",
            action,
            "--payload",
            &payload_str,
        ])
        .current_dir(&root)
        .output()
        .or_else(|_| {
            Command::new("python")
                .args(["-m", "mercury", "bridge", action, "--payload", &payload_str])
                .current_dir(&root)
                .output()
        })
        .map_err(|e| format!("Failed to spawn Python Mercury bridge: {e}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Mercury bridge error: {stderr}"));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    serde_json::from_str(stdout.trim())
        .map_err(|e| format!("Invalid JSON from Mercury bridge: {e} ({stdout})"))
}

#[tauri::command]
fn mercury_state() -> Result<Value, String> {
    call_mercury_bridge("state", &serde_json::json!({}))
}

#[tauri::command]
fn mercury_run(payload: Value) -> Result<Value, String> {
    call_mercury_bridge("run", &payload)
}

#[tauri::command]
fn mercury_contrast(payload: Value) -> Result<Value, String> {
    call_mercury_bridge("contrast", &payload)
}

#[tauri::command]
fn mercury_pack(payload: Value) -> Result<Value, String> {
    call_mercury_bridge("pack", &payload)
}

#[tauri::command]
fn mercury_reinforce(payload: Value) -> Result<Value, String> {
    call_mercury_bridge("reinforce", &payload)
}

#[tauri::command]
fn mercury_seed() -> Result<Value, String> {
    call_mercury_bridge("seed", &serde_json::json!({}))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            mercury_state,
            mercury_run,
            mercury_contrast,
            mercury_pack,
            mercury_reinforce,
            mercury_seed
        ])
        .run(tauri::generate_context!())
        .expect("error while running MercBot Tauri application");
}
