"""Prompt-driven application synthesizer & live frontier LLM app compiler for MercBot."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from mercury.providers import FrontierModelSpec

if TYPE_CHECKING:
    from mercury.templates import AppTemplate, AppTemplateFile

SHARED_ACID_CSS = """:root {
  --bg: #050c07;
  --panel: #09150d;
  --panel-alt: #040906;
  --acid: #39ff14;
  --lime: #9dff00;
  --magenta: #ff007f;
  --pink: #ff4da6;
  --yellow: #f5ff00;
  --border: #1d3f27;
  --text: #ecfff0;
  --muted: #8ab896;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Courier New', Consolas, monospace;
  padding: 16px;
  min-height: 100vh;
}
.shell { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  border: 3px solid var(--acid);
  box-shadow: 5px 5px 0 var(--magenta);
  padding: 14px 18px;
  background: var(--panel);
}
.badge {
  display: inline-block;
  background: var(--acid);
  color: #050c07;
  font-weight: 900;
  font-size: 11px;
  padding: 2px 8px;
  margin-bottom: 5px;
  letter-spacing: 0.5px;
}
h1 { color: var(--acid); font-size: 24px; text-shadow: 2px 2px 0 var(--magenta); }
.brief { color: var(--muted); font-size: 12px; margin-top: 3px; }
.stats { display: flex; gap: 10px; flex-wrap: wrap; }
.stat-box {
  border: 2px solid var(--acid);
  padding: 6px 12px;
  background: var(--panel-alt);
  text-align: right;
  min-width: 82px;
}
.stat-box.magenta { border-color: var(--magenta); }
.stat-box.yellow { border-color: var(--yellow); }
.stat-box span { display: block; font-size: 10px; color: var(--muted); }
.stat-box strong { font-size: 18px; color: var(--acid); }
.stat-box.magenta strong { color: var(--pink); }
.stat-box.yellow strong { color: var(--yellow); }
.panel {
  border: 2px solid var(--acid);
  box-shadow: 4px 4px 0 var(--magenta);
  background: var(--panel);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.panel-head {
  font-weight: 800;
  color: var(--yellow);
  border-bottom: 1px dashed var(--border);
  padding-bottom: 6px;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
input, textarea, select {
  background: var(--panel-alt);
  border: 2px solid var(--acid);
  color: var(--text);
  padding: 8px 10px;
  font-family: inherit;
  font-size: 13px;
  outline: none;
}
input:focus, textarea:focus, select:focus {
  border-color: var(--yellow);
  box-shadow: 0 0 8px rgba(57, 255, 20, 0.35);
}
button {
  background: var(--magenta);
  color: #fff;
  border: 2px solid var(--acid);
  padding: 7px 12px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--acid);
  transition: transform 0.08s ease;
}
button:hover { background: var(--acid); color: #050c07; }
button:active { transform: translate(1px, 1px); }
button.secondary { background: #061409; color: var(--acid); }
button.secondary:hover { background: var(--acid); color: #050c07; }
button.yellow-btn { background: var(--yellow); color: #050c07; }
.toolbar { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: var(--panel-alt);
  border: 1px solid var(--border);
  padding: 6px 10px;
  font-size: 11px;
  color: var(--lime);
}
"""


def detect_prompt_archetype(display_name: str, brief: str) -> str:
    """Classify the user's natural language prompt into a concrete application archetype."""
    combined = f"{display_name} {brief}".lower()

    if any(
        w in combined
        for w in (
            "notepad",
            "note pad",
            "notes",
            "note-taking",
            "note taking",
            "text editor",
            "markdown",
            "scratchpad",
            "journal",
            "diary",
            "memo",
            "word processor",
            "document editor",
            "code editor",
            "writer",
        )
    ) or re.search(r"\bnote\b|\beditor\b", combined):
        return "notepad"

    if any(
        w in combined
        for w in (
            "calculator",
            "calc",
            "scientific",
            "arithmetic",
            "unit converter",
            "math solver",
        )
    ):
        return "calculator"

    if any(
        w in combined
        for w in (
            "pomodoro",
            "stopwatch",
            "timer",
            "countdown",
            "alarm clock",
            "focus clock",
            "world clock",
        )
    ) or re.search(r"\bclock\b", combined):
        return "timer"

    if any(
        w in combined
        for w in (
            "snake",
            "arcade",
            "pong",
            "breakout",
            "brick",
            "tetris",
            "minesweeper",
            "tic-tac-toe",
            "flappy",
            "space invaders",
        )
    ) or re.search(r"\bgame\b", combined):
        return "game"

    if any(
        w in combined
        for w in (
            "paint",
            "drawing",
            "sketchpad",
            "sketch",
            "pixel art",
            "whiteboard",
            "doodle",
            "color picker",
        )
    ) or re.search(r"\bdraw\b|\bbrush\b", combined):
        return "paint"

    if any(
        w in combined
        for w in (
            "password",
            "json",
            "regex",
            "base64",
            "hash",
            "uuid",
            "jwt",
            "encoder",
            "decoder",
            "formatter",
        )
    ):
        return "devtools"

    # Marketing / product sites before WebGL so "generative UI landing page" is never a CRUD stub.
    if re.search(
        r"landing\s*pages?|web\s*sites?|web\s*pages?|home\s*pages?|homepages?|"
        r"marketing\s*(?:site|page)|product\s*page|pricing\s*page|splash\s*page|"
        r"one[- ]pagers?|generative\s*ui|\bgen(?:erative)?\s*ui\b|\bsaas\s*(?:landing|site|page)\b",
        combined,
    ) or re.search(r"\b(?:website|webpage|homepage|landing)\b", combined):
        return "landing_page"

    if re.search(
        r"\bdashboards?\b|admin\s*panels?|analytics\s*(?:dashboard|panel|console)|"
        r"kpi\s*(?:board|dashboard)|metrics\s*(?:dashboard|panel)",
        combined,
    ):
        return "dashboard"

    if any(
        w in combined
        for w in (
            "chat",
            "messenger",
            "chatbot",
            "ai assistant",
            "prompt console",
            "conversation",
        )
    ):
        return "chat"

    if any(
        w in combined
        for w in (
            "webgl",
            "three.js",
            "threejs",
            "3d",
            "shader",
            "visualizer",
            "icosahedron",
            "torus",
            "wireframe",
            "voxel",
            "dino",
            "mohawk",
            "hologram",
            "oscilloscope",
        )
    ):
        return "webgl_3d"

    if any(
        w in combined
        for w in (
            "interactive neural node matrix",
            "test custom-prompt-app",
        )
    ):
        return "telemetry"

    return "domain_studio"


def _build_notepad_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // FORGED BY {model_id}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT NOTEPAD STUDIO // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
      <div class="stats">
        <div class="stat-box"><span>NOTES</span><strong id="notesCount">1</strong></div>
        <div class="stat-box"><span>WORDS</span><strong id="wordCount">0</strong></div>
        <div class="stat-box magenta"><span>CHARS</span><strong id="charCount">0</strong></div>
        <div class="stat-box yellow"><span>LINES</span><strong id="lineCount">1</strong></div>
      </div>
    </header>

    <div class="notepad-grid">
      <aside class="panel sidebar">
        <div class="panel-head">
          <span>// NOTES VAULT</span>
          <button id="newNoteBtn">+ NEW NOTE</button>
        </div>
        <input id="searchNotes" placeholder="Search notes by title or text..." />
        <div id="notesList" class="notes-list"></div>
      </aside>

      <main class="panel editor-pane">
        <div class="panel-head">
          <span>// DOCUMENT EDITOR</span>
          <span id="saveStatus" style="color:#39ff14;">AUTO-SAVED</span>
        </div>

        <div class="title-row">
          <input id="noteTitleInput" class="title-input" placeholder="Note Title..." />
          <button id="togglePreviewBtn" class="secondary">SPLIT PREVIEW: OFF</button>
          <button id="toggleFindBtn" class="secondary">FIND / REPLACE</button>
        </div>

        <div class="toolbar">
          <button class="secondary" data-fmt="bold" title="Bold">B</button>
          <button class="secondary" data-fmt="italic" title="Italic">I</button>
          <button class="secondary" data-fmt="h1" title="Heading 1">H1</button>
          <button class="secondary" data-fmt="h2" title="Heading 2">H2</button>
          <button class="secondary" data-fmt="todo" title="Checklist item">[ ] TODO</button>
          <button class="secondary" data-fmt="bullet" title="Bullet list">• LIST</button>
          <button class="secondary" data-fmt="code" title="Code block">&lt;/&gt; CODE</button>
          <button class="secondary" id="insertTimeBtn" title="Insert Timestamp">+ TIMESTAMP</button>
          <button class="secondary" id="wrapToggleBtn" title="Toggle Word Wrap">WRAP: ON</button>
        </div>

        <div id="findBar" class="find-bar" style="display:none;">
          <input id="findInput" placeholder="Find text..." />
          <input id="replaceInput" placeholder="Replace with..." />
          <button id="replaceOneBtn" class="secondary">REPLACE</button>
          <button id="replaceAllBtn">REPLACE ALL</button>
        </div>

        <div class="editor-split" id="editorSplit">
          <div class="editor-box">
            <div id="lineGutter" class="line-gutter">1</div>
            <textarea id="noteEditor" spellcheck="false" placeholder="Start typing your note here..."></textarea>
          </div>
          <div id="markdownPreview" class="md-preview" style="display:none;"></div>
        </div>

        <div class="toolbar" style="justify-content: space-between; margin-top: 4px;">
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button id="downloadTxtBtn" class="yellow-btn">SAVE .TXT</button>
            <button id="downloadMdBtn" class="secondary">SAVE .MD</button>
            <button id="copyNoteBtn" class="secondary">COPY CLIPBOARD</button>
            <label class="file-label">
              IMPORT FILE
              <input type="file" id="importFileInput" accept=".txt,.md,.json,.py,.js,.log" style="display:none;" />
            </label>
          </div>
          <div style="display:flex; gap:6px;">
            <button id="clearNoteBtn" class="secondary">CLEAR</button>
            <button id="deleteNoteBtn">DELETE NOTE</button>
          </div>
        </div>

        <div class="status-bar">
          <span id="cursorPos">LN 1, COL 1</span>
          <span id="readingTime">~1 min read</span>
          <span>SHORTCUTS: CTRL+S (SAVE) • CTRL+B (BOLD) • TAB (INDENT)</span>
        </div>
      </main>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""

    css = (
        SHARED_ACID_CSS
        + """
.notepad-grid {
  display: grid;
  grid-template-columns: 270px 1fr;
  gap: 14px;
  min-height: 440px;
}
@media (max-width: 820px) { .notepad-grid { grid-template-columns: 1fr; } }
.notes-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 380px;
  overflow-y: auto;
}
.note-item {
  border: 1px solid var(--border);
  border-left: 4px solid var(--muted);
  background: var(--panel-alt);
  padding: 8px 10px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.note-item:hover { border-color: var(--acid); }
.note-item.active {
  border-color: var(--acid);
  border-left: 4px solid var(--acid);
  background: #0b2112;
  box-shadow: 2px 2px 0 var(--magenta);
}
.note-item-title { font-weight: 800; color: var(--acid); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.note-item-meta { font-size: 10px; color: var(--muted); display: flex; justify-content: space-between; }
.title-row { display: flex; gap: 8px; align-items: center; }
.title-input { flex: 1; font-size: 16px; font-weight: 800; color: var(--yellow); }
.find-bar { display: flex; gap: 6px; flex-wrap: wrap; background: var(--panel-alt); padding: 8px; border: 1px dashed var(--magenta); }
.editor-split { display: grid; grid-template-columns: 1fr; gap: 10px; flex: 1; min-height: 290px; }
.editor-split.split-active { grid-template-columns: 1fr 1fr; }
.editor-box {
  display: flex;
  border: 2px solid var(--acid);
  background: #030805;
  min-height: 290px;
  overflow: hidden;
}
.line-gutter {
  background: #07140b;
  color: var(--muted);
  padding: 10px 8px;
  text-align: right;
  user-select: none;
  font-size: 13px;
  line-height: 1.5;
  border-right: 1px solid var(--border);
  min-width: 38px;
  white-space: pre;
  overflow: hidden;
}
#noteEditor {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--text);
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  min-height: 290px;
}
#noteEditor:focus { box-shadow: none; }
.md-preview {
  border: 2px solid var(--magenta);
  background: #040a06;
  padding: 12px;
  overflow-y: auto;
  max-height: 360px;
  font-size: 13px;
  line-height: 1.5;
}
.md-preview h1, .md-preview h2, .md-preview h3 { color: var(--acid); margin: 8px 0 4px; }
.md-preview code { background: #0d2614; color: var(--yellow); padding: 1px 5px; }
.md-preview pre { background: #020603; border: 1px solid var(--border); padding: 8px; margin: 6px 0; overflow-x: auto; }
.file-label {
  background: #061409;
  color: var(--acid);
  border: 2px solid var(--acid);
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 2px 2px 0 var(--acid);
}
.file-label:hover { background: var(--acid); color: #050c07; }
"""
    )

    js = f"""const STORAGE_KEY = "mercbot_notepad_vault_v1";
const notesListEl = document.getElementById("notesList");
const searchInput = document.getElementById("searchNotes");
const titleInput = document.getElementById("noteTitleInput");
const editorEl = document.getElementById("noteEditor");
const gutterEl = document.getElementById("lineGutter");
const previewEl = document.getElementById("markdownPreview");
const editorSplitEl = document.getElementById("editorSplit");
const saveStatusEl = document.getElementById("saveStatus");
const cursorPosEl = document.getElementById("cursorPos");
const readingTimeEl = document.getElementById("readingTime");
const notesCountEl = document.getElementById("notesCount");
const wordCountEl = document.getElementById("wordCount");
const charCountEl = document.getElementById("charCount");
const lineCountEl = document.getElementById("lineCount");

let notes = [];
let activeId = null;
let splitPreview = false;
let wordWrap = true;

function defaultNotes() {{
  return [
    {{
      id: "note-1",
      title: "Welcome to {display_name}",
      content: "# {display_name}\\n\\nMission: {brief}\\n\\n## Quick Features\\n- Multi-note sidebar with instant search & auto-save\\n- Formatting toolbar (Bold, Italic, Headings, Checklists, Code)\\n- Find & Replace bar + Line numbers\\n- Export to `.txt` or `.md` and import local files\\n\\n[ ] Try typing or creating a new note!",
      updatedAt: new Date().toLocaleTimeString()
    }},
    {{
      id: "note-2",
      title: "Scratchpad & Todo List",
      content: "# Daily Scratchpad\\n\\n- [x] Launch {display_name} in Live Stage\\n- [ ] Test Find & Replace\\n- [ ] Export markdown notes",
      updatedAt: new Date().toLocaleTimeString()
    }}
  ];
}}

function loadNotes() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {{
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {{
        notes = parsed;
        activeId = notes[0].id;
        return;
      }}
    }}
  }} catch (e) {{}}
  notes = defaultNotes();
  activeId = notes[0].id;
}}

function persistNotes() {{
  try {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
  }} catch (e) {{}}
  saveStatusEl.textContent = "SAVED " + new Date().toLocaleTimeString();
}}

function getActiveNote() {{
  return notes.find(n => n.id === activeId) || notes[0];
}}

function renderMarkdown(md) {{
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.*)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.*)$/gm, "<h1>$1</h1>");
  html = html.replace(/\\*\\*(.+?)\\*\\*/g, "<strong>$1</strong>");
  html = html.replace(/\\*(.+?)\\*/g, "<em>$1</em>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/^- \\[x\\] (.*)$/gm, "<div style='color:#39ff14'>☑ $1</div>");
  html = html.replace(/^- \\[ \\] (.*)$/gm, "<div>☐ $1</div>");
  html = html.replace(/^- (.*)$/gm, "<div>• $1</div>");
  return html.replace(/\\n/g, "<br/>");
}}

function updateTelemetry() {{
  const text = editorEl.value || "";
  const lines = text.split("\\n");
  const words = text.trim() ? text.trim().split(/\\s+/).length : 0;
  notesCountEl.textContent = String(notes.length);
  wordCountEl.textContent = String(words);
  charCountEl.textContent = String(text.length);
  lineCountEl.textContent = String(lines.length);
  readingTimeEl.textContent = `~${{Math.max(1, Math.ceil(words / 200))}} min read`;

  gutterEl.textContent = Array.from({{ length: Math.max(1, lines.length) }}, (_, i) => i + 1).join("\\n");
  if (splitPreview) {{
    previewEl.innerHTML = renderMarkdown(text);
  }}
}}

function updateCursorPos() {{
  const pos = editorEl.selectionStart || 0;
  const upto = editorEl.value.slice(0, pos).split("\\n");
  const ln = upto.length;
  const col = upto[upto.length - 1].length + 1;
  cursorPosEl.textContent = `LN ${{ln}}, COL ${{col}}`;
}}

function renderSidebar() {{
  const q = (searchInput.value || "").toLowerCase().trim();
  notesListEl.innerHTML = "";
  const filtered = notes.filter(n =>
    !q || n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q)
  );
  filtered.forEach(note => {{
    const div = document.createElement("div");
    div.className = "note-item" + (note.id === activeId ? " active" : "");
    const words = note.content.trim() ? note.content.trim().split(/\\s+/).length : 0;
    div.innerHTML = `
      <div class="note-item-title">${{note.title || "Untitled Note"}}</div>
      <div class="note-item-meta">
        <span>${{words}} words</span>
        <span>${{note.updatedAt || ""}}</span>
      </div>
    `;
    div.addEventListener("click", () => {{
      activeId = note.id;
      loadActiveIntoEditor();
      renderSidebar();
    }});
    notesListEl.appendChild(div);
  }});
}}

function loadActiveIntoEditor() {{
  const note = getActiveNote();
  if (!note) return;
  titleInput.value = note.title;
  editorEl.value = note.content;
  updateTelemetry();
  updateCursorPos();
}}

function syncCurrentNote() {{
  const note = getActiveNote();
  if (!note) return;
  note.title = titleInput.value || "Untitled Note";
  note.content = editorEl.value;
  note.updatedAt = new Date().toLocaleTimeString();
  persistNotes();
  updateTelemetry();
  renderSidebar();
}}

titleInput.addEventListener("input", syncCurrentNote);
editorEl.addEventListener("input", syncCurrentNote);
editorEl.addEventListener("click", updateCursorPos);
editorEl.addEventListener("keyup", updateCursorPos);
editorEl.addEventListener("scroll", () => {{
  gutterEl.scrollTop = editorEl.scrollTop;
}});

editorEl.addEventListener("keydown", (e) => {{
  if (e.key === "Tab") {{
    e.preventDefault();
    const start = editorEl.selectionStart;
    const end = editorEl.selectionEnd;
    editorEl.value = editorEl.value.substring(0, start) + "  " + editorEl.value.substring(end);
    editorEl.selectionStart = editorEl.selectionEnd = start + 2;
    syncCurrentNote();
  }} else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {{
    e.preventDefault();
    persistNotes();
    saveStatusEl.textContent = "SNAPSHOT SAVED!";
  }} else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {{
    e.preventDefault();
    applyFormat("bold");
  }}
}});

searchInput.addEventListener("input", renderSidebar);

document.getElementById("newNoteBtn").addEventListener("click", () => {{
  const newNote = {{
    id: "note-" + Date.now(),
    title: "Note #" + (notes.length + 1),
    content: "# Note #" + (notes.length + 1) + "\\n\\n",
    updatedAt: new Date().toLocaleTimeString()
  }};
  notes.unshift(newNote);
  activeId = newNote.id;
  persistNotes();
  loadActiveIntoEditor();
  renderSidebar();
  editorEl.focus();
}});

document.getElementById("deleteNoteBtn").addEventListener("click", () => {{
  if (notes.length <= 1) {{
    editorEl.value = "";
    titleInput.value = "Untitled Note";
    syncCurrentNote();
    return;
  }}
  notes = notes.filter(n => n.id !== activeId);
  activeId = notes[0].id;
  persistNotes();
  loadActiveIntoEditor();
  renderSidebar();
}});

document.getElementById("clearNoteBtn").addEventListener("click", () => {{
  editorEl.value = "";
  syncCurrentNote();
  editorEl.focus();
}});

function applyFormat(fmt) {{
  const start = editorEl.selectionStart;
  const end = editorEl.selectionEnd;
  const selected = editorEl.value.slice(start, end) || "text";
  let replacement = selected;
  if (fmt === "bold") replacement = `**${{selected}}**`;
  else if (fmt === "italic") replacement = `*${{selected}}*`;
  else if (fmt === "h1") replacement = `\\n# ${{selected}}`;
  else if (fmt === "h2") replacement = `\\n## ${{selected}}`;
  else if (fmt === "todo") replacement = `\\n- [ ] ${{selected}}`;
  else if (fmt === "bullet") replacement = `\\n- ${{selected}}`;
  else if (fmt === "code") replacement = "`" + selected + "`";

  editorEl.value = editorEl.value.slice(0, start) + replacement + editorEl.value.slice(end);
  syncCurrentNote();
  editorEl.focus();
}}

document.querySelectorAll("[data-fmt]").forEach(btn => {{
  btn.addEventListener("click", () => applyFormat(btn.getAttribute("data-fmt")));
}});

document.getElementById("insertTimeBtn").addEventListener("click", () => {{
  const stamp = `[${{new Date().toLocaleString()}}] `;
  const pos = editorEl.selectionStart || editorEl.value.length;
  editorEl.value = editorEl.value.slice(0, pos) + stamp + editorEl.value.slice(pos);
  syncCurrentNote();
}});

document.getElementById("wrapToggleBtn").addEventListener("click", (e) => {{
  wordWrap = !wordWrap;
  editorEl.style.whiteSpace = wordWrap ? "pre-wrap" : "pre";
  e.target.textContent = `WRAP: ${{wordWrap ? "ON" : "OFF"}}`;
}});

document.getElementById("togglePreviewBtn").addEventListener("click", (e) => {{
  splitPreview = !splitPreview;
  previewEl.style.display = splitPreview ? "block" : "none";
  editorSplitEl.classList.toggle("split-active", splitPreview);
  e.target.textContent = `SPLIT PREVIEW: ${{splitPreview ? "ON" : "OFF"}}`;
  updateTelemetry();
}});

document.getElementById("toggleFindBtn").addEventListener("click", () => {{
  const bar = document.getElementById("findBar");
  bar.style.display = bar.style.display === "none" ? "flex" : "none";
}});

document.getElementById("replaceOneBtn").addEventListener("click", () => {{
  const f = document.getElementById("findInput").value;
  const r = document.getElementById("replaceInput").value;
  if (!f) return;
  editorEl.value = editorEl.value.replace(f, r);
  syncCurrentNote();
}});

document.getElementById("replaceAllBtn").addEventListener("click", () => {{
  const f = document.getElementById("findInput").value;
  const r = document.getElementById("replaceInput").value;
  if (!f) return;
  editorEl.value = editorEl.value.split(f).join(r);
  syncCurrentNote();
}});

function downloadFile(ext) {{
  const note = getActiveNote();
  const blob = new Blob([editorEl.value], {{ type: "text/plain;charset=utf-8" }});
  const a = document.createElement("a");
  const safeName = (note.title || "note").toLowerCase().replace(/[^a-z0-9_-]+/g, "-");
  a.href = URL.createObjectURL(blob);
  a.download = `${{safeName}}.${{ext}}`;
  a.click();
}}

document.getElementById("downloadTxtBtn").addEventListener("click", () => downloadFile("txt"));
document.getElementById("downloadMdBtn").addEventListener("click", () => downloadFile("md"));

document.getElementById("copyNoteBtn").addEventListener("click", () => {{
  if (navigator.clipboard) {{
    navigator.clipboard.writeText(editorEl.value);
  }}
  saveStatusEl.textContent = "COPIED TO CLIPBOARD!";
}});

document.getElementById("importFileInput").addEventListener("change", (e) => {{
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {{
    const imported = {{
      id: "note-" + Date.now(),
      title: file.name.replace(/\\.[^.]+$/, ""),
      content: String(reader.result || ""),
      updatedAt: new Date().toLocaleTimeString()
    }};
    notes.unshift(imported);
    activeId = imported.id;
    persistNotes();
    loadActiveIntoEditor();
    renderSidebar();
  }};
  reader.readAsText(file);
}});

loadNotes();
loadActiveIntoEditor();
renderSidebar();
"""

    verify_py = """from pathlib import Path

for req in ("index.html", "style.css", "app.js"):
    p = Path(req)
    assert p.exists() and p.stat().st_size > 100, f"Missing {req}"

html = Path("index.html").read_text(encoding="utf-8")
assert "noteEditor" in html and "noteTitleInput" in html and "notesList" in html
print("PASS: Notepad multi-note editor bundle verified (noteEditor, noteTitleInput, notesList)")
"""

    return [
        {"path": "index.html", "description": "Interactive Notepad & Markdown Studio UI", "content": html},
        {"path": "style.css", "description": "Acid-punk Notepad layout & line-gutter styles", "content": css},
        {"path": "app.js", "description": "Multi-note storage, formatting toolbar, find/replace & file export engine", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying Notepad DOM & script anchors", "content": verify_py},
    ]


def _build_calculator_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // FORGED BY {model_id}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT SCIENTIFIC CALCULATOR // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
      <div class="stats">
        <div class="stat-box"><span>MEMORY</span><strong id="memVal">0</strong></div>
        <div class="stat-box magenta"><span>OPS</span><strong id="calcCount">0</strong></div>
      </div>
    </header>

    <div class="calc-grid">
      <section class="panel">
        <div class="panel-head"><span>// SCIENTIFIC & EXPRESSION DECK</span><span id="angleMode">DEG / FLOAT</span></div>
        <div class="calc-screen">
          <div id="calcExpr" class="calc-expr">0</div>
          <input id="calcDisplay" class="calc-display" value="0" />
        </div>
        <div class="keypad" id="calcKeypad">
          <button class="secondary" data-act="mc">MC</button>
          <button class="secondary" data-act="mr">MR</button>
          <button class="secondary" data-act="m+">M+</button>
          <button class="secondary" data-act="m-">M-</button>
          <button data-act="clear">AC</button>

          <button class="secondary" data-fn="Math.sin(">sin</button>
          <button class="secondary" data-fn="Math.cos(">cos</button>
          <button class="secondary" data-fn="Math.tan(">tan</button>
          <button class="secondary" data-fn="Math.sqrt(">√</button>
          <button class="secondary" data-act="back">⌫</button>

          <button data-val="7">7</button>
          <button data-val="8">8</button>
          <button data-val="9">9</button>
          <button class="secondary" data-val="/">÷</button>
          <button class="secondary" data-val="**">x^y</button>

          <button data-val="4">4</button>
          <button data-val="5">5</button>
          <button data-val="6">6</button>
          <button class="secondary" data-val="*">×</button>
          <button class="secondary" data-val="(">(</button>

          <button data-val="1">1</button>
          <button data-val="2">2</button>
          <button data-val="3">3</button>
          <button class="secondary" data-val="-">−</button>
          <button class="secondary" data-val=")">)</button>

          <button data-val="0">0</button>
          <button data-val=".">.</button>
          <button class="secondary" data-val="3.14159265">π</button>
          <button class="secondary" data-val="+">+</button>
          <button class="yellow-btn" id="equalsBtn" data-act="eval">=</button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <span>// CALCULATION HISTORY TAPE</span>
          <button id="clearTapeBtn" class="secondary">CLEAR TAPE</button>
        </div>
        <div id="historyTape" class="tape-list"></div>
      </section>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""
    css = (
        SHARED_ACID_CSS
        + """
.calc-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 14px; }
@media (max-width: 820px) { .calc-grid { grid-template-columns: 1fr; } }
.calc-screen {
  border: 2px solid var(--acid);
  background: #020603;
  padding: 12px;
  text-align: right;
}
.calc-expr { color: var(--muted); font-size: 12px; min-height: 18px; }
.calc-display {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--acid);
  font-size: 28px;
  font-weight: 900;
  text-align: right;
  padding: 4px 0;
}
.keypad {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-top: 6px;
}
.keypad button { padding: 12px 6px; font-size: 14px; }
.tape-list { display: flex; flex-direction: column; gap: 6px; max-height: 360px; overflow-y: auto; }
.tape-row {
  background: var(--panel-alt);
  border-left: 3px solid var(--acid);
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  cursor: pointer;
}
"""
    )
    js = """const display = document.getElementById("calcDisplay");
const exprEl = document.getElementById("calcExpr");
const tapeEl = document.getElementById("historyTape");
const memEl = document.getElementById("memVal");
const countEl = document.getElementById("calcCount");

let memory = 0;
let ops = 0;
let history = [{ expr: "128 * 8", res: "1024" }, { expr: "Math.sqrt(144)", res: "12" }];

function renderTape() {
  tapeEl.innerHTML = "";
  history.slice().reverse().forEach(item => {
    const row = document.createElement("div");
    row.className = "tape-row";
    row.innerHTML = `<span>${item.expr} =</span><strong style="color:#39ff14">${item.res}</strong>`;
    row.addEventListener("click", () => { display.value = item.res; });
    tapeEl.appendChild(row);
  });
}

function evaluateCurrent() {
  const raw = display.value.trim();
  if (!raw) return;
  try {
    const result = Function('"use strict"; return (' + raw + ')')();
    const formatted = Number.isFinite(result) ? String(Number(result.toPrecision(12))) : String(result);
    exprEl.textContent = raw + " =";
    display.value = formatted;
    ops += 1;
    countEl.textContent = String(ops);
    history.push({ expr: raw, res: formatted });
    renderTape();
  } catch (e) {
    exprEl.textContent = "SYNTAX ERROR";
  }
}

document.getElementById("calcKeypad").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const val = btn.getAttribute("data-val");
  const fn = btn.getAttribute("data-fn");
  const act = btn.getAttribute("data-act");

  if (val) {
    display.value = display.value === "0" ? val : display.value + val;
  } else if (fn) {
    display.value = display.value === "0" ? fn : display.value + fn;
  } else if (act === "clear") {
    display.value = "0";
    exprEl.textContent = "0";
  } else if (act === "back") {
    display.value = display.value.length > 1 ? display.value.slice(0, -1) : "0";
  } else if (act === "eval") {
    evaluateCurrent();
  } else if (act === "mc") {
    memory = 0; memEl.textContent = "0";
  } else if (act === "mr") {
    display.value = String(memory);
  } else if (act === "m+") {
    memory += parseFloat(display.value) || 0; memEl.textContent = String(memory);
  } else if (act === "m-") {
    memory -= parseFloat(display.value) || 0; memEl.textContent = String(memory);
  }
});

display.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); evaluateCurrent(); }
});

document.getElementById("clearTapeBtn").addEventListener("click", () => {
  history = [];
  renderTape();
});

renderTape();
"""
    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
assert "calcDisplay" in html and "calcKeypad" in html and "historyTape" in html
print("PASS: Scientific Calculator bundle verified (calcDisplay, calcKeypad, historyTape)")
"""
    return [
        {"path": "index.html", "description": "Scientific Calculator & History Tape UI", "content": html},
        {"path": "style.css", "description": "Acid-punk Calculator layout styles", "content": css},
        {"path": "app.js", "description": "Expression evaluator, memory register & history tape controller", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying calculator assets", "content": verify_py},
    ]


def _build_timer_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // FORGED BY {model_id}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT CHRONO & POMODORO DECK // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
      <div class="stats">
        <div class="stat-box"><span>SESSIONS</span><strong id="sessionCount">0</strong></div>
        <div class="stat-box magenta"><span>MODE</span><strong id="timerModeLabel">FOCUS</strong></div>
      </div>
    </header>

    <div class="calc-grid" style="display:grid;grid-template-columns:1.2fr 1fr;gap:14px;">
      <section class="panel" style="align-items:center;text-align:center;">
        <div class="panel-head" style="width:100%;"><span>// POMODORO & COUNTDOWN CLOCK</span><span>SYNTH CHIME ARMED</span></div>
        <div class="toolbar" style="justify-content:center;margin-top:6px;">
          <button class="secondary" data-mins="25" data-mode="FOCUS">25:00 FOCUS</button>
          <button class="secondary" data-mins="5" data-mode="SHORT BREAK">05:00 SHORT</button>
          <button class="secondary" data-mins="15" data-mode="LONG BREAK">15:00 LONG</button>
        </div>
        <div id="clockDisplay" style="font-size:64px;font-weight:900;color:#39ff14;text-shadow:3px 3px 0 #ff007f;margin:16px 0;">25:00</div>
        <div class="toolbar" style="justify-content:center;">
          <button id="startPauseBtn" class="yellow-btn">START / PAUSE</button>
          <button id="lapBtn" class="secondary">RECORD LAP / SPLIT</button>
          <button id="resetTimerBtn" class="secondary">RESET</button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head"><span>// LAP SPLITS & FOCUS TASKS</span></div>
        <div style="display:flex;gap:6px;">
          <input id="taskGoalInput" style="flex:1;" placeholder="Add focus goal or lap note..." />
          <button id="addGoalBtn">ADD</button>
        </div>
        <div id="lapList" style="display:flex;flex-direction:column;gap:6px;max-height:260px;overflow-y:auto;"></div>
      </section>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""
    css = SHARED_ACID_CSS
    js = """const clockEl = document.getElementById("clockDisplay");
const modeEl = document.getElementById("timerModeLabel");
const sessionEl = document.getElementById("sessionCount");
const lapListEl = document.getElementById("lapList");
const goalInput = document.getElementById("taskGoalInput");

let remainingSec = 25 * 60;
let running = false;
let intervalId = null;
let sessions = 0;
let items = [{ tag: "READY", text: "Pomodoro 25:00 focus block initialized" }];

function fmt(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function renderList() {
  lapListEl.innerHTML = "";
  items.slice().reverse().forEach(it => {
    const d = document.createElement("div");
    d.style.cssText = "background:#040906;border-left:3px solid #39ff14;padding:8px;display:flex;justify-content:space-between;font-size:12px;";
    d.innerHTML = `<span>${it.text}</span><strong style="color:#f5ff00">${it.tag}</strong>`;
    lapListEl.appendChild(d);
  });
}

document.querySelectorAll("[data-mins]").forEach(btn => {
  btn.addEventListener("click", () => {
    running = false;
    clearInterval(intervalId);
    remainingSec = parseInt(btn.getAttribute("data-mins"), 10) * 60;
    modeEl.textContent = btn.getAttribute("data-mode");
    clockEl.textContent = fmt(remainingSec);
  });
});

document.getElementById("startPauseBtn").addEventListener("click", () => {
  running = !running;
  if (running) {
    intervalId = setInterval(() => {
      if (remainingSec > 0) {
        remainingSec -= 1;
        clockEl.textContent = fmt(remainingSec);
      } else {
        running = false;
        clearInterval(intervalId);
        sessions += 1;
        sessionEl.textContent = String(sessions);
        items.push({ tag: "DONE", text: `Completed ${modeEl.textContent} session!` });
        renderList();
      }
    }, 1000);
  } else {
    clearInterval(intervalId);
  }
});

document.getElementById("lapBtn").addEventListener("click", () => {
  items.push({ tag: fmt(remainingSec), text: `Split recorded (${modeEl.textContent})` });
  renderList();
});

document.getElementById("resetTimerBtn").addEventListener("click", () => {
  running = false;
  clearInterval(intervalId);
  remainingSec = 25 * 60;
  clockEl.textContent = fmt(remainingSec);
});

document.getElementById("addGoalBtn").addEventListener("click", () => {
  const v = goalInput.value.trim();
  if (!v) return;
  goalInput.value = "";
  items.push({ tag: fmt(remainingSec), text: v });
  renderList();
});

renderList();
"""
    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
assert "clockDisplay" in html and "startPauseBtn" in html and "lapList" in html
print("PASS: Pomodoro & Chrono Timer bundle verified")
"""
    return [
        {"path": "index.html", "description": "Pomodoro Focus Timer & Lap Stopwatch UI", "content": html},
        {"path": "style.css", "description": "Acid-punk Timer styling", "content": css},
        {"path": "app.js", "description": "Countdown engine, lap splits & focus task controller", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying Timer DOM", "content": verify_py},
    ]


def _build_game_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // FORGED BY {model_id}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT ARCADE ENGINE // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
      <div class="stats">
        <div class="stat-box"><span>SCORE</span><strong id="gameScore">0</strong></div>
        <div class="stat-box magenta"><span>HIGH SCORE</span><strong id="highScore">0</strong></div>
      </div>
    </header>

    <section class="panel" style="align-items:center;">
      <div class="panel-head" style="width:100%;">
        <span>// INTERACTIVE ARCADE ARENA (USE ARROW KEYS / WASD OR BUTTONS)</span>
        <span id="gameStatus">PLAYING</span>
      </div>
      <canvas id="gameCanvas" width="520" height="320" style="border:2px solid #39ff14;background:#030704;"></canvas>
      <div class="toolbar" style="justify-content:center;">
        <button class="secondary" data-dir="UP">▲ UP</button>
        <button class="secondary" data-dir="LEFT">◀ LEFT</button>
        <button class="secondary" data-dir="DOWN">▼ DOWN</button>
        <button class="secondary" data-dir="RIGHT">▶ RIGHT</button>
        <button id="restartGameBtn" class="yellow-btn">NEW GAME / RESET</button>
      </div>
    </section>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""
    css = SHARED_ACID_CSS
    js = """const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
const scoreEl = document.getElementById("gameScore");
const highEl = document.getElementById("highScore");
const statusEl = document.getElementById("gameStatus");

const GRID = 20;
let snake = [{ x: 8, y: 8 }, { x: 7, y: 8 }, { x: 6, y: 8 }];
let dir = { x: 1, y: 0 };
let food = { x: 14, y: 8 };
let score = 0;
let high = 0;

function spawnFood() {
  food = {
    x: Math.floor(Math.random() * (canvas.width / GRID)),
    y: Math.floor(Math.random() * (canvas.height / GRID))
  };
}

function resetGame() {
  snake = [{ x: 8, y: 8 }, { x: 7, y: 8 }, { x: 6, y: 8 }];
  dir = { x: 1, y: 0 };
  score = 0;
  scoreEl.textContent = "0";
  statusEl.textContent = "PLAYING";
  spawnFood();
}

function step() {
  const head = {
    x: (snake[0].x + dir.x + canvas.width / GRID) % (canvas.width / GRID),
    y: (snake[0].y + dir.y + canvas.height / GRID) % (canvas.height / GRID)
  };
  if (snake.some(s => s.x === head.x && s.y === head.y)) {
    statusEl.textContent = "CRASHED — AUTO RESTART";
    resetGame();
    return;
  }
  snake.unshift(head);
  if (head.x === food.x && head.y === food.y) {
    score += 10;
    high = Math.max(high, score);
    scoreEl.textContent = String(score);
    highEl.textContent = String(high);
    spawnFood();
  } else {
    snake.pop();
  }

  ctx.fillStyle = "#030704";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#ff007f";
  ctx.fillRect(food.x * GRID + 2, food.y * GRID + 2, GRID - 4, GRID - 4);
  snake.forEach((seg, idx) => {
    ctx.fillStyle = idx === 0 ? "#f5ff00" : "#39ff14";
    ctx.fillRect(seg.x * GRID + 1, seg.y * GRID + 1, GRID - 2, GRID - 2);
  });
}

function setDirection(d) {
  if (d === "UP" && dir.y === 0) dir = { x: 0, y: -1 };
  if (d === "DOWN" && dir.y === 0) dir = { x: 0, y: 1 };
  if (d === "LEFT" && dir.x === 0) dir = { x: -1, y: 0 };
  if (d === "RIGHT" && dir.x === 0) dir = { x: 1, y: 0 };
}

window.addEventListener("keydown", (e) => {
  if (e.key === "ArrowUp" || e.key === "w") setDirection("UP");
  if (e.key === "ArrowDown" || e.key === "s") setDirection("DOWN");
  if (e.key === "ArrowLeft" || e.key === "a") setDirection("LEFT");
  if (e.key === "ArrowRight" || e.key === "d") setDirection("RIGHT");
});

document.querySelectorAll("[data-dir]").forEach(btn => {
  btn.addEventListener("click", () => setDirection(btn.getAttribute("data-dir")));
});
document.getElementById("restartGameBtn").addEventListener("click", resetGame);

setInterval(step, 120);
"""
    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
assert "gameCanvas" in html and "gameScore" in html and "restartGameBtn" in html
print("PASS: Interactive Arcade Game bundle verified")
"""
    return [
        {"path": "index.html", "description": "Interactive Arcade Game Arena UI", "content": html},
        {"path": "style.css", "description": "Acid-punk Arcade styling", "content": css},
        {"path": "app.js", "description": "Real-time 2D arcade loop, collision engine & controls", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying game canvas", "content": verify_py},
    ]


def _build_paint_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // FORGED BY {model_id}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT PAINT & PIXEL STUDIO // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
      <div class="stats">
        <div class="stat-box"><span>STROKES</span><strong id="strokeCount">0</strong></div>
      </div>
    </header>

    <section class="panel">
      <div class="toolbar">
        <input type="color" id="brushColor" value="#39ff14" style="width:44px;height:34px;padding:2px;" />
        <button class="secondary" data-color="#39ff14">ACID</button>
        <button class="secondary" data-color="#ff007f">MAGENTA</button>
        <button class="secondary" data-color="#f5ff00">YELLOW</button>
        <button class="secondary" data-color="#00ffa3">CYAN</button>
        <button class="secondary" data-color="#030704">ERASER</button>
        <input type="range" id="brushSize" min="2" max="28" value="5" />
        <button id="clearCanvasBtn" class="secondary">CLEAR</button>
        <button id="exportPngBtn" class="yellow-btn">EXPORT PNG</button>
      </div>
      <canvas id="paintCanvas" width="820" height="360" style="border:2px solid #39ff14;background:#030704;cursor:crosshair;width:100%;"></canvas>
    </section>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""
    css = SHARED_ACID_CSS
    js = """const canvas = document.getElementById("paintCanvas");
const ctx = canvas.getContext("2d");
const colorEl = document.getElementById("brushColor");
const sizeEl = document.getElementById("brushSize");
const strokeEl = document.getElementById("strokeCount");

let drawing = false;
let strokes = 0;

ctx.fillStyle = "#030704";
ctx.fillRect(0, 0, canvas.width, canvas.height);

function getPos(e) {
  const r = canvas.getBoundingClientRect();
  return {
    x: (e.clientX - r.left) * (canvas.width / r.width),
    y: (e.clientY - r.top) * (canvas.height / r.height)
  };
}

canvas.addEventListener("mousedown", (e) => {
  drawing = true;
  const p = getPos(e);
  ctx.beginPath();
  ctx.moveTo(p.x, p.y);
  strokes += 1;
  strokeEl.textContent = String(strokes);
});
canvas.addEventListener("mousemove", (e) => {
  if (!drawing) return;
  const p = getPos(e);
  ctx.strokeStyle = colorEl.value;
  ctx.lineWidth = Number(sizeEl.value);
  ctx.lineCap = "round";
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
});
window.addEventListener("mouseup", () => { drawing = false; });

document.querySelectorAll("[data-color]").forEach(btn => {
  btn.addEventListener("click", () => { colorEl.value = btn.getAttribute("data-color"); });
});
document.getElementById("clearCanvasBtn").addEventListener("click", () => {
  ctx.fillStyle = "#030704";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
});
document.getElementById("exportPngBtn").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = canvas.toDataURL("image/png");
  a.download = "mercbot-artwork.png";
  a.click();
});
"""
    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
assert "paintCanvas" in html and "brushColor" in html and "exportPngBtn" in html
print("PASS: Paint & Drawing Studio bundle verified")
"""
    return [
        {"path": "index.html", "description": "Interactive Paint & Pixel Studio UI", "content": html},
        {"path": "style.css", "description": "Acid-punk Paint Studio styling", "content": css},
        {"path": "app.js", "description": "Canvas brush engine, swatches & PNG exporter", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying paint canvas", "content": verify_py},
    ]


def _build_devtools_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // FORGED BY {model_id}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT DEVELOPER WORKBENCH // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
    </header>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      <section class="panel">
        <div class="panel-head"><span>// CRYPTOGRAPHIC PASSWORD & TOKEN GENERATOR</span></div>
        <div style="display:flex;gap:8px;align-items:center;">
          <input id="generatedPass" style="flex:1;font-weight:800;color:#39ff14;" readonly />
          <button id="genPassBtn" class="yellow-btn">GENERATE</button>
        </div>
        <div class="toolbar">
          <label>LEN: <input type="number" id="passLen" value="24" min="8" max="64" style="width:65px;" /></label>
          <button id="uuidBtn" class="secondary">NEW UUID</button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head"><span>// JSON FORMATTER & BASE64 TRANSFORMER</span></div>
        <textarea id="devInput" rows="6" placeholder="Paste JSON or text here...">{{"service":"{display_name}","status":"armed","version":1}}</textarea>
        <div class="toolbar">
          <button id="fmtJsonBtn">FORMAT JSON</button>
          <button id="b64EncBtn" class="secondary">BASE64 ENCODE</button>
          <button id="b64DecBtn" class="secondary">BASE64 DECODE</button>
        </div>
        <div id="devStatus" class="status-bar">READY</div>
      </section>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""
    css = SHARED_ACID_CSS
    js = """const passEl = document.getElementById("generatedPass");
const lenEl = document.getElementById("passLen");
const devIn = document.getElementById("devInput");
const statusEl = document.getElementById("devStatus");

function genPass() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*_+-=";
  const n = Math.max(8, Math.min(64, parseInt(lenEl.value, 10) || 24));
  let out = "";
  for (let i = 0; i < n; i++) out += chars[Math.floor(Math.random() * chars.length)];
  passEl.value = out;
}

document.getElementById("genPassBtn").addEventListener("click", genPass);
document.getElementById("uuidBtn").addEventListener("click", () => {
  passEl.value = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
  });
});

document.getElementById("fmtJsonBtn").addEventListener("click", () => {
  try {
    devIn.value = JSON.stringify(JSON.parse(devIn.value), null, 2);
    statusEl.textContent = "VALID JSON — PRETTY PRINTED";
  } catch (e) {
    statusEl.textContent = "INVALID JSON: " + e.message;
  }
});
document.getElementById("b64EncBtn").addEventListener("click", () => {
  devIn.value = btoa(unescape(encodeURIComponent(devIn.value)));
  statusEl.textContent = "ENCODED TO BASE64";
});
document.getElementById("b64DecBtn").addEventListener("click", () => {
  try {
    devIn.value = decodeURIComponent(escape(atob(devIn.value.trim())));
    statusEl.textContent = "DECODED FROM BASE64";
  } catch (e) {
    statusEl.textContent = "INVALID BASE64 INPUT";
  }
});

genPass();
"""
    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
assert "generatedPass" in html and "devInput" in html and "fmtJsonBtn" in html
print("PASS: Developer Workbench bundle verified")
"""
    return [
        {"path": "index.html", "description": "Developer Workbench & Password/JSON Utility UI", "content": html},
        {"path": "style.css", "description": "Acid-punk DevTools styling", "content": css},
        {"path": "app.js", "description": "Password generator, UUID, JSON formatter & Base64 engine", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying DevTools DOM", "content": verify_py},
    ]


def _build_domain_studio_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    """Build a tailored interactive workspace & item editor for any custom domain prompt."""
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // FORGED BY {model_id}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT APPLICATION STUDIO // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
      <div class="stats">
        <div class="stat-box"><span>ITEMS</span><strong id="totalItems">0</strong></div>
        <div class="stat-box magenta"><span>ACTIVE</span><strong id="activeItems">0</strong></div>
        <div class="stat-box yellow"><span>COMPLETED</span><strong id="doneItems">0</strong></div>
      </div>
    </header>

    <div style="display:grid;grid-template-columns:1fr 1.25fr;gap:14px;">
      <section class="panel">
        <div class="panel-head">
          <span>// CREATE & MANAGE {display_name.upper()} ENTRIES</span>
          <button id="exportJsonBtn" class="secondary">EXPORT JSON</button>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <input id="itemTitleIn" style="flex:2;" placeholder="Title or name..." />
          <input id="itemCategoryIn" style="flex:1;" placeholder="Category / Tag..." />
          <button id="createItemBtn" class="yellow-btn">+ ADD</button>
        </div>
        <textarea id="itemDetailIn" rows="3" placeholder="Details, notes, or parameters for this entry..."></textarea>
        <input id="filterInput" placeholder="Search & filter entries..." />
        <div id="domainList" style="display:flex;flex-direction:column;gap:6px;max-height:250px;overflow-y:auto;"></div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <span>// LIVE INSPECTOR & EDITOR PANE</span>
          <span id="inspectorStatus" style="color:#39ff14;">READY</span>
        </div>
        <input id="editTitle" style="font-size:16px;font-weight:800;color:#f5ff00;" placeholder="Select an entry to edit..." />
        <textarea id="editBody" rows="9" placeholder="Select or create an entry on the left to inspect and edit its full contents..."></textarea>
        <div class="toolbar" style="justify-content:space-between;">
          <div style="display:flex;gap:6px;">
            <button id="saveEditBtn">SAVE CHANGES</button>
            <button id="toggleStateBtn" class="secondary">TOGGLE DONE / ACTIVE</button>
          </div>
          <button id="deleteItemBtn" class="secondary">DELETE</button>
        </div>
      </section>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""
    css = SHARED_ACID_CSS
    js = f"""const listEl = document.getElementById("domainList");
const titleIn = document.getElementById("itemTitleIn");
const catIn = document.getElementById("itemCategoryIn");
const detailIn = document.getElementById("itemDetailIn");
const filterIn = document.getElementById("filterInput");
const editTitle = document.getElementById("editTitle");
const editBody = document.getElementById("editBody");
const totalEl = document.getElementById("totalItems");
const activeEl = document.getElementById("activeItems");
const doneEl = document.getElementById("doneItems");
const statusEl = document.getElementById("inspectorStatus");

let items = [
  {{ id: 1, title: "{display_name} Primary Workspace", category: "CORE", body: "Mission: {brief}\\nUse this workspace to create, edit, filter, and export records.", done: false }},
  {{ id: 2, title: "Sample Entry #2", category: "GENERAL", body: "Click any item to edit its contents or toggle its completion state.", done: true }}
];
let selectedId = 1;

function render() {{
  const q = (filterIn.value || "").toLowerCase().trim();
  listEl.innerHTML = "";
  items.filter(it => !q || it.title.toLowerCase().includes(q) || it.category.toLowerCase().includes(q) || it.body.toLowerCase().includes(q))
    .forEach(it => {{
      const row = document.createElement("div");
      row.style.cssText = "background:#040906;border:1px solid #1d3f27;border-left:4px solid " + (it.done ? "#f5ff00" : "#39ff14") + ";padding:8px 10px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-size:12px;";
      row.innerHTML = `<div><strong style="color:#39ff14">${{it.title}}</strong> <span style="color:#8ab896">[${{it.category}}]</span></div><span style="color:${{it.done ? '#f5ff00' : '#39ff14'}}">${{it.done ? 'DONE' : 'ACTIVE'}}</span>`;
      row.addEventListener("click", () => {{
        selectedId = it.id;
        loadInspector();
      }});
      listEl.appendChild(row);
    }});
  totalEl.textContent = String(items.length);
  activeEl.textContent = String(items.filter(i => !i.done).length);
  doneEl.textContent = String(items.filter(i => i.done).length);
}}

function loadInspector() {{
  const cur = items.find(i => i.id === selectedId) || items[0];
  if (!cur) return;
  selectedId = cur.id;
  editTitle.value = cur.title;
  editBody.value = cur.body;
  statusEl.textContent = `${{cur.category}} // ${{cur.done ? "DONE" : "ACTIVE"}}`;
}}

document.getElementById("createItemBtn").addEventListener("click", () => {{
  const t = titleIn.value.trim();
  if (!t) return;
  const item = {{
    id: Date.now(),
    title: t,
    category: (catIn.value.trim() || "GENERAL").toUpperCase(),
    body: detailIn.value.trim() || t,
    done: false
  }};
  items.unshift(item);
  selectedId = item.id;
  titleIn.value = ""; catIn.value = ""; detailIn.value = "";
  render();
  loadInspector();
}});

document.getElementById("saveEditBtn").addEventListener("click", () => {{
  const cur = items.find(i => i.id === selectedId);
  if (!cur) return;
  cur.title = editTitle.value.trim() || cur.title;
  cur.body = editBody.value;
  statusEl.textContent = "SAVED!";
  render();
}});

document.getElementById("toggleStateBtn").addEventListener("click", () => {{
  const cur = items.find(i => i.id === selectedId);
  if (!cur) return;
  cur.done = !cur.done;
  render();
  loadInspector();
}});

document.getElementById("deleteItemBtn").addEventListener("click", () => {{
  items = items.filter(i => i.id !== selectedId);
  selectedId = items[0] ? items[0].id : null;
  render();
  loadInspector();
}});

document.getElementById("exportJsonBtn").addEventListener("click", () => {{
  const blob = new Blob([JSON.stringify(items, null, 2)], {{ type: "application/json" }});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "workspace-export.json";
  a.click();
}});

filterIn.addEventListener("input", render);
render();
loadInspector();
"""
    verify_py = """from pathlib import Path
html = Path("index.html").read_text(encoding="utf-8")
assert "domainList" in html and "createItemBtn" in html and "editBody" in html
print("PASS: Custom Domain Application Studio verified")
"""
    return [
        {"path": "index.html", "description": f"Interactive {display_name} Studio UI", "content": html},
        {"path": "style.css", "description": "Acid-punk application styling", "content": css},
        {"path": "app.js", "description": "Interactive CRUD state, search filter, inspector & JSON export", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying application bundle", "content": verify_py},
    ]


def _build_webgl_3d_files(display_name: str, brief: str, model_id: str) -> list[dict[str, str]]:
    from mercury.webgl_subject import mesh_mode_for_subject, resolve_webgl_subject, subject_bootstrap_js, subject_builder_js

    subject = resolve_webgl_subject(f"{display_name}\n{brief}")
    mode_for_family = mesh_mode_for_subject(subject)
    mesh_modes = ["subject", "core", "dino", "torus"]
    initial_idx = mesh_modes.index(mode_for_family)
    mesh_label = subject["name"].upper()
    subject_name = subject["name"]
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{display_name} // 3D WEBGL STUDIO ({model_id})</title>
  <link rel="stylesheet" href="style.css" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
  <div class="shell">
    <header class="top-bar">
      <div>
        <div class="badge">MERCBOT 3D WEBGL &amp; SHADER STUDIO // {model_id}</div>
        <h1>{display_name}</h1>
        <p class="brief">{brief}</p>
      </div>
      <div class="stats">
        <div class="stat-box"><span>3D ENGINE</span><strong id="engineStatus">WEBGL 3D</strong></div>
        <div class="stat-box"><span>SCORE / OPS</span><strong id="opsCount">0</strong></div>
        <div class="stat-box magenta"><span>ENERGY</span><strong id="energyVal">100%</strong></div>
      </div>
    </header>

    <div class="webgl-grid">
      <section class="panel">
        <div class="panel-head">
          <span>// INTERACTIVE 3D WEBGL SIMULATION &amp; VISUALIZER (DRAG TO ORBIT • SCROLL TO ZOOM)</span>
          <span id="meshLabel" style="color:var(--acid);">MESH: {mesh_label}</span>
        </div>
        <canvas id="simCanvas" width="760" height="400" data-initial-mesh="{mode_for_family}" data-subject="{subject_name}"></canvas>
        <div class="controls" style="margin-top:12px;">
          <button id="pulseBtn">TRIGGER PULSE WAVE</button>
          <button id="spawnBtn">SPAWN ORBITAL NODE</button>
          <button id="modeBtn" class="secondary">CYCLE SHADER MODE</button>
          <button id="meshBtn" class="secondary">SWITCH 3D MODEL</button>
          <button id="clearBtn" class="secondary">RESET MATRIX</button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <span>// LIVE 3D TELEMETRY &amp; SHADER COMMAND LOG</span>
          <span id="shaderBadge" style="color:var(--magenta);">SHADER: NEON SOLID</span>
        </div>
        <div style="display:flex;gap:8px;margin-bottom:10px;">
          <input id="entryInput" placeholder="Tell it what to build next — chicken, cat, spaceship, house..." />
          <button id="addEntryBtn">EXECUTE</button>
        </div>
        <div id="entriesList" class="entries"></div>
      </section>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""

    css = (
        SHARED_ACID_CSS
        + """
.webgl-grid {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 16px;
}
@media (max-width: 900px) {
  .webgl-grid { grid-template-columns: 1fr; }
}
#simCanvas {
  width: 100%;
  height: 400px;
  background: radial-gradient(circle at center, #0a1f12 0%, #030704 75%);
  border: 2px solid var(--acid);
  box-shadow: inset 0 0 24px rgba(255, 0, 127, 0.35);
  display: block;
  cursor: grab;
}
#simCanvas:active { cursor: grabbing; }
.entries {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 390px;
  overflow-y: auto;
}
.entry-card {
  background: #040906;
  border: 1px solid var(--border);
  border-left: 4px solid var(--acid);
  padding: 8px 10px;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
"""
    )

    js = f"""const canvas = document.getElementById("simCanvas");
const opsEl = document.getElementById("opsCount");
const energyEl = document.getElementById("energyVal");
const entriesList = document.getElementById("entriesList");
const entryInput = document.getElementById("entryInput");
const meshLabel = document.getElementById("meshLabel");
const shaderBadge = document.getElementById("shaderBadge");
const engineStatus = document.getElementById("engineStatus");

let ops = 0;
let energy = 100;
let shaderMode = 0; // 0: Neon Solid, 1: Acid Wireframe, 2: Magenta Overdrive
const shaderNames = ["NEON SOLID", "ACID WIREFRAME", "MAGENTA OVERDRIVE"];
const meshModes = ["subject", "core", "dino", "torus"];
let currentMeshIdx = {initial_idx};
if (currentMeshIdx < 0) currentMeshIdx = 0;

let pulseActive = false;
let pulseTimer = 0;
let rotX = 0.25;
let rotY = -0.5;
let zoom = 12;
let userAdjustedZoom = false;
let fitZoom = 12;
___SUBJECT_BOOTSTRAP___
let dragging = false;
let lastMouse = {{ x: 0, y: 0 }};

const records = [
  {{ id: 101, text: "Initialized 3D subject mesh: {subject_name}", status: "ACTIVE" }},
  {{ id: 102, text: "3D Scene Ready: {display_name}", status: "VERIFIED" }}
];

function renderEntries() {{
  entriesList.innerHTML = "";
  records.slice().reverse().forEach(item => {{
    const div = document.createElement("div");
    div.className = "entry-card";
    div.innerHTML = `<span><strong style="color:#f5ff00">#${{item.id}}</strong> ${{item.text}}</span><span style="color:#39ff14">${{item.status}}</span>`;
    entriesList.appendChild(div);
  }});
}}
renderEntries();

function bumpOps(label) {{
  ops += 1;
  opsEl.textContent = String(ops);
  energy = Math.max(15, energy - 2);
  energyEl.textContent = `${{energy}}%`;
  if (label) {{
    records.push({{ id: 100 + records.length + 1, text: label, status: "OK" }});
    renderEntries();
  }}
}}

canvas.addEventListener("mousedown", (e) => {{
  dragging = true;
  lastMouse = {{ x: e.clientX, y: e.clientY }};
}});
window.addEventListener("mouseup", () => {{ dragging = false; }});
window.addEventListener("mousemove", (e) => {{
  if (!dragging) return;
  const dx = e.clientX - lastMouse.x;
  const dy = e.clientY - lastMouse.y;
  lastMouse = {{ x: e.clientX, y: e.clientY }};
  rotY += dx * 0.01;
  rotX = Math.max(-1.4, Math.min(1.4, rotX + dy * 0.01));
}});
canvas.addEventListener("wheel", (e) => {{
  e.preventDefault();
  zoom = Math.max(4, Math.min(28, zoom + e.deltaY * 0.01));
  userAdjustedZoom = true;
}}, {{ passive: false }});

let spawnNodeFn = () => {{}};
let applyShaderFn = () => {{}};
let rebuildMeshFn = () => {{}};
let clearNodesFn = () => {{}};

if (typeof window.THREE !== "undefined") {{
  engineStatus.textContent = "THREE.JS WEBGL";
  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.setSize(canvas.clientWidth || 760, canvas.clientHeight || 400, false);
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x030704);
  scene.fog = new THREE.FogExp2(0x030704, 0.045);

  const camera = new THREE.PerspectiveCamera(45, (canvas.clientWidth || 760) / (canvas.clientHeight || 400), 0.1, 1000);
  camera.position.z = zoom;

  scene.add(new THREE.AmbientLight(0xffffff, 0.62));
  const keyLight = new THREE.DirectionalLight(0xfff8ee, 0.95);
  keyLight.position.set(6, 10, 8);
  scene.add(keyLight);
  const light1 = new THREE.PointLight(0xff007f, 0.45, 60);
  light1.position.set(6, 6, 6);
  scene.add(light1);
  const light2 = new THREE.PointLight(0x39ff14, 0.35, 60);
  light2.position.set(-6, -5, 6);
  scene.add(light2);

  const rootGroup = new THREE.Group();
  scene.add(rootGroup);

  const nodes = [];
  const materials = [];

  function makeMat(hex, wire = false, emissive = 0x09150d, kind = "metal") {{
    const organic = kind === "organic" || kind === "matte";
    const gel = kind === "gel";
    const m = new THREE.MeshStandardMaterial({{
      color: hex,
      metalness: organic || gel ? 0.04 : 0.75,
      roughness: kind === "matte" ? 0.9 : organic ? 0.72 : gel ? 0.2 : 0.25,
      wireframe: wire || shaderMode === 1,
      emissive: shaderMode === 2 ? 0x33001b : (organic || gel ? 0x000000 : emissive),
      flatShading: organic,
      transparent: gel,
      opacity: gel ? 0.9 : 1
    }});
    materials.push(m);
    return m;
  }}

___BUILD_REQUESTED_SUBJECT___
  function build3DModel() {{
    while (rootGroup.children.length > 0) {{
      rootGroup.remove(rootGroup.children[0]);
    }}
    materials.length = 0;
    const modeName = meshModes[currentMeshIdx];
    meshLabel.textContent = (modeName === "subject" || modeName === activeSubject.family)
      ? ("MESH: " + activeSubject.name.toUpperCase())
      : ("MESH: " + modeName.toUpperCase());

    if (modeName === "dino") {{
      // 3D Punk DinoBuddy with Neon Mohawk
      const bodyMat = makeMat(activeSubject.colors.body);
      const mohawkMat = makeMat(activeSubject.colors.detail, false, 0x440022);
      const eyeMat = makeMat(activeSubject.colors.eye, false, 0x555500);

      const torso = new THREE.Mesh(new THREE.BoxGeometry(2.2, 2.6, 1.6), bodyMat);
      torso.position.set(0, -0.4, 0);
      rootGroup.add(torso);

      const head = new THREE.Mesh(new THREE.BoxGeometry(2.0, 1.6, 1.7), bodyMat);
      head.position.set(0.7, 1.5, 0);
      rootGroup.add(head);

      const snout = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.9, 1.3), bodyMat);
      snout.position.set(2.1, 1.3, 0);
      rootGroup.add(snout);

      const tail = new THREE.Mesh(new THREE.ConeGeometry(0.7, 2.6, 6), bodyMat);
      tail.rotation.z = Math.PI / 2.4;
      tail.position.set(-2.1, -0.9, 0);
      rootGroup.add(tail);

      const legL = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.5, 0.6), bodyMat);
      legL.position.set(-0.3, -2.1, 0.5);
      const legR = legL.clone();
      legR.position.z = -0.5;
      rootGroup.add(legL, legR);

      const eyeL = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 12), eyeMat);
      eyeL.position.set(1.2, 1.8, 0.88);
      const eyeR = eyeL.clone();
      eyeR.position.z = -0.88;
      rootGroup.add(eyeL, eyeR);

      // Spiked Punk Mohawk along head & back
      for (let i = 0; i < 6; i++) {{
        const spike = new THREE.Mesh(new THREE.ConeGeometry(0.28, 1.25, 5), mohawkMat);
        spike.position.set(1.3 - i * 0.48, 2.7 - i * 0.22, 0);
        spike.rotation.z = 0.2 * i;
        rootGroup.add(spike);
      }}
    }} else if (modeName === "torus") {{
      const knotMat = makeMat(0x39ff14);
      const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(2.1, 0.55, 120, 18), knotMat);
      rootGroup.add(knot);
      const wireCage = new THREE.Mesh(
        new THREE.IcosahedronGeometry(3.8, 1),
        new THREE.MeshBasicMaterial({{ color: 0xff007f, wireframe: true, transparent: true, opacity: 0.35 }})
      );
      rootGroup.add(wireCage);
    }} else if (modeName === "core") {{
      // MercBot 3D Core + Orbital Rings
      const core = new THREE.Mesh(new THREE.IcosahedronGeometry(2.1, 0), makeMat(0x223829));
      rootGroup.add(core);
      const ring1 = new THREE.Mesh(
        new THREE.TorusGeometry(3.5, 0.1, 16, 100),
        new THREE.MeshBasicMaterial({{ color: 0x39ff14, wireframe: shaderMode === 1 }})
      );
      ring1.rotation.x = Math.PI / 2;
      rootGroup.add(ring1);
      const ring2 = new THREE.Mesh(
        new THREE.TorusGeometry(4.4, 0.07, 16, 100),
        new THREE.MeshBasicMaterial({{ color: 0xff007f, wireframe: shaderMode === 1 }})
      );
      ring2.rotation.y = Math.PI / 2;
      rootGroup.add(ring2);
    }} else {{
      buildRequestedSubject();
    }}
  }}

  spawnNodeFn = () => {{
    const isAcid = nodes.length % 2 === 0;
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.28, 14, 14),
      new THREE.MeshBasicMaterial({{ color: isAcid ? 0x39ff14 : 0xff007f, wireframe: shaderMode === 1 }})
    );
    const angle = Math.random() * Math.PI * 2;
    const radius = 5 + Math.random() * 2.8;
    const speed = 0.012 + Math.random() * 0.025;
    const yOff = (Math.random() - 0.5) * 3.5;
    scene.add(mesh);
    nodes.push({{ mesh, angle, radius, speed, yOff }});
  }};

  clearNodesFn = () => {{
    nodes.forEach(n => scene.remove(n.mesh));
    nodes.length = 0;
    for (let i = 0; i < 4; i++) spawnNodeFn();
  }};

  applyShaderFn = () => {{
    materials.forEach(m => {{
      m.wireframe = shaderMode === 1;
      m.emissive.setHex(shaderMode === 2 ? 0xff007f : 0x09150d);
    }});
  }};

  rebuildMeshFn = build3DModel;
  build3DModel();
  const orbitCount = (activeSubject.family === "core" || activeSubject.family === "torus") ? 5 : 0;
  for (let i = 0; i < orbitCount; i++) spawnNodeFn();

  window.addEventListener("resize", () => {{
    if (!canvas.clientWidth) return;
    camera.aspect = canvas.clientWidth / canvas.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  }});

  function animateThree() {{
    requestAnimationFrame(animateThree);
    camera.position.z = zoom;
    if (!dragging) {{
      rotY += 0.008;
    }}
    rootGroup.rotation.y = rotY;
    rootGroup.rotation.x = rotX;

    if (pulseActive) {{
      pulseTimer -= 1;
      const scale = 1 + Math.sin(pulseTimer * 0.25) * 0.22;
      rootGroup.scale.setScalar(scale);
      if (pulseTimer <= 0) {{
        pulseActive = false;
        rootGroup.scale.setScalar(1);
      }}
    }} else {{
      rootGroup.scale.setScalar(1 + Math.sin(Date.now() * 0.003) * 0.04);
    }}

    nodes.forEach(n => {{
      n.angle += n.speed + (pulseActive ? 0.04 : 0);
      n.mesh.position.x = Math.cos(n.angle) * n.radius;
      n.mesh.position.z = Math.sin(n.angle) * n.radius;
      n.mesh.position.y = n.yOff + Math.sin(n.angle * 2) * 0.4;
    }});

    renderer.render(scene, camera);
  }}
  animateThree();
}} else {{
  // Offline software 3D perspective wireframe renderer fallback
  engineStatus.textContent = "3D PROJECTION";
  const ctx = canvas.getContext("2d");
  const orbiters = Array.from({{ length: 6 }}, (_, i) => ({{ angle: i, radius: 140 + i * 12, speed: 0.02 + i * 0.004 }}));
  spawnNodeFn = () => orbiters.push({{ angle: Math.random() * 6, radius: 130 + Math.random() * 60, speed: 0.025 }});
  clearNodesFn = () => {{ orbiters.length = 4; }};

  function animateFallback() {{
    requestAnimationFrame(animateFallback);
    ctx.fillStyle = "#030704";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    rotY += 0.012;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const r = pulseActive ? 95 : 75;
    if (pulseActive && --pulseTimer <= 0) pulseActive = false;

    if (activeSubject && activeSubject.family !== "core" && activeSubject.family !== "torus") {{
      drawSubjectFallback(ctx);
      return;
    }}
    ctx.strokeStyle = shaderMode === 2 ? "#ff007f" : "#39ff14";
    ctx.lineWidth = 2;
    for (let i = 0; i < 12; i++) {{
      const a = (i / 12) * Math.PI * 2 + rotY;
      ctx.beginPath();
      ctx.ellipse(cx, cy, r, Math.abs(Math.cos(a)) * r, rotX, 0, Math.PI * 2);
      ctx.stroke();
    }}
  }}
  animateFallback();
}}

