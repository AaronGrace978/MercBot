import pytest

pytest.importorskip("mercury_forge")

from mercury_runtime.providers import (
    FrontierOnlyError,
    ProviderId,
    get_frontier_model,
    list_frontier_models,
)
from mercury_runtime.runtime import MercuryAgentRuntime
from mercury_forge.server import MercuryBridge
from mercury.tiers import ModelTier, classify_model


def test_only_frontier_models_listed():
    models = list_frontier_models()
    assert len(models) >= 15
    # Every single model in the catalog MUST be ModelTier.FRONTIER
    for spec in models:
        assert spec.tier is ModelTier.FRONTIER
        assert classify_model(spec.id) is ModelTier.FRONTIER

    ids = {m.id for m in models}
    # Google Gemini Argon must be present
    assert "gemini-4-argon-high" in ids
    assert "gemini-4-argon" in ids
    # Ollama Cloud flagships must be present
    assert "deepseek-v4-pro:cloud" in ids
    assert "kimi-k3:cloud" in ids
    assert "glm-5.3:cloud" in ids
    assert "minimax-m3:cloud" in ids
    assert "qwen3.5:397b-cloud" in ids
    assert "gpt-oss:120b-cloud" in ids
    # Lesser and mid-tier models must NOT be in the catalog
    for banned in ("gpt-4o-mini", "claude-haiku-4", "gemini-3.5-flash", "claude-sonnet-4", "gpt-oss:20b-cloud"):
        assert banned not in ids


def test_rejects_non_frontier_models():
    for non_frontier in ("gpt-4o-mini", "claude-sonnet-4", "gemini-3.5-flash", "gpt-5.6-luna", "gpt-oss:20b-cloud"):
        with pytest.raises(FrontierOnlyError):
            get_frontier_model(non_frontier)


def test_provider_filtering():
    google_models = list_frontier_models(ProviderId.GOOGLE)
    assert all(m.provider is ProviderId.GOOGLE for m in google_models)
    assert any("argon" in m.id for m in google_models)

    ollama_models = list_frontier_models(ProviderId.OLLAMA_CLOUD)
    assert len(ollama_models) >= 6
    assert all(m.is_ollama_cloud for m in ollama_models)


def test_agent_runtime_executes_and_distills(tmp_path):
    store_dir = tmp_path / ".mercury"
    runtime = MercuryAgentRuntime(store_path=store_dir, default_model="gemini-4-argon-high")

    res = runtime.run(
        "Login keeps redirecting back to /login after a successful password check",
        model="gemini-4-argon-high",
        mode="synth",
    )
    assert res.model_spec.id == "gemini-4-argon-high"
    assert res.trace.tier is ModelTier.FRONTIER
    assert res.grade.score >= 0.85
    assert res.grade.policy_score == 1.0
    assert res.grade.competence_score == 1.0
    assert len(res.distilled_cards) >= 4
    assert runtime.harness.stats()["traces"] >= 1


def test_agent_runtime_ollama_cloud_and_rejection(tmp_path):
    store_dir = tmp_path / ".mercury"
    runtime = MercuryAgentRuntime(store_path=store_dir)

    res = runtime.run(
        "Fix flaky billing test",
        model="kimi-k3:cloud",
        mode="synth",
    )
    assert res.model_spec.provider is ProviderId.OLLAMA_CLOUD
    assert res.trace.tier is ModelTier.FRONTIER

    with pytest.raises(FrontierOnlyError):
        runtime.run("Attempt with lesser model", model="gpt-4o-mini")


def test_bridge_state_and_operations(tmp_path):
    bridge = MercuryBridge(store_path=tmp_path / ".mercury")
    state = bridge.get_state()
    assert len(state["models"]) >= 15
    assert state["stats"]["traces"] >= 2
    assert state["stats"]["cards"] >= 5

    run_out = bridge.run_agent(
        {
            "task": "Verify Gemini Argon tier classification",
            "model": "deepseek-v4-pro:cloud",
            "mode": "synth",
        }
    )
    assert run_out["run"]["model"]["id"] == "deepseek-v4-pro:cloud"
    assert run_out["run"]["grade"]["score"] >= 0.85


