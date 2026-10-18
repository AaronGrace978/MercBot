"""Live frontier-model application synthesis for the MercBot Application Forge.

The selected model writes the application. Output uses plain file blocks rather
than JSON so HTML/CSS/JS never has to survive string escaping:

    ===FILE: index.html===
    ...
    ===END FILE===

Every response is validated (entry point present, local references resolved,
no truncated documents). One repair turn is attempted with the concrete
problems before the synthesis is reported as failed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Callable

from mercury_runtime.providers import FrontierModelSpec, call_frontier_provider, live_model_route

SYNTHESIS_TIMEOUT_S = 420.0
SYNTHESIS_MAX_OUTPUT_TOKENS = 32000
MAX_FILES = 24

_FILE_BLOCK = re.compile(
    r"^[ \t]*===\s*FILE:\s*(?P<path>[^\n=]+?)\s*===[ \t]*\r?\n(?P<body>.*?)^[ \t]*===\s*END\s*FILE\s*===[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
_FENCED_LABELED = re.compile(
    r"^[ \t]*(?:#+\s*|\*\*)?`?(?P<path>[\w./-]+\.(?:html|css|js|mjs|json|svg|md|py|txt))`?(?:\*\*)?:?[ \t]*\r?\n"
    r"```[\w+-]*[ \t]*\r?\n(?P<body>.*?)^```",
    re.MULTILINE | re.DOTALL,
)
_FENCE_WRAPPER = re.compile(r"^\s*```[\w+-]*\s*\n(?P<body>.*)\n\s*```\s*$", re.DOTALL)

SYSTEM_PROMPT = """You are the MercBot Application Forge, a senior product engineer and designer.
You build exactly the application the user describes, as a complete, working, polished static web app.

Hard requirements:
- Build what was asked. A landing page is a landing page, a dashboard is a dashboard, a game is a game.
  Never substitute a generic CRUD list, todo app, or placeholder demo for the requested product.
- Match the requested style, theme, and tone. If the user names an aesthetic (cyberpunk, minimal,
  retro, luxury, playful...), commit to it in typography, color, layout, and motion.
- Real content: specific headlines, copy, labels, and sample data written for this request.
  No lorem ipsum, no "Feature 1", no TODO comments, no unimplemented buttons.
- Every visible control must work. Include meaningful interactivity and responsive layout.
- Entry point is `index.html`. Put styles in `style.css` and behavior in `app.js`, linked with
  `<link rel="stylesheet" href="style.css">` and `<script src="app.js" defer></script>`.
  Add more files only if they genuinely help. Relative paths only.