document.getElementById("pulseBtn").addEventListener("click", () => {{
  pulseActive = true;
  pulseTimer = 55;
  bumpOps("Triggered high-energy 3D pulse wave across WebGL mesh");
}});

document.getElementById("spawnBtn").addEventListener("click", () => {{
  spawnNodeFn();
  spawnNodeFn();
  bumpOps("Spawned +2 3D orbital telemetry nodes");
}});

document.getElementById("modeBtn").addEventListener("click", () => {{
  shaderMode = (shaderMode + 1) % 3;
  shaderBadge.textContent = `SHADER: ${{shaderNames[shaderMode]}}`;
  applyShaderFn();
  bumpOps(`Switched 3D WebGL shader -> ${{shaderNames[shaderMode]}}`);
}});

document.getElementById("meshBtn").addEventListener("click", () => {{
  currentMeshIdx = (currentMeshIdx + 1) % meshModes.length;
  rebuildMeshFn();
  bumpOps(`Loaded 3D geometry -> ${{meshModes[currentMeshIdx].toUpperCase()}}`);
}});

document.getElementById("clearBtn").addEventListener("click", () => {{
  clearNodesFn();
  rotX = 0.25;
  rotY = -0.5;
  userAdjustedZoom = false;
  zoom = fitZoom || 12;
  bumpOps("Reset 3D orbital matrix & camera transform");
}});

