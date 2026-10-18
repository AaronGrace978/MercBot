from mercury.demo import frontier_auth_fix, lesser_auth_fail
from mercury.grade import blind_retry, grade_delta, grade_trace
from mercury.models import (
    AgentTrace,
    EventType,
    OutcomeStatus,
    ToolCall,
    TraceEvent,
    TraceOutcome,
)


def test_frontier_trace_scores_high():
    report = grade_trace(frontier_auth_fix())
    passed = set(report.passed_names)
    assert "explored_first" in passed
    assert "read_before_edit" in passed
    assert "verified_after_edit" in passed
    assert "recovered_after_error" in passed
    assert "outcome_recorded" in passed
    assert "evidence_depth" in passed
    assert "phase_completeness" in passed
    assert report.score >= 0.8
    assert report.policy_score >= 0.8
    assert report.competence_score >= 0.75


def test_lesser_trace_fails_policy_checks():
    report = grade_trace(lesser_auth_fail())
    failed = set(report.failed_names)
    passed = set(report.passed_names)
    assert "explored_first" in failed
    assert "read_before_edit" in failed
    # The fixture did run a test after editing and changed its second edit,
    # so the grader must NOT punish it for those.
    assert "verified_after_edit" in passed
    assert "recovered_after_error" in passed
    assert report.score <= 0.7
    assert report.policy_score <= 0.7


def test_explore_once_then_flail_clears_floor_but_fails_ceiling():
    """A model can pass policy hygiene and still thrash — competence catches it."""
    report = grade_trace(_explore_then_flail())
    passed = set(report.passed_names)
    failed = set(report.failed_names)
    assert "explored_first" in passed
    assert "read_before_edit" in passed
    assert "verified_after_edit" in passed
    assert "outcome_recorded" in passed
    assert report.policy_score >= 0.75
    assert "no_edit_thrash" in failed or "focused_edits" in failed
    assert report.competence_score < report.policy_score
    assert report.competence_score <= 0.5


def test_grade_delta_detects_pack_effect():
    before = grade_trace(lesser_auth_fail())
    after = grade_trace(frontier_auth_fix())
    delta = grade_delta(before, after)
    assert delta.score_delta > 0
    assert delta.policy_delta > 0
    assert "explored_first" in delta.newly_passed
    payload = delta.as_dict()
    assert "score_delta" in payload
    assert payload["before"]["model"] == "gpt-4o-mini"


def test_blind_retry_failure_emits_anti_pattern_card():
    from mercury.distill import distill_trace

    cards = distill_trace(_retry_trace("y"), teacher=False)
    retry = [card for card in cards if "identical edit" in card.title]
    assert retry, "expected a blind-retry anti-pattern card"
    assert retry[0].kind.value == "anti_pattern"
    assert retry[0].rejected


def _retry_trace(new_string_two: str):
    return AgentTrace(
        id="t",
        model="gpt-4o-mini",
        task="retry loop",
        outcome=TraceOutcome(status=OutcomeStatus.FAILURE),
        events=[
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[ToolCall(name="search_replace", arguments={"path": "a.py", "old_string": "x", "new_string": "y"})],
            ),
            TraceEvent(type=EventType.TOOL, tool_name="search_replace", is_error=True, content="error"),
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[ToolCall(name="search_replace", arguments={"path": "a.py", "old_string": "x", "new_string": new_string_two})],
            ),
        ],
    )


def _explore_then_flail() -> AgentTrace:
    """Explore once, then thrash edits across many files — policy OK, competence bad."""
    events = [
        TraceEvent(type=EventType.USER, content="fix the flaky auth suite"),
        TraceEvent(
            type=EventType.ASSISTANT,
            tool_calls=[ToolCall(name="grep", arguments={"pattern": "auth"})],
        ),
        TraceEvent(type=EventType.TOOL, tool_name="grep", content="src/a.ts\nsrc/b.ts\nsrc/c.ts\nsrc/d.ts"),
        TraceEvent(
            type=EventType.ASSISTANT,
            tool_calls=[ToolCall(name="read", arguments={"path": "src/a.ts"})],
        ),
        TraceEvent(type=EventType.TOOL, tool_name="read", content="export const a = 1"),
    ]
    for path in ("src/a.ts", "src/b.ts", "src/c.ts", "src/d.ts", "src/e.ts"):
        events.append(
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[
                    ToolCall(
                        name="search_replace",
                        arguments={"path": path, "old_string": "x", "new_string": f"y-{path}"},
                    )
                ],
            )
        )
        events.append(TraceEvent(type=EventType.TOOL, tool_name="search_replace", content=f"updated {path}"))
    events.append(
        TraceEvent(
            type=EventType.ASSISTANT,
            tool_calls=[ToolCall(name="shell", arguments={"command": "pytest -q"})],
        )
    )
    events.append(TraceEvent(type=EventType.TOOL, tool_name="shell", is_error=True, content="FAILED"))
    # More thrash after verify
    for path in ("src/a.ts", "src/b.ts", "src/c.ts"):
        events.append(
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[
                    ToolCall(
                        name="search_replace",
                        arguments={"path": path, "old_string": f"y-{path}", "new_string": f"z-{path}"},
                    )
                ],
            )
        )
        events.append(TraceEvent(type=EventType.TOOL, tool_name="search_replace", content=f"updated {path}"))
    return AgentTrace(
        id="trace_explore_flail",
        model="gpt-4o-mini",
        task="Fix the flaky auth suite",
        files_touched=["src/a.ts", "src/b.ts", "src/c.ts", "src/d.ts", "src/e.ts"],
        outcome=TraceOutcome(status=OutcomeStatus.FAILURE, summary="thrashed"),
        events=events,
    )


