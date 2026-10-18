import json

import pytest

pytest.importorskip("mercury_runtime")

from mercury import MercuryHarness
from mercury_runtime import MercuryAgentRuntime
from mercury_runtime.ab import AB_LOG_NAME, run_ab
from mercury.cli import main
from mercury.demo import frontier_auth_fix
from mercury.models import ToolCall
from mercury_runtime.providers import FrontierOnlyError, ProviderTurnResponse


def _turn(*calls, text=""):
    return ProviderTurnResponse(
        content=text,
        tool_calls=[ToolCall(name=n, arguments=a, call_id=f"c{i}") for i, (n, a) in enumerate(calls)],
    )


class _FakeModel:
    """Disciplined with a system prompt, careless without one."""

    def __init__(self):
        self.first_messages = []

    def __call__(self, spec, messages, tools=None, **kwargs):
        step = sum(1 for m in messages if m["role"] == "assistant")
        has_system = any(m["role"] == "system" for m in messages)
        if step == 0:
            self.first_messages.append([dict(m) for m in messages])
        if has_system:
            script = [
                _turn(("grep", {"pattern": "greeting", "path": "."})),
                _turn(("read", {"path": "app.py"}), ("read", {"path": "test_app.py"})),
                _turn(("search_replace", {"path": "app.py", "old_string": "hello", "new_string": "hi"})),
                _turn(("shell", {"command": "echo ok"})),
            ]
        else:
            script = [_turn(("search_replace", {"path": "app.py", "old_string": "hello", "new_string": "hi"}))]
        return script[step] if step < len(script) else _turn(text="Changed the greeting in app.py")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "app.py").write_text("GREETING = 'hello'\n", encoding="utf-8")
    (ws / "test_app.py").write_text("def test_greeting():\n    assert True\n", encoding="utf-8")
    monkeypatch.chdir(ws)
    return ws


def _runtime(tmp_path):
    harness = MercuryHarness.init(tmp_path / "store")
    harness.capture(frontier_auth_fix())
    return MercuryAgentRuntime(harness, store_path=tmp_path / "store")


def test_control_arm_has_no_system_prompt_and_pack_arm_does(tmp_path, workspace, monkeypatch):
    fake = _FakeModel()
    monkeypatch.setattr("mercury_runtime.runtime.call_frontier_provider", fake)
    runtime = _runtime(tmp_path)
    result = run_ab(
        runtime,
        "Change the greeting in app.py",
        model="gpt-4o-mini",
        mode="live",
        sandbox_root=tmp_path / "ab",
    )

    pack_first, control_first = fake.first_messages
    assert pack_first[0]["role"] == "system" and "Mercury" in pack_first[0]["content"]
    assert [m["role"] for m in control_first] == ["user"]
    assert control_first[0]["content"] == "Change the greeting in app.py"

    assert result.measurable
    assert result.with_pack.injected_pack is not None
    assert result.control.injected_pack is None
    assert result.pack_grade.policy_score > result.control_grade.policy_score
    assert result.as_dict()["delta"]["policy"] > 0
    assert "explored_first" in result.as_dict()["delta"]["newly_passed"]


def test_arms_run_in_isolated_copies_and_leave_the_store_and_workspace_alone(tmp_path, workspace, monkeypatch):
    monkeypatch.setattr("mercury_runtime.runtime.call_frontier_provider", _FakeModel())
    runtime = _runtime(tmp_path)
    traces_before = runtime.harness.stats()["traces"]
    cards_before = runtime.harness.stats()["cards"]
    result = run_ab(runtime, "Change the greeting in app.py", model="gpt-4o-mini", mode="live", sandbox_root=tmp_path / "ab")

    assert (workspace / "app.py").read_text(encoding="utf-8") == "GREETING = 'hello'\n"
    from pathlib import Path

    run_dir = Path(result.sandbox_dir)
    for arm in ("pack", "control"):
        assert (run_dir / arm / "app.py").read_text(encoding="utf-8") == "GREETING = 'hi'\n"
    assert runtime.harness.stats()["traces"] == traces_before
    assert runtime.harness.stats()["cards"] == cards_before
    assert runtime.workspace_root == workspace.resolve()


def test_synth_mode_is_flagged_not_measurable(tmp_path, workspace):
    runtime = _runtime(tmp_path)
    result = run_ab(runtime, "Fix the login redirect", model="gpt-4o-mini", mode="synth", sandbox_root=tmp_path / "ab")
    assert not result.measurable
    assert "does not call the model" in result.caveat
    assert "NOT MEASURABLE" in result.summary()


def test_cli_no_pack_prints_side_by_side_and_logs(tmp_path, workspace, monkeypatch, capsys):
    monkeypatch.setattr("mercury_runtime.runtime.call_frontier_provider", _FakeModel())
    store = tmp_path / "s"
    code = main(["--store", str(store), "run", "--no-pack", "--task", "Change the greeting in app.py", "--mode", "live"])
    out = capsys.readouterr().out
    assert code == 0
    assert "control" in out and "pack" in out and "delta" in out
    assert "policy floor" in out
    records = [json.loads(line) for line in (store / AB_LOG_NAME).read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["model"] == "gpt-4o-mini"
    assert records[0]["pack"]["score"] != records[0]["control"]["score"]

    code = main(["--store", str(store), "run", "--no-pack", "--task", "Change the greeting in app.py", "--mode", "live", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["measurable"] is True
    assert len((store / AB_LOG_NAME).read_text(encoding="utf-8").splitlines()) == 2


def test_plain_run_still_rejects_student_models(tmp_path, workspace):
    runtime = _runtime(tmp_path)
    with pytest.raises(FrontierOnlyError):
        runtime.run("Fix the login redirect", model="gpt-4o-mini", mode="synth")
