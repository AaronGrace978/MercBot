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