def test_app_templates_and_build_forge(tmp_path):
    from mercury_forge.templates import infer_template_from_prompt, list_build_templates, list_built_apps

    templates = list_build_templates()
    template_ids = {t.id for t in templates}
    assert {
        "acid-synth-web",
        "neon-vault-api",
        "tauri-punk-starter",
        "frontier-agent-cli",
        "cyber-kanban-board",
        "custom-prompt-app",
    }.issubset(template_ids)

    assert infer_template_from_prompt("Build a 303 acid bassline synth")[0] == "acid-synth-web"
    assert infer_template_from_prompt("Create a cyberpunk kanban board")[0] == "cyber-kanban-board"
    assert infer_template_from_prompt("Build a custom telemetry matrix")[0] == "custom-prompt-app"

    store_dir = tmp_path / ".mercury"
    out_dir = tmp_path / "workspaces"
    runtime = MercuryAgentRuntime(store_path=store_dir, workspace_root=tmp_path)

    for tpl_id in (
        "acid-synth-web",
        "neon-vault-api",
        "tauri-punk-starter",
        "frontier-agent-cli",
        "cyber-kanban-board",
        "custom-prompt-app",
    ):
        res = runtime.build_template(
            tpl_id,
            project_name=f"Test {tpl_id}",
            custom_prompt="Include full smoke test verification",
            model="gemini-4-argon-high",
            output_root=out_dir,
        )
        art = res["artifact"]
        assert art["verification_passed"] is True, f"Template {tpl_id} failed verification: {art['verification_output']}"
        assert len(art["files_written"]) >= 1
        assert len(art["preview_html"]) > 200
        assert res["grade"]["score"] >= 0.85
        assert len(res["distilled_cards"]) >= 4

    # Freeform build prompt through runtime.run() should auto-forge and attach built_app
    run_res = runtime.run(
        "Build a custom neural telemetry studio with live matrix nodes",
        model="gemini-4-argon-high",
        mode="synth",
    )
    assert run_res.built_app is not None
    assert run_res.built_app["verify_passed"] is True
    assert len(run_res.built_app["preview_html"]) > 200

    persisted = list_built_apps(out_dir)
    assert len(persisted) >= 7


def test_stateful_iteration_limiter_and_soft_pivot(tmp_path):
    """Verify >3 sequential edits with >50% line overlap throws IterationLimitExceededError."""
    from mercury.models import ToolCall
    from mercury_runtime.runtime import IterationLimitExceededError, compute_line_overlap

    runtime = MercuryAgentRuntime(
        store_path=tmp_path / ".mercury",
        workspace_root=tmp_path,
    )

    base_code = "\n".join(
        [
            "def authenticate(user, password):",
            "    if not user or not password:",
            "        return None",
            "    token = issue_token(user)",
            "    return {'token': token, 'sameSite': 'Strict'}",
        ]
    )
    variant_1 = base_code + "\n# edit 1"
    variant_2 = base_code + "\n# edit 2"
    variant_3 = base_code + "\n# edit 3"

    assert compute_line_overlap(base_code.splitlines(), variant_1.splitlines()) > 0.50

    # Edits 1, 2, 3 on the same path succeed
    runtime.record_file_edit("src/auth/session.py", base_code)
    runtime.record_file_edit("src/auth/session.py", variant_1)
    runtime.record_file_edit("src/auth/session.py", variant_2)

    # 4th sequential edit (>3 sequential edits) with >50% line overlap raises IterationLimitExceededError
    with pytest.raises(IterationLimitExceededError) as exc_info:
        runtime.record_file_edit("src/auth/session.py", variant_3)

    assert exc_info.value.file_path == "src/auth/session.py"
    assert exc_info.value.sequential_edits == 4
    assert exc_info.value.overlap_ratio > 0.50
    assert len(runtime.rejected_pathways) >= 1

    # Also verify _execute_tool_with_guard catches the soft internal exception during agent loop
    output, is_err, loop_exc = runtime._execute_tool_with_guard(
        ToolCall(
            name="edit",
            arguments={"path": "src/auth/session.py", "new": variant_3},
        )
    )
    assert is_err is True
    assert loop_exc is not None
    assert "ITERATION_LIMIT_EXCEEDED" in output
    assert len(runtime.recovery_injections) >= 1


def test_prompt_driven_reject_buffer_injection(tmp_path):
    """Verify # REJECTED PATHWAYS section is dynamically injected into frontier system prompts."""
    from mercury_runtime.providers import get_frontier_model

    runtime = MercuryAgentRuntime(
        store_path=tmp_path / ".mercury",
        workspace_root=tmp_path,
    )
    runtime.rejected_pathways.append(
        "src/auth/login.tsx (overlap=88%): window.location.href = '/dashboard'"
    )

    for model_id in ("gemini-4-argon-high", "gpt-5.6-sol-high"):
        spec = get_frontier_model(model_id)
        sys_prompt = runtime.assemble_system_prompt(
            spec,
            "Fix the authentication redirect loop",
        )
        assert "# REJECTED PATHWAYS" in sys_prompt
        assert "Do not output these structural blocks again." in sys_prompt
        assert "src/auth/login.tsx" in sys_prompt