- Must run by opening index.html directly from disk. Third-party libraries only from a CDN
  (https://cdn.jsdelivr.net, https://unpkg.com, https://cdnjs.cloudflare.com) and only when needed.
- Write complete files. Never abbreviate with "..." or "rest of code here".

Output format (nothing before the first block, nothing after the last):
===FILE: index.html===
<full file contents>
===END FILE===
===FILE: style.css===
<full file contents>
===END FILE===
===FILE: app.js===
<full file contents>
===END FILE===
"""


@dataclass
class SynthesisResult:
    files: list[dict[str, str]] = field(default_factory=list)
    ok: bool = False
    route: str = ""
    error: str = ""
    attempts: int = 0
    notes: list[str] = field(default_factory=list)


def _clean_path(raw: str) -> str | None:
    cleaned = raw.strip().strip("`'\"").replace("\\", "/").lstrip("./")
    if not cleaned or cleaned.startswith("/") or ":" in cleaned:
        return None
    parts = PurePosixPath(cleaned).parts
    if any(p in ("..", "") for p in parts):
        return None
    if cleaned in ("mercbot.app.json", "bundle.preview.html"):
        return None
    return cleaned


def parse_file_blocks(text: str) -> list[dict[str, str]]:
    """Extract `{path, content}` files from a model response."""
    files: dict[str, str] = {}
    for match in _FILE_BLOCK.finditer(text or ""):
        path = _clean_path(match.group("path"))
        if not path:
            continue
        body = match.group("body")
        wrapped = _FENCE_WRAPPER.match(body)
        if wrapped:
            body = wrapped.group("body")
        files[path] = body.rstrip() + "\n"
    if not files:
        for match in _FENCED_LABELED.finditer(text or ""):
            path = _clean_path(match.group("path"))
            if path:
                files[path] = match.group("body").rstrip() + "\n"
    if not files:
        doc = re.search(r"(<!doctype html.*?</html>)", text or "", re.IGNORECASE | re.DOTALL)
        if doc:
            files["index.html"] = doc.group(1).strip() + "\n"
    return [{"path": p, "content": c} for p, c in list(files.items())[:MAX_FILES]]


_LOCAL_REF = re.compile(r"""(?:src|href)\s*=\s*["'](?P<ref>[^"'#?]+)""", re.IGNORECASE)


def validate_app_files(files: list[dict[str, str]]) -> list[str]:
    """Return concrete problems with a synthesized bundle (empty list means it is usable)."""
    problems: list[str] = []
    by_path = {f["path"]: f["content"] for f in files}
    html = by_path.get("index.html")
    if html is None:
        problems.append("Missing `index.html` entry point.")
        return problems
    lowered = html.lower()
    if len(html.strip()) < 200:
        problems.append("`index.html` is too short to be a real application.")
    if "<body" not in lowered:
        problems.append("`index.html` has no <body> element.")
    if "</html>" not in lowered:
        problems.append("`index.html` is truncated (no closing </html>).")
    for match in _LOCAL_REF.finditer(html):
        ref = match.group("ref").strip()
        if not ref or re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", ref, re.IGNORECASE):
            continue
        local = _clean_path(ref)
        if local and local.lower().endswith((".css", ".js", ".mjs", ".json", ".svg")) and local not in by_path:
            problems.append(f"`index.html` references `{ref}` but that file was not provided.")
    for path, content in by_path.items():
        if not content.strip():
            problems.append(f"`{path}` is empty.")
        if re.search(r"(?:\.\.\.\s*(?:rest|remaining|more) (?:of|code)|//\s*\.\.\.\s*$)", content, re.IGNORECASE | re.MULTILINE):
            problems.append(f"`{path}` contains an abbreviated placeholder instead of real code.")
        if path.endswith((".js", ".mjs")):
            if content.count("{") - content.count("}") > 2:
                problems.append(f"`{path}` looks truncated (unbalanced braces).")
        if path.endswith(".css") and content.count("{") != content.count("}"):
            problems.append(f"`{path}` looks truncated (unbalanced braces).")
    if re.search(r"lorem ipsum", " ".join(by_path.values()), re.IGNORECASE):
        problems.append("Contains lorem ipsum placeholder copy; write real content.")
    return problems


def build_verify_script(files: list[dict[str, str]]) -> str:
    """A verification script derived from the files the model actually wrote."""
    paths = sorted(f["path"] for f in files)
    return (
        "import re\n"
        "from pathlib import Path\n\n"
        f"FILES = {paths!r}\n"
        "for rel in FILES:\n"
        "    p = Path(rel)\n"
        "    assert p.is_file() and p.stat().st_size > 0, f'Missing or empty {rel}'\n\n"
        "html = Path('index.html').read_text(encoding='utf-8')\n"
        "assert '<body' in html.lower() and '</html>' in html.lower(), 'index.html is incomplete'\n"
        "for ref in re.findall(r'''(?:src|href)\\s*=\\s*[\"']([^\"'#?]+)''', html):\n"
        "    if re.match(r'^(?:[a-z][a-z0-9+.-]*:|//)', ref, re.I):\n"
        "        continue\n"
        "    target = Path(ref.lstrip('./'))\n"
        "    if target.suffix.lower() in ('.css', '.js', '.mjs', '.json', '.svg'):\n"
        "        assert target.is_file(), f'index.html references missing {ref}'\n"
        "print(f'PASS: live-synthesized bundle verified ({len(FILES)} files, all references resolved)')\n"
    )


def _user_message(display_name: str, brief: str) -> str:
    return (
        f"Project name: {display_name}\n"
        f"User request (build exactly this): {brief}\n\n"
        "Return the complete application as file blocks."
    )


def synthesize_app_with_model(
    spec: FrontierModelSpec,
    *,
    display_name: str,
    brief: str,
    api_keys: dict[str, str] | None = None,
    on_progress: Callable[[str], None] | None = None,
    call: Callable[..., Any] = call_frontier_provider,
) -> SynthesisResult:
    """Ask the selected frontier model to write the application, validating and repairing once."""
    reachable, route = live_model_route(spec, api_keys)
    result = SynthesisResult(route=route)
    if not reachable:
        result.error = route
        return result

    def progress(msg: str) -> None:
        result.notes.append(msg)
        if on_progress:
            on_progress(msg)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_message(display_name, brief)},
    ]
    for attempt in (1, 2):
        result.attempts = attempt
        progress(f"[{spec.name}] Writing application files via {route} (attempt {attempt}/2)...")
        try:
            resp = call(
                spec,
                messages=messages,
                tools=[],
                api_keys=api_keys,
                timeout=SYNTHESIS_TIMEOUT_S,
                allow_offline_fallback=False,
                max_output_tokens=SYNTHESIS_MAX_OUTPUT_TOKENS,
            )
        except Exception as exc:
            result.error = f"{spec.id} call failed: {exc}"
            return result
        content = str(getattr(resp, "content", "") or "")
        files = parse_file_blocks(content)
        problems = validate_app_files(files) if files else ["No file blocks found in the response."]
        if not problems:
            files.append(
                {
                    "path": "verify_custom.py",
                    "description": "Verification derived from the synthesized files",
                    "content": build_verify_script(files),
                }
            )
            for f in files:
                f.setdefault("description", f"Written by {spec.name}")
            result.files = files
            result.ok = True
            progress(f"[{spec.name}] Produced {len(files) - 1} application files.")
            return result
        progress(f"[{spec.name}] Output rejected: {'; '.join(problems)}")
        messages.append({"role": "assistant", "content": content[:60000]})
        messages.append(
            {
                "role": "user",
                "content": (
                    "That output cannot ship:\n- "
                    + "\n- ".join(problems)
                    + "\n\nResend the COMPLETE application (every file, full contents) using the exact "
                    "===FILE: path=== / ===END FILE=== format."
                ),
            }
        )
    result.error = f"{spec.id} output failed validation twice: {'; '.join(problems)}"
    return result
