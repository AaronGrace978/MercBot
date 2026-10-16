"""Contrastive distillation: lesser failure vs frontier success on a similar task."""

from __future__ import annotations

from mercury.models import AgentTrace, CardKind, OperationalCard, card_id
from mercury.phases import first_tool, normalize_tool, segment_phases


def contrast_traces(student: AgentTrace, teacher: AgentTrace) -> list[OperationalCard]:
    """Where a lesser model diverged, emit 'don't do X, do Y' cards.

    Contrast is the strongest decision-function signal we have: the student
    documents what was chosen *against*, the teacher documents the replacement.
    """
    cards: list[OperationalCard] = []
    student_first = first_tool(student)
    teacher_first = first_tool(teacher)
    if (
        student_first
        and teacher_first
        and normalize_tool(student_first) != normalize_tool(teacher_first)
    ):
        cards.append(
            OperationalCard(
                id=card_id("contrast-first", student.id, teacher.id, teacher_first),
                kind=CardKind.CONTRAST,
                title="Open like the frontier model, not the lesser one",
                situation=teacher.task,
                procedure=(
                    f"Lesser models often start with `{student_first}`. "
                    f"The frontier model started with `{teacher_first}` and succeeded. "
                    f"Start with `{teacher_first}`."
                ),
                rationale="Contrastive first-action divergence on a matched task.",
                tools=[teacher_first],
                chose=f"start with `{teacher_first}`",
                rejected=[f"start with `{student_first}`"],
                task_type=teacher.task_type,
                source_trace_id=teacher.id,
                source_model=teacher.model,
                confidence=0.88 if teacher.outcome.succeeded and student.outcome.failed else 0.62,
                languages=list(teacher.languages),
                metadata={"student_trace_id": student.id, "student_model": student.model},
            )
        )

    student_phases = [phase.name for phase in segment_phases(student)]
    teacher_phases = [phase.name for phase in segment_phases(teacher)]
    if teacher_phases and student_phases != teacher_phases:
        skipped, extra_phases = _align_phases(student_phases, teacher_phases)
        detail_bits: list[str] = []
        if skipped:
            detail_bits.append(f"The lesser model skipped frontier phase(s): {', '.join(skipped)}")
        if extra_phases:
            detail_bits.append(f"inserted premature/extra phase(s): {', '.join(extra_phases)}")
        alignment_note = (". ".join(detail_bits) + ". ") if detail_bits else ""
        cards.append(
            OperationalCard(
                id=card_id("contrast-phase", student.id, teacher.id, "|".join(teacher_phases)),
                kind=CardKind.CONTRAST,
                title="Follow the frontier phase order",
                situation=teacher.task,
                procedure=(
                    f"{alignment_note}Avoid this lesser-model phase order: {' → '.join(student_phases) or '(none)'}. "
                    f"Use this frontier order: {' → '.join(teacher_phases)}."
                ),
                rationale="Phase-level LCS alignment between a failed student run and a successful teacher run.",
                tools=teacher.tool_sequence()[:8],
                chose=" → ".join(teacher_phases),
                rejected=[" → ".join(student_phases) or "(no phases)"],
                task_type=teacher.task_type,
                source_trace_id=teacher.id,
                source_model=teacher.model,
                confidence=0.84 if teacher.outcome.succeeded else 0.5,
                languages=list(teacher.languages),
                metadata={
                    "student_trace_id": student.id,
                    "student_phases": student_phases,
                    "skipped_phases": skipped,
                    "extra_phases": extra_phases,
                },
            )
        )

    recovery_card = _contrast_recovery(student, teacher)
    if recovery_card is not None:
        cards.append(recovery_card)

    student_files = set(student.files_touched)
    teacher_files = set(teacher.files_touched)
    extra = sorted(student_files - teacher_files)
    missing = sorted(teacher_files - student_files)
    if extra or missing:
        bits: list[str] = []
        if extra:
            bits.append("Do not start in " + ", ".join(_base(path) for path in extra[:4]))
        if missing:
            bits.append("The frontier model actually touched " + ", ".join(_base(path) for path in missing[:4]))
        cards.append(
            OperationalCard(
                id=card_id("contrast-files", student.id, teacher.id, ",".join(missing[:6])),
                kind=CardKind.CONTRAST,
                title="Touch the same files the frontier model touched",
                situation=teacher.task,
                procedure=". ".join(bits) + ".",
                rationale="File-set mismatch on a contrastive pair.",
                tools=["read", "grep"],
                chose=", ".join(_base(path) for path in missing[:4]) if missing else "frontier file set",
                rejected=[_base(path) for path in extra[:4]],
                task_type=teacher.task_type,
                source_trace_id=teacher.id,
                source_model=teacher.model,
                confidence=0.7,
                languages=list(teacher.languages),
                metadata={"student_trace_id": student.id},
            )
        )
    return cards


def _base(path: str) -> str:
    return f"`{path.split('/')[-1]}`"


def _align_phases(student_phases: list[str], teacher_phases: list[str]) -> tuple[list[str], list[str]]:
    """Compute LCS phase alignment to identify skipped teacher phases and premature student phases."""
    m, n = len(student_phases), len(teacher_phases)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if student_phases[i] == teacher_phases[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    i = j = 0
    matched_s: set[int] = set()
    matched_t: set[int] = set()
    while i < m and j < n:
        if student_phases[i] == teacher_phases[j]:
            matched_s.add(i)
            matched_t.add(j)
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    skipped: list[str] = []
    for idx, name in enumerate(teacher_phases):
        if idx not in matched_t and name not in skipped:
            skipped.append(name)
    extra: list[str] = []
    for idx, name in enumerate(student_phases):
        if idx not in matched_s and name not in extra:
            extra.append(name)
    return skipped, extra


def _contrast_recovery(student: AgentTrace, teacher: AgentTrace) -> OperationalCard | None:
    """Contrast how the student and teacher reacted immediately after their first tool error."""
    from mercury.models import EventType

    s_next = _first_post_error_tools(student)
    t_next = _first_post_error_tools(teacher)
    if not s_next or not t_next:
        return None
    if [normalize_tool(x) for x in s_next] == [normalize_tool(x) for x in t_next]:
        return None
    return OperationalCard(
        id=card_id("contrast-recovery", student.id, teacher.id, ",".join(t_next)),
        kind=CardKind.CONTRAST,
        title="Recover from errors like the frontier model",
        situation=teacher.task,
        procedure=(
            f"After a tool error, the lesser model pivoted to `{', '.join(s_next[:3])}` "
            f"while the frontier model pivoted to `{', '.join(t_next[:3])}`. "
            f"Follow the frontier recovery pivot (`{', '.join(t_next[:3])}`)."
        ),
        rationale="Post-error recovery divergence between student failure and teacher success.",
        tools=t_next[:4],
        chose=", ".join(t_next[:3]),
        rejected=[", ".join(s_next[:3])],
        task_type=teacher.task_type,
        source_trace_id=teacher.id,
        source_model=teacher.model,
        confidence=0.82 if teacher.outcome.succeeded else 0.55,
        languages=list(teacher.languages),
        metadata={"student_trace_id": student.id},
    )


def _first_post_error_tools(trace: AgentTrace) -> list[str]:
    from mercury.models import EventType

    events = trace.events
    for idx, event in enumerate(events):
        if event.type is EventType.TOOL and event.is_error:
            for later in events[idx + 1 : idx + 5]:
                if later.type is EventType.ASSISTANT and later.tool_calls:
                    return [call.name for call in later.tool_calls]
    return []