def test_specification_anchored_verification_in_build_pipeline(tmp_path):
    """Verify mercury build generates/reads SPEC.md before editing files and verifies against it."""
    store_dir = tmp_path / ".mercury"
    out_dir = tmp_path / "workspaces"
    runtime = MercuryAgentRuntime(store_path=store_dir, workspace_root=tmp_path)

    res = runtime.build_template(
        "neon-vault-api",
        project_name="Spec Anchored Vault",
        custom_prompt="Enforce strict SPEC.md architectural verification",
        model="gemini-4-argon-high",
        output_root=out_dir,
    )
    artifact = res["artifact"]
    assert "SPEC.md" in artifact["files_written"]
    assert "SPEC.md" in artifact["file_contents"]
    assert artifact["spec_verification"] is not None
    assert artifact["spec_verification"]["passed"] is True
    assert "SPEC.md" in artifact["spec_verification"]["summary"]
    assert "PASS" in artifact["spec_verification"]["summary"]

    # Ensure the agent trace explicitly read SPEC.md before modifying files
    trace_events = res["trace"]["events"]
    tool_events = [
        tc
        for ev in trace_events
        for tc in ev.get("tool_calls", [])
    ]
    read_paths = [
        tc["arguments"].get("path")
        for tc in tool_events
        if tc["name"] == "read"
    ]
    write_indices = [
        idx
        for idx, tc in enumerate(tool_events)
        if tc["name"] in ("write_file", "write", "edit", "search_replace")
    ]
    spec_read_indices = [
        idx
        for idx, tc in enumerate(tool_events)
        if tc["name"] == "read" and tc["arguments"].get("path") == "SPEC.md"
    ]
    assert "SPEC.md" in read_paths
    assert spec_read_indices[0] < write_indices[0]


def test_offline_mode_enforcement_fallback_routing(tmp_path, monkeypatch):
    """Verify network drops on primary cloud endpoints route seamlessly to Ollama Cloud / Local Titan."""
    import mercury_runtime.providers as providers
    from mercury_runtime.providers import NetworkDropError, call_frontier_provider, get_frontier_model

    spec = get_frontier_model("gemini-4-argon-high")

    def simulated_network_drop(*args, **kwargs):
        raise NetworkDropError("Simulated primary cloud endpoint timeout (HTTP 504)")

    monkeypatch.setattr(providers, "_dispatch_provider", simulated_network_drop)

    result = call_frontier_provider(
        spec,
        messages=[
            {"role": "system", "content": "You are a frontier coding agent."},
            {"role": "user", "content": "Fix the login redirect loop in session.py"},
        ],
    )
    assert result["offline_routed"] is True
    assert "content" in result
    assert len(result["tool_calls"]) >= 1


def test_chunked_event_streaming_bridge(tmp_path):
    """Verify MercuryBridge emits real-time token and terminal chunks bit-by-bit."""
    bridge = MercuryBridge(workspace_root=tmp_path)
    chunks = []

    res = bridge.run_agent(
        {
            "task": "Fix the flaky billing test in test_billing.py",
            "model": "gemini-4-argon-high",
            "mode": "synth",
        },
        on_stream=lambda chunk: chunks.append(chunk),
    )
    assert res["run"]["grade"]["score"] >= 0.85
    chunk_types = {c["type"] for c in chunks}
    assert "trace_event" in chunk_types
    assert "token" in chunk_types or "terminal_chunk" in chunk_types


def test_prompt_driven_app_synthesis_builds_requested_app(tmp_path):
    """Verify 'Build a NotePad' and 'Build a Calculator' actually synthesize a real Notepad and Calculator."""
    runtime = MercuryAgentRuntime(
        store_path=tmp_path / ".mercury",
        workspace_root=tmp_path,
    )

    notepad_res = runtime.run(
        "Build a NotePad",
        model="deepseek-v4-pro:cloud",
        mode="synth",
    )
    assert notepad_res.built_app is not None
    assert notepad_res.built_app["verify_passed"] is True
    assert "noteEditor" in notepad_res.built_app["preview_html"]
    assert "noteTitleInput" in notepad_res.built_app["preview_html"]
    assert "notesList" in notepad_res.built_app["preview_html"]
    assert "simCanvas" not in notepad_res.built_app["preview_html"]

    calc_res = runtime.run(
        "Build a Scientific Calculator",
        model="gemini-4-argon-high",
        mode="synth",
    )
    assert calc_res.built_app is not None
    assert calc_res.built_app["verify_passed"] is True
    assert "calcDisplay" in calc_res.built_app["preview_html"]
    assert "calcKeypad" in calc_res.built_app["preview_html"]
    assert "historyTape" in calc_res.built_app["preview_html"]