document.getElementById("addEntryBtn").addEventListener("click", () => {{
  const v = entryInput.value.trim();
  if (!v) return;
  entryInput.value = "";
  applySubjectCommand(v);
  pulseActive = true;
  pulseTimer = 45;
  bumpOps(`Executed 3D command: ${{v}}`);
}});
""".replace("___SUBJECT_BOOTSTRAP___", subject_bootstrap_js(subject)).replace(
        "___BUILD_REQUESTED_SUBJECT___", subject_builder_js()
    )

    verify_py = """from pathlib import Path

for req in ("index.html", "style.css", "app.js"):
    p = Path(req)
    assert p.exists() and p.stat().st_size > 100, f"Missing {req}"

html = Path("index.html").read_text(encoding="utf-8")
js = Path("app.js").read_text(encoding="utf-8")
assert "simCanvas" in html and "pulseBtn" in html
assert "WebGLRenderer" in js and "IcosahedronGeometry" in js
print("PASS: 3D WebGL & Three.js interactive visualizer bundle verified")
"""
    return [
        {"path": "index.html", "description": "Interactive 3D WebGL & Three.js Visualizer UI", "content": html},
        {"path": "style.css", "description": "Acid-punk 3D WebGL viewport stylesheet", "content": css},
        {"path": "app.js", "description": f"Three.js 3D WebGL engine for {subject_name}", "content": js},
        {"path": "verify_custom.py", "description": "Smoke test verifying 3D WebGL application bundle", "content": verify_py},
    ]


# Open-ended products where the selected model should write the app when reachable.
# Offline builders below are the fallback so synth mode still ships a real product.
_LIVE_FIRST_ARCHETYPES = frozenset({"landing_page", "dashboard", "domain_studio", "chat"})


def _try_live_llm_app_synthesis(
    spec: FrontierModelSpec,
    display_name: str,
    brief: str,
    api_keys: dict[str, str] | None,
    *,
    on_progress: Any | None = None,
) -> list[dict[str, str]] | None:
    """Ask the selected frontier model to write the app (validated file blocks + one repair)."""
    from mercury.app_synthesis import synthesize_app_with_model

    result = synthesize_app_with_model(
        spec,
        display_name=display_name,
        brief=brief,
        api_keys=api_keys,
        on_progress=on_progress,
    )
    if result.ok and result.files:
        return result.files
    return None


def synthesize_prompt_driven_template(
    base_tmpl: "AppTemplate",
    *,
    display_name: str,
    brief: str,
    model_spec: FrontierModelSpec,
    api_keys: dict[str, str] | None = None,
    mode: str = "auto",
    on_progress: Any | None = None,
) -> "AppTemplate":
    """Return a prompt-tailored AppTemplate that actually builds what the user asked for."""
    from mercury.offline_sites import build_dashboard_files, build_landing_page_files
    from mercury.templates import AppTemplate, AppTemplateFile

    archetype = detect_prompt_archetype(display_name, brief)
    if archetype == "telemetry":
        return base_tmpl

    # 1. Live model writes the product when the user asked for live/auto on an open-ended request.
    want_live = mode == "live" or (
        mode == "auto" and (archetype in _LIVE_FIRST_ARCHETYPES or bool(api_keys))
    )
    if want_live:
        live_files = _try_live_llm_app_synthesis(
            model_spec,
            display_name,
            brief,
            api_keys,
            on_progress=on_progress,
        )
        if live_files:
            return AppTemplate(
                id=base_tmpl.id,
                name=f"{display_name} (Live {model_spec.name} Forge)",
                category=base_tmpl.category,
                badge=base_tmpl.badge,
                stack=base_tmpl.stack,
                tagline=brief,
                verify_command="python verify_custom.py",
                run_instructions=base_tmpl.run_instructions,
                files=[AppTemplateFile(**f) for f in live_files],
            )

    # 2. Offline builders that still match the request (never a generic CRUD stub for sites).
    builders = {
        "notepad": _build_notepad_files,
        "calculator": _build_calculator_files,
        "timer": _build_timer_files,
        "game": _build_game_files,
        "paint": _build_paint_files,
        "devtools": _build_devtools_files,
        "webgl_3d": _build_webgl_3d_files,
        "landing_page": build_landing_page_files,
        "dashboard": build_dashboard_files,
        "chat": _build_domain_studio_files,
        "domain_studio": _build_domain_studio_files,
    }
    builder_fn = builders.get(archetype, _build_domain_studio_files)
    file_dicts = builder_fn(display_name, brief, model_spec.id)

    return AppTemplate(
        id=base_tmpl.id,
        name=f"{display_name} ({archetype.replace('_', ' ').title()})",
        category=base_tmpl.category,
        badge=base_tmpl.badge,
        stack=base_tmpl.stack,
        tagline=brief,
        verify_command="python verify_custom.py",
        run_instructions=base_tmpl.run_instructions,
        files=[AppTemplateFile(**f) for f in file_dicts],
    )
