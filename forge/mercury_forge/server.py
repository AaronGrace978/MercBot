"""HTTP & JSON-RPC bridge for the MercBot Tauri Punk Desktop App and CLI."""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from mercury.demo import frontier_auth_fix, frontier_pytest_fix, lesser_auth_fail
from mercury.grade import grade_delta, grade_trace
from mercury.harness import MercuryHarness
from mercury.inject import build_pack
from mercury.phases import segment_phases
from mercury_runtime.providers import (
    FrontierOnlyError,
    list_frontier_models,
    list_providers,
)
from mercury_runtime.runtime import MercuryAgentRuntime
from mercury_forge.templates import (
    build_app_from_template,
    infer_template_from_prompt,
    launch_built_app,
    list_build_templates,
    list_built_apps,
)


class SSEBroadcaster:
    """Thread-safe Server-Sent Events (SSE) broadcaster for chunked token and terminal streaming."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[dict[str, Any] | None]] = []

    def subscribe(self) -> queue.Queue[dict[str, Any] | None]:
        q: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=1024)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any] | None]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except queue.Empty:
                    pass


class MercuryBridge:
    """Stateless/stateful controller backing both Tauri IPC commands and the local HTTP server."""

    def __init__(
        self,
        store_path: str | Path = ".mercury",
        workspace_root: str | Path = ".",
    ) -> None:
        self.store_path = Path(store_path)
        self.workspace_root = Path(workspace_root).resolve()
        self.harness = MercuryHarness.init(self.store_path)
        self.runtime = MercuryAgentRuntime(
            self.harness,
            store_path=self.store_path,
            workspace_root=self.workspace_root,
            default_model="gemini-4-argon-high",
            allow_writes=True,
        )
        self.broadcaster = SSEBroadcaster()
        self.built_apps: list[dict[str, Any]] = []
        # Ensure initial seed traces exist so the dashboard is immediately alive
        if self.harness.stats()["traces"] == 0:
            self.seed_default_traces()

    def seed_default_traces(self) -> dict[str, Any]:
        teacher_auth = frontier_auth_fix()
        # Upgrade default teacher trace to Gemini 4 Argon High & Ollama Cloud Kimi K3
        argon_trace = teacher_auth.model_copy(
            update={
                "id": "trace_gemini_4_argon_auth",
                "model": "gemini-4-argon-high",
            }
        )
        ollama_trace = frontier_pytest_fix().model_copy(
            update={
                "id": "trace_kimi_k3_cloud_pytest",
                "model": "kimi-k3:cloud",
            }
        )
        student_fail = lesser_auth_fail()
        self.harness.capture(argon_trace, force_teacher=True)
        self.harness.capture(ollama_trace, force_teacher=True)
        self.harness.contrast(student_fail, argon_trace)
        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        traces = self.harness.store.traces()
        enriched_traces: list[dict[str, Any]] = []
        for tr in reversed(traces):
            grade = grade_trace(tr)
            phases = [
                {
                    "name": p.name,
                    "summary": p.summary(),
                    "tools": p.tool_names(),
                }
                for p in segment_phases(tr)
            ]
            enriched_traces.append(
                {
                    **tr.model_dump(),
                    "tier": tr.tier.value,
                    "task_type": tr.task_type.value,
                    "grade": grade.as_dict(),
                    "phases": phases,
                }
            )

        cards = [
            {
                **c.model_dump(),
                "effective_confidence": round(c.effective_confidence, 4),
                "reinforcement_bonus": round(c.reinforcement_bonus, 4),
                "estimated_tokens": c.estimated_tokens(),
            }
            for c in self.harness.store.cards()
        ]
        return {
            "models": [m.model_dump() for m in list_frontier_models()],
            "providers": list_providers(),
            "templates": [t.model_dump() for t in list_build_templates()],
            "built_apps": list_built_apps(self.workspace_root / "workspaces"),
            "stats": self.harness.stats(),
            "traces": enriched_traces,
            "cards": cards,
        }

    def _make_stream_emitter(
        self,
        on_stream: Callable[[dict[str, Any]], None] | None = None,
    ) -> Callable[[dict[str, Any]], None]:
        def _emit(chunk: dict[str, Any]) -> None:
            self.broadcaster.publish(chunk)
            if on_stream is not None:
                on_stream(chunk)

        return _emit

    def build_app(
        self,
        payload: dict[str, Any],
        *,
        on_stream: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        template_id = str(payload.get("template_id") or "auto").strip()
        project_name = str(payload.get("project_name") or "").strip()
        custom_prompt = str(payload.get("custom_prompt") or "").strip()
        model = str(payload.get("model") or "gemini-4-argon-high").strip()
        mode = str(payload.get("mode") or "auto").strip().lower() or "auto"
        if mode not in ("auto", "synth", "live"):
            mode = "auto"
        auto_launch = bool(payload.get("launch", False))
        api_keys = payload.get("api_keys") if isinstance(payload.get("api_keys"), dict) else None
        output_root = self.workspace_root / "workspaces"
        emitter = self._make_stream_emitter(on_stream)

        if template_id in ("auto", "prompt", "freeform", ""):
            inferred_tpl, inferred_title = infer_template_from_prompt(custom_prompt or project_name or "Custom App")
            template_id = inferred_tpl
            if not project_name:
                project_name = inferred_title

        artifact, trace, grade, cards = build_app_from_template(
            self.runtime,
            template_id=template_id,
            project_name=project_name,
            custom_prompt=custom_prompt,
            model=model,
            output_root=output_root,
            api_keys=api_keys,
            mode=mode,
            on_stream=emitter,
        )
        art_dict = artifact.as_dict()
        launch_info = None
        if auto_launch:
            try:
                launch_info = launch_built_app(
                    artifact.project_slug,
                    target="window",
                    output_root=output_root,
                )
            except Exception as exc:
                launch_info = {"launched": False, "error": str(exc)}
        res = {
            "build": art_dict,
            "launch": launch_info,
            "trace": trace.model_dump(),
            "grade": grade.as_dict(),
            "distilled_cards": [c.model_dump() for c in cards],
            "state": self.get_state(),
        }
        emitter({"type": "complete", "kind": "build", "trace_id": trace.id, "timestamp": time.time()})
        return res

    def launch_app(self, payload: dict[str, Any]) -> dict[str, Any]:
        slug = str(payload.get("project_slug") or payload.get("slug") or "").strip()
        target = str(payload.get("target") or "window").strip()
        output_root = self.workspace_root / "workspaces"
        if not slug:
            existing = list_built_apps(output_root)
            if not existing:
                raise ValueError("No forged applications found in workspaces/. Build an app first!")
            slug = str(existing[0]["project_slug"])
        info = launch_built_app(slug, target=target, output_root=output_root)
        return {
            "launch": info,
            "state": self.get_state(),
        }

    def run_agent(
        self,
        payload: dict[str, Any],
        *,
        on_stream: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        task = str(payload.get("task") or "Audit the Mercury tier classifier and verify frontier markers pass pytest").strip()
        model = str(payload.get("model") or "gemini-4-argon-high").strip()
        mode = str(payload.get("mode") or "auto").strip()
        api_keys = payload.get("api_keys") if isinstance(payload.get("api_keys"), dict) else None
        emitter = self._make_stream_emitter(on_stream)

        result = self.runtime.run(
            task,
            model=model,
            mode=mode,
            api_keys=api_keys,
            inject_pack=True,
            auto_capture=True,
            on_stream=emitter,
        )
        out = {
            "run": result.as_dict(),
            "state": self.get_state(),
        }
        emitter({"type": "complete", "kind": "run", "trace_id": result.trace.id, "timestamp": time.time()})
        return out

    def run_contrast(self, payload: dict[str, Any]) -> dict[str, Any]:
        teacher_model = str(payload.get("teacher_model") or "gemini-4-argon-high").strip()
        teacher = frontier_auth_fix().model_copy(
            update={
                "id": f"trace_teacher_{teacher_model.replace(':', '_')}",
                "model": teacher_model,
            }
        )
        student = lesser_auth_fail()
        cards = self.harness.contrast(student, teacher)
        delta = grade_delta(student, teacher)
        return {
            "contrast_cards": [c.model_dump() for c in cards],
            "delta": delta.as_dict(),
            "state": self.get_state(),
        }

    def compile_pack(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = str(payload.get("task") or "Users bounce back to /login after authenticating").strip()
        model = str(payload.get("model") or "gpt-4o-mini").strip()
        error_sig = payload.get("error_signature") or None
        budget = payload.get("token_budget")
        pack = build_pack(
            self.harness.store,
            task,
            embedder=self.harness.embedder,
            model=model,
            error_signature=str(error_sig) if error_sig else None,
            token_budget=int(budget) if budget else 1800,
        )
        return {
            "task": pack.task,
            "model": pack.model,
            "tier": pack.tier.value,
            "token_budget": pack.token_budget,
            "estimated_tokens": pack.estimated_tokens(),
            "markdown": pack.render(),
            "cursor_rule": pack.as_cursor_rule(),
            "sft": pack.as_finetune_rows(),
            "dpo": pack.as_dpo_rows(),
            "cards": [c.model_dump() for c in pack.cards],
            "scores": [round(s, 4) for s in pack.scores],
        }

    def reinforce_card(self, payload: dict[str, Any]) -> dict[str, Any]:
        card_ids = payload.get("card_ids") or []
        if isinstance(card_ids, str):
            card_ids = [card_ids]
        succeeded = bool(payload.get("succeeded", True))
        updated = self.harness.record_outcome(card_ids, succeeded=succeeded)
        return {
            "updated": updated,
            "state": self.get_state(),
        }


def serve_http(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    store_path: str | Path = ".mercury",
    workspace_root: str | Path = ".",
) -> None:
    """Start the local MercBot JSON + Server-Sent Events (SSE) API server."""
    bridge = MercuryBridge(store_path=store_path, workspace_root=workspace_root)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send_json(self, status: int, data: Any) -> None:
            body = json.dumps(data, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()

        def _begin_sse(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("Connection", "close")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
            self.end_headers()

        def _write_sse_event(self, event_name: str, payload: Any) -> None:
            serialized = json.dumps(payload, default=str)
            frame = f"event: {event_name}\ndata: {serialized}\n\n".encode("utf-8")
            self.wfile.write(frame)
            self.wfile.flush()

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send_json(200, {"ok": True})

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/api/state", "/api/status"):
                self._send_json(200, bridge.get_state())
                return
            if parsed.path == "/api/models":
                qs = parse_qs(parsed.query)
                provider = qs.get("provider", [None])[0]
                models = [m.model_dump() for m in list_frontier_models(provider)]
                self._send_json(200, {"models": models, "providers": list_providers()})
                return
            if parsed.path == "/api/templates":
                self._send_json(200, {"templates": [t.model_dump() for t in list_build_templates()]})
                return
            if parsed.path in ("/api/stream", "/api/events"):
                qs = parse_qs(parsed.query)
                once = qs.get("once", ["0"])[0] == "1"
                self._begin_sse()
                self._write_sse_event("ready", {"status": "online", "stream": "sse"})
                if once:
                    return
                sub_q = bridge.broadcaster.subscribe()
                try:
                    while True:
                        try:
                            item = sub_q.get(timeout=10.0)
                            if item is None:
                                break
                            ev_type = str(item.get("type") or "chunk")
                            self._write_sse_event(ev_type, item)
                        except queue.Empty:
                            self._write_sse_event("ping", {"ts": time.time()})
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                finally:
                    bridge.broadcaster.unsubscribe(sub_q)
                return
            self._send_json(404, {"error": f"Unknown endpoint {parsed.path}"})

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                payload = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                payload = {}

            accept = (self.headers.get("Accept") or "").lower()
            wants_sse = (
                "text/event-stream" in accept
                or bool(payload.get("stream"))
                or self.path.endswith("/stream")
            )

            try:
                if self.path in ("/api/run", "/api/run/stream"):
                    if wants_sse:
                        self._begin_sse()
                        self._write_sse_event("start", {"kind": "run", "task": payload.get("task", "")})

                        def _stream_run_chunk(chunk: dict[str, Any]) -> None:
                            try:
                                self._write_sse_event(str(chunk.get("type") or "chunk"), chunk)
                            except OSError:
                                pass

                        result = bridge.run_agent(payload, on_stream=_stream_run_chunk)
                        self._write_sse_event("result", result)
                        return
                    self._send_json(200, bridge.run_agent(payload))
                    return
                if self.path in ("/api/build", "/api/build/stream"):
                    if wants_sse:
                        self._begin_sse()
                        self._write_sse_event("start", {"kind": "build", "template_id": payload.get("template_id", "auto")})

                        def _stream_build_chunk(chunk: dict[str, Any]) -> None:
                            try:
                                self._write_sse_event(str(chunk.get("type") or "chunk"), chunk)
                            except OSError:
                                pass

                        result = bridge.build_app(payload, on_stream=_stream_build_chunk)
                        self._write_sse_event("result", result)
                        return
                    self._send_json(200, bridge.build_app(payload))
                    return
                if self.path == "/api/launch":
                    self._send_json(200, bridge.launch_app(payload))
                    return
                if self.path == "/api/contrast":
                    self._send_json(200, bridge.run_contrast(payload))
                    return
                if self.path == "/api/pack":
                    self._send_json(200, bridge.compile_pack(payload))
                    return
                if self.path == "/api/reinforce":
                    self._send_json(200, bridge.reinforce_card(payload))
                    return
                if self.path == "/api/seed":
                    self._send_json(200, bridge.seed_default_traces())
                    return
                self._send_json(404, {"error": f"Unknown POST route {self.path}"})
            except FrontierOnlyError as exc:
                if wants_sse:
                    try:
                        self._write_sse_event("error", {"error": str(exc), "code": "FRONTIER_ONLY"})
                    except OSError:
                        pass
                else:
                    self._send_json(400, {"error": str(exc), "code": "FRONTIER_ONLY"})
            except Exception as exc:
                if wants_sse:
                    try:
                        self._write_sse_event("error", {"error": str(exc)})
                    except OSError:
                        pass
                else:
                    self._send_json(500, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    server = ThreadingHTTPServer((host, port), Handler)
    lock = threading.RLock()
    orig_get_state = bridge.get_state
    orig_run_agent = bridge.run_agent
    orig_build_app = bridge.build_app
    orig_launch_app = bridge.launch_app
    orig_run_contrast = bridge.run_contrast
    orig_compile_pack = bridge.compile_pack
    orig_reinforce_card = bridge.reinforce_card
    orig_seed = bridge.seed_default_traces

    bridge.get_state = lambda: _with_lock(lock, orig_get_state)  # type: ignore[method-assign]
    bridge.run_agent = lambda p, **kw: _with_lock(lock, lambda: orig_run_agent(p, **kw))  # type: ignore[method-assign]
    bridge.build_app = lambda p, **kw: _with_lock(lock, lambda: orig_build_app(p, **kw))  # type: ignore[method-assign]
    bridge.launch_app = lambda p: _with_lock(lock, orig_launch_app, p)  # type: ignore[method-assign]
    bridge.run_contrast = lambda p: _with_lock(lock, orig_run_contrast, p)  # type: ignore[method-assign]
    bridge.compile_pack = lambda p: _with_lock(lock, orig_compile_pack, p)  # type: ignore[method-assign]
    bridge.reinforce_card = lambda p: _with_lock(lock, orig_reinforce_card, p)  # type: ignore[method-assign]
    bridge.seed_default_traces = lambda: _with_lock(lock, orig_seed)  # type: ignore[method-assign]

    print(f"MERCBOT // ACID-HARNESS SERVER ONLINE -> http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def run_stdio_bridge_worker(
    *,
    store_path: str | Path = ".mercury",
    workspace_root: str | Path = ".",
) -> None:
    """Persistent asynchronous stdio JSON-RPC worker process for desktop IPC delegation."""
    bridge = MercuryBridge(store_path=store_path, workspace_root=workspace_root)
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        req_id: Any = None
        try:
            msg = json.loads(line)
            req_id = msg.get("id")
            action = str(msg.get("action") or "state")
            payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            stream_enabled = bool(msg.get("stream", True))

            def _emit_chunk(chunk: dict[str, Any]) -> None:
                if stream_enabled:
                    sys.stdout.write(
                        json.dumps({"id": req_id, "stream_chunk": chunk}, default=str) + "\n"
                    )
                    sys.stdout.flush()

            if action == "state":
                res = bridge.get_state()
            elif action == "run":
                res = bridge.run_agent(payload, on_stream=_emit_chunk)
            elif action == "build":
                res = bridge.build_app(payload, on_stream=_emit_chunk)
            elif action == "launch":
                res = bridge.launch_app(payload)
            elif action == "templates":
                res = {"templates": [t.model_dump() for t in list_build_templates()]}
            elif action == "contrast":
                res = bridge.run_contrast(payload)
            elif action == "pack":
                res = bridge.compile_pack(payload)
            elif action == "reinforce":
                res = bridge.reinforce_card(payload)
            elif action == "seed":
                res = bridge.seed_default_traces()
            else:
                raise ValueError(f"Unknown bridge-worker action: {action}")

            sys.stdout.write(
                json.dumps({"id": req_id, "ok": True, "result": res}, default=str) + "\n"
            )
            sys.stdout.flush()
        except Exception as exc:
            sys.stdout.write(
                json.dumps({"id": req_id, "ok": False, "error": str(exc)}, default=str) + "\n"
            )
            sys.stdout.flush()


def _with_lock(lock: threading.Lock, fn: Any, *args: Any) -> Any:
    with lock:
        return fn(*args)
