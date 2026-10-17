import pytest

from mercury.providers import (
    FrontierOnlyError,
    ProviderId,
    get_frontier_model,
    list_frontier_models,
)
from mercury.runtime import MercuryAgentRuntime
from mercury.server import MercuryBridge
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
    from mercury.templates import infer_template_from_prompt, list_build_templates, list_built_apps

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
    from mercury.runtime import IterationLimitExceededError, compute_line_overlap

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
    from mercury.providers import get_frontier_model

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
    import mercury.providers as providers
    from mercury.providers import NetworkDropError, call_frontier_provider, get_frontier_model

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



