#!/usr/bin/env bash
# ============================================================
#  MercBot // Mercury Harness — product launcher
# ------------------------------------------------------------
#   ./mercury.sh            interactive menu
#   ./mercury.sh build      build & verify an app from prompt/template
#   ./mercury.sh launch     launch a built app from workspaces/
#   ./mercury.sh templates  list application build templates
#   ./mercury.sh run        run the Frontier Agent Runtime on a task
#   ./mercury.sh models     list Frontier models (Gemini Argon, Ollama Cloud)
#   ./mercury.sh serve      start the MercBot HTTP bridge server
#   ./mercury.sh demo       frontier -> lesser flywheel demo
#   ./mercury.sh status     knowledge-store stats
#   ./mercury.sh pack --task "Fix the redirect bug"
#   ./mercury.sh capture path/to/trace.json
#   ./mercury.sh test       run the pytest suite
#   ./mercury.sh doctor     environment check
#   ./mercury.sh version    print installed version
#
# Bootstraps .venv, installs the package (editable) if needed,
# then forwards everything to the `mercury` CLI.
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv"
PYBIN="$VENV/bin/python"
STORE="$ROOT/.mercury"

C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
say() { printf '%s[mercury]%s %s\n' "$C_CYAN" "$C_OFF" "$*"; }
ok()  { printf '%s[ok]%s %s\n' "$C_GREEN" "$C_OFF" "$*"; }
err() { printf '%s[err]%s %s\n' "$C_RED" "$C_OFF" "$*" >&2; }

banner() {
  printf '%s' "$C_CYAN"
  cat <<'EOF'
   __  __
  |  \/  | ___ _ __ ___ _   _ _ __ _   _
  | |\/| |/ _ \ '__/ __| | | | '__| | | |
  | |  | |  __/ | | (__| |_| | |  | |_| |
  |_|  |_|\___|_|  \___|\__,_|_|   \__, |
                                  |___/  HARNESS
EOF
  printf '%s' "$C_OFF"
}

bootstrap() {
  if [[ ! -x "$PYBIN" ]]; then
    say "creating .venv ..."
    command -v python3 >/dev/null 2>&1 || { err "python3 (3.10+) not found"; exit 1; }
    python3 -m venv "$VENV"
    ok "created .venv"
  fi
  local marker="$VENV/.mercury-installed"
  if [[ ! -f "$marker" || pyproject.toml -nt "$marker" || runtime/pyproject.toml -nt "$marker" || forge/pyproject.toml -nt "$marker" ]]; then
    say "installing mercury-harness + mercury-runtime + mercury-forge (editable) + dev deps ..."
    "$PYBIN" -m pip install --quiet --upgrade pip
    "$PYBIN" -m pip install --quiet -e ".[dev]" -e ./runtime -e ./forge
    touch "$marker"
    ok "install complete"
  fi
}

run_mercury() { "$PYBIN" -m mercury --store "$STORE" "$@"; }

cmd_demo()   { say "launching frontier -> lesser flywheel demo ..."; echo; run_mercury demo; }
cmd_status() { say "knowledge store status:"; echo; run_mercury status; }
cmd_test()   { say "running test suite ..."; echo; "$PYBIN" -m pytest; }
cmd_shell()  { say "venv python REPL (mercury importable), Ctrl-D to exit"; "$PYBIN"; }

cmd_version() {
  local v
  v="$("$PYBIN" -c 'import importlib.metadata as m; print(m.version("mercury-harness"))' 2>/dev/null || echo unknown)"
  printf 'mercury-harness %s%s%s\n' "$C_GREEN" "$v" "$C_OFF"
}

cmd_doctor() {
  say "environment check"
  printf '  python : %s\n' "$("$PYBIN" --version 2>&1)"
  printf '  version: %s\n' "$("$PYBIN" -c 'import importlib.metadata as m; print(m.version("mercury-harness"))' 2>/dev/null || echo unknown)"
  printf '  module : %s\n' "$("$PYBIN" -c 'import mercury,pathlib;print(pathlib.Path(mercury.__file__).resolve())' 2>&1)"
  printf '  store  : %s\n' "$STORE"
  echo
  run_mercury status
}

usage() {
  banner
  cat <<'EOF'
Mercury Harness — launcher

Usage: ./mercury.sh [command] [args...]

Product commands:
  build --prompt "..."   Forge, verify, and optionally --launch an application
  launch [app-slug]      Launch a forged application in a window (or --folder)
  templates              List Application Forge build templates
  run --task "..."       Run the Frontier Agent Runtime (Gemini 4 Argon / Ollama Cloud)
  models                 List strictly-frontier teacher models
  serve                  Start the local MercBot HTTP bridge server (port 8765)
  demo                   Run the built-in frontier -> lesser flywheel demo
  status                 Show knowledge-store statistics
  pack --task "..."      Print a Frontier Operating Pack for a lesser-model task
  capture <trace.json>   Ingest a frontier/other agent trace
  contrast <s> <t>       Distill divergence: failed student vs successful teacher
  grade <trace.json>     Deterministically grade how a trace operated
  distill                Re-distill every stored trace into operational cards
  init                   Create an empty knowledge store

Launcher commands:
  test                   Run the pytest suite
  doctor                 Environment check
  version                Print installed version
  shell                  Python REPL with mercury importable
  help                   This screen

With no command, an interactive menu opens.
EOF
}

menu() {
  banner
  echo "What do you want to launch?"
  echo
  echo "  1) build      tell MercBot what to build (and launch it!)"
  echo "  2) launch     launch a built application from workspaces/"
  echo "  3) templates  list ready-to-build application templates"
  echo "  4) run        run the Frontier Agent Runtime on a mission"
  echo "  5) models     list Frontier models (Gemini 4 Argon, Ollama Cloud)"
  echo "  6) demo       frontier -> lesser flywheel on fixture traces"
  echo "  7) status     knowledge-store statistics"
  echo "  8) pack       print a Frontier Operating Pack for a task"
  echo "  9) test       run the pytest suite"
  echo "  0) doctor     environment check"
  echo "  q) quit"
  echo
  read -r -p "> " choice
  case "$choice" in
    1|build)
      read -r -p "What should MercBot build? (e.g. 'Acid 303 synth' or 'Cyber Kanban'): " prompt
      read -r -p "Project name (optional): " pname
      run_mercury build --template auto --name "$pname" --prompt "$prompt" --launch
      ;;
    2|launch)
      read -r -p "App slug in workspaces/ (leave blank for latest): " slug
      run_mercury launch $slug
      ;;
    3|templates) run_mercury templates ;;
    4|run)
      read -r -p "Mission / task for Frontier Agent: " task
      run_mercury run --task "$task"
      ;;
    5|models)    run_mercury models ;;
    6|demo)      cmd_demo ;;
    7|status)    cmd_status ;;
    8|pack)      read -r -p "Task description: " task; run_mercury pack --task "$task" ;;
    9|test)      cmd_test ;;
    0|doctor)    cmd_doctor ;;
    q|quit|"")   ok "later." ;;
    *)           err "unknown choice: $choice"; exit 2 ;;
  esac
}

bootstrap
cmd="${1:-}"
case "$cmd" in
  "")             menu ;;
  help|-h|--help) usage ;;
  demo)           shift; cmd_demo "$@" ;;
  status)         shift; cmd_status "$@" ;;
  test)           shift; cmd_test "$@" ;;
  doctor)         shift; cmd_doctor "$@" ;;
  version|-v|--version) cmd_version ;;
  shell)          shift; cmd_shell "$@" ;;
  *)              run_mercury "$@" ;;
esac