def test_webgl_prompt_builds_the_named_subject():
    """A 3D prompt must build the named subject, not the generic core mesh."""
    from mercury_forge.prompt_forge import _build_webgl_3d_files
    from mercury_forge.webgl_subject import resolve_webgl_subject

    chicken = resolve_webgl_subject("Build a 3d Chicken in WebGL")
    assert chicken["family"] == "bird"
    assert chicken["token"] == "chicken"
    assert "comb" in chicken["features"]

    files = _build_webgl_3d_files("3d Chicken In Webgl", "Build a 3d Chicken in WebGL", "kimi-k3:cloud")
    html = next(item["content"] for item in files if item["path"] == "index.html")
    js = next(item["content"] for item in files if item["path"] == "app.js")
    assert "MESH: CHICKEN" in html
    assert "function buildBird" in js
    assert "IcosahedronGeometry" in js
    assert "WebGLRenderer" in js

    dino = resolve_webgl_subject("Build me a 3D webGL of a Punk DinoBuddy with a mohawk")
    assert dino["family"] == "dino"
    assert dino["name"] == "Dino Mohawk"

    assert resolve_webgl_subject("Create a 3d cat")["family"] == "quadruped"
    assert resolve_webgl_subject("forge a 3d spaceship")["family"] == "vehicle"
    assert resolve_webgl_subject("make a 3d house")["family"] == "structure"
    assert resolve_webgl_subject("Build a 3d webgl visualizer")["family"] == "core"
    dragon = resolve_webgl_subject("build a red dragon")
    assert dragon["family"] == "serpent"
    assert dragon["colors"]["body"] == 0xE10600


def test_landing_page_prompt_is_not_crud_domain_studio(tmp_path):
    """Landing / generative UI prompts must ship a real marketing page, not the CRUD stub."""
    from mercury_forge.prompt_forge import detect_prompt_archetype
    from mercury_runtime.runtime import MercuryAgentRuntime

    assert (
        detect_prompt_archetype(
            "Cool Cyberpunk Generative Ui",
            "Build me a Cool CyberPunk Generative Ui landing page",
        )
        == "landing_page"
    )
    assert detect_prompt_archetype("Coffee Shop", "make a minimal coffee shop website") == "landing_page"
    assert detect_prompt_archetype("Ops Console", "build an analytics dashboard") == "dashboard"

    runtime = MercuryAgentRuntime(
        store_path=tmp_path / ".mercury",
        workspace_root=tmp_path,
    )
    res = runtime.run(
        "Build me a Cool CyberPunk Generative Ui landing page",
        model="gemini-4-argon-high",
        mode="synth",
    )
    assert res.built_app is not None
    assert res.built_app["verify_passed"] is True
    preview = res.built_app["preview_html"]
    assert "domainList" not in preview
    assert "createItemBtn" not in preview
    assert "hero" in preview.lower() or "Generate" in preview
    assert "cyber" in preview.lower() or "neon" in preview.lower() or "#ff2bd6" in preview


def test_live_workspace_edits_auto_sync_bundle_preview(tmp_path):
    """Verify bundle.preview.html and mercbot.app.json recompile when index.html/app.js are updated on disk."""
    from mercury_forge.templates import list_built_apps, sync_workspace_manifest

    runtime = MercuryAgentRuntime(
        store_path=tmp_path / ".mercury",
        workspace_root=tmp_path,
    )
    webgl_res = runtime.run(
        "Build me a 3D webGL of a Punk DinoBuddy with a mohawk",
        model="gemini-4-argon-high",
        mode="synth",
    )
    assert webgl_res.built_app is not None
    assert "WebGLRenderer" in webgl_res.built_app["preview_html"]
    ws_dir = tmp_path / "workspaces" / webgl_res.built_app["project_slug"]

    # Simulate a live model editing app.js on disk after initial build
    (ws_dir / "app.js").write_text(
        'console.log("CUSTOM_THREEJS_ICOSAHEDRON_LIVE_UPDATE");',
        encoding="utf-8",
    )

    apps = list_built_apps(tmp_path / "workspaces")
    assert len(apps) == 1
    assert "CUSTOM_THREEJS_ICOSAHEDRON_LIVE_UPDATE" in apps[0]["preview_html"]
    assert "CUSTOM_THREEJS_ICOSAHEDRON_LIVE_UPDATE" in (ws_dir / "bundle.preview.html").read_text(encoding="utf-8")

    synced = sync_workspace_manifest(ws_dir, force_recompile=True)
    assert synced is not None
    assert "CUSTOM_THREEJS_ICOSAHEDRON_LIVE_UPDATE" in synced["preview_html"]