def test_blind_retry_detects_unchanged_rerun():
    trace = _retry_trace("y")
    hit = blind_retry(trace)
    assert hit is not None
    assert "identical edit" in hit[0]
    report = grade_trace(trace)
    assert "no_blind_retry" in report.failed_names


def test_blind_retry_allows_changed_rerun():
    trace = _retry_trace("z")
    assert blind_retry(trace) is None
    report = grade_trace(trace)
    assert "no_blind_retry" in report.passed_names


def test_grade_is_deterministic():
    first = grade_trace(frontier_auth_fix())
    second = grade_trace(frontier_auth_fix())
    assert first.as_dict() == second.as_dict()


def test_grade_report_json_shape():
    report = grade_trace(lesser_auth_fail())
    data = report.as_dict()
    assert set(data) >= {
        "model",
        "task",
        "score",
        "policy_score",
        "competence_score",
        "passed",
        "failed",
        "checks",
    }
    assert 0.0 <= data["score"] <= 1.0
    assert data["checks"][0]["band"] in {"policy", "competence"}


def test_cross_harness_tool_names_grade_the_same():
    """Cursor/Claude aliases must not mis-segment relative to Mercury names."""
    mercury = _alias_trace("grep", "read", "search_replace", "shell")
    cursor = _alias_trace("rg", "read_file", "StrReplace", "run_terminal_cmd")
    claude = _alias_trace("Grep", "Read", "Edit", "Bash")
    scores = [grade_trace(trace).as_dict() for trace in (mercury, cursor, claude)]
    assert scores[0]["passed"] == scores[1]["passed"] == scores[2]["passed"]
    assert scores[0]["score"] == scores[1]["score"] == scores[2]["score"]


def _alias_trace(explore: str, read: str, edit: str, verify: str) -> AgentTrace:
    return AgentTrace(
        id=f"alias_{explore}",
        model="claude-opus-4.1",
        task="alias normalization",
        outcome=TraceOutcome(status=OutcomeStatus.SUCCESS),
        events=[
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[ToolCall(name=explore, arguments={"pattern": "x"})],
            ),
            TraceEvent(type=EventType.TOOL, tool_name=explore, content="a.py:1"),
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[ToolCall(name=read, arguments={"path": "a.py"})],
            ),
            TraceEvent(type=EventType.TOOL, tool_name=read, content="code"),
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[ToolCall(name=edit, arguments={"path": "a.py", "old_string": "x", "new_string": "y"})],
            ),
            TraceEvent(type=EventType.TOOL, tool_name=edit, content="ok"),
            TraceEvent(
                type=EventType.ASSISTANT,
                tool_calls=[ToolCall(name=verify, arguments={"command": "pytest"})],
            ),
            TraceEvent(type=EventType.TOOL, tool_name=verify, content="passed"),
        ],
    )


def _clean_process_trace(
    *,
    task: str,
    status: OutcomeStatus,
    summary: str,
    files: list[str],
    edit_path: str = "src/lib/session.ts",
) -> AgentTrace:
    trace = _alias_trace("grep", "read", "search_replace", "shell")
    events = [TraceEvent(type=EventType.USER, content=task), *trace.events]
    for event in events:
        for call in event.tool_calls:
            if call.name == "search_replace":
                call.arguments["path"] = edit_path
    return trace.model_copy(
        update={
            "task": task,
            "files_touched": files,
            "events": events,
            "outcome": TraceOutcome(status=status, summary=summary),
        }
    )


def _check(report, name):
    return next(check for check in report.checks if check.name == name)


def test_anchor_passes_when_change_matches_task():
    report = grade_trace(frontier_auth_fix())
    anchor = _check(report, "outcome_anchored")
    assert anchor.passed
    assert anchor.band == "outcome"
    assert not report.hard_failed


def test_anchor_fails_when_change_drifts_from_task():
    trace = _clean_process_trace(
        task="Fix the billing invoice rounding error",
        status=OutcomeStatus.SUCCESS,
        summary="Reworded the changelog.",
        files=["docs/CHANGELOG.md"],
        edit_path="docs/CHANGELOG.md",
    )
    report = grade_trace(trace)
    anchor = _check(report, "outcome_anchored")
    assert not anchor.passed
    assert not anchor.hard
    assert "does not appear to address" in anchor.detail
    assert not report.hard_failed
    assert report.score > 0.0


def test_failure_with_high_policy_score_is_a_hard_contradiction():
    trace = _clean_process_trace(
        task="Login keeps redirecting back to /login",
        status=OutcomeStatus.FAILURE,
        summary="Patched the session cookie for the login redirect.",
        files=["src/lib/session.ts"],
    )
    report = grade_trace(trace)
    assert report.policy_score >= 0.8
    anchor = _check(report, "outcome_anchored")
    assert not anchor.passed and anchor.hard
    assert "contradiction" in anchor.detail
    assert report.hard_failed
    assert report.score == 0.0
    assert report.as_dict()["hard_failed"] is True
    assert "HARD FAIL" in report.summary()


def test_failure_with_low_policy_score_is_not_a_contradiction():
    report = grade_trace(lesser_auth_fail())
    assert not report.hard_failed
    assert _check(report, "outcome_anchored").passed


def test_anchor_skipped_without_anything_to_compare():
    trace = AgentTrace(id="empty", model="gpt-4o-mini", task="Fix the login redirect")
    assert "outcome_anchored" not in {check.name for check in grade_trace(trace).checks}


def test_failure_with_too_few_policy_checks_is_not_a_contradiction():
    trace = AgentTrace(
        id="thin",
        model="gpt-4o-mini",
        task="Fix the login redirect",
        outcome=TraceOutcome(status=OutcomeStatus.FAILURE, summary="gave up on login redirect"),
    )
    report = grade_trace(trace)
    assert not report.hard_failed
