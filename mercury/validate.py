"""Card validation gate: ask a teacher model whether a card matches its trace.

Distillation is deterministic and will happily write a confident card about a
procedure the trace never performed. One cheap yes/no call per new card keeps
those out of the store. The gate is a protocol so tests and offline setups can
plug in any callable; ``mercury_runtime.teacher.TeacherCardValidator`` is the real-model
implementation, kept in the runtime package because it needs the provider adapters.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Protocol, runtime_checkable

from mercury.models import AgentTrace, EventType, OperationalCard

VALIDATION_PROMPT = (
    "Answer with exactly one word, YES or NO: does this procedure actually match "
    "what happened in the trace?"
)

_MAX_TRACE_CHARS = 6000
_MAX_ARG_CHARS = 120
_MAX_OUTPUT_CHARS = 100


class Verdict(str, Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True)
class CardValidation:
    card_id: str
    title: str
    verdict: Verdict
    reason: str = ""


@runtime_checkable
class CardValidatorProtocol(Protocol):
    def validate(
        self,
        card: OperationalCard,
        trace: AgentTrace | None,
        counterpart: AgentTrace | None = None,
    ) -> CardValidation: ...


def render_trace_for_validation(trace: AgentTrace, *, limit: int = _MAX_TRACE_CHARS) -> str:
    """Compact, deterministic rendering: task, ordered tool calls, errors, outcome."""
    lines = [f"Task: {trace.task}", f"Model: {trace.model}"]
    for event in trace.events:
        if event.type is EventType.ASSISTANT and event.tool_calls:
            for call in event.tool_calls:
                args = json.dumps(call.arguments, sort_keys=True, default=str)
                lines.append(f"- call {call.name} {_clip(args, _MAX_ARG_CHARS)}")
        elif event.type is EventType.TOOL:
            status = "ERROR" if event.is_error else "ok"
            lines.append(f"  -> {event.tool_name or 'tool'} {status}: {_clip(event.content, _MAX_OUTPUT_CHARS)}")
    lines.append(f"Outcome: {trace.outcome.status.value} - {_clip(trace.outcome.summary, 200)}")
    text = "\n".join(lines)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def build_validation_prompt(
    card: OperationalCard,
    trace: AgentTrace,
    counterpart: AgentTrace | None = None,
) -> str:
    parts = [VALIDATION_PROMPT, "", "TRACE:", render_trace_for_validation(trace)]
    if counterpart is not None:
        parts += ["", "COMPARISON TRACE (the run this card was contrasted against):", render_trace_for_validation(counterpart)]
    parts += [
        "",
        "PROCEDURE:",
        f"Situation: {card.situation}",
        f"Procedure: {card.procedure}",
    ]
    if card.chose:
        parts.append(f"Chose: {card.chose}")
    if card.rejected:
        parts.append(f"Rejected: {'; '.join(card.rejected)}")
    return "\n".join(parts)


def parse_verdict(reply: str) -> Verdict:
    """YES confirms, NO rejects; anything else is unconfirmed rather than guessed."""
    words = (reply or "").strip().upper().replace("*", "").split()
    first = words[0].strip(".,:;!\"'") if words else ""
    if first == "YES":
        return Verdict.CONFIRMED
    if first == "NO":
        return Verdict.REJECTED
    return Verdict.UNCONFIRMED


class CompletionCardValidator:
    """Validate through any ``prompt -> reply`` callable. Never raises: a failed call is ``unconfirmed``."""

    def __init__(self, complete: Callable[[str], str]) -> None:
        self._complete = complete

    def validate(
        self,
        card: OperationalCard,
        trace: AgentTrace | None,
        counterpart: AgentTrace | None = None,
    ) -> CardValidation:
        if trace is None:
            return CardValidation(card.id, card.title, Verdict.UNCONFIRMED, "source trace not in store")
        prompt = build_validation_prompt(card, trace, counterpart)
        try:
            reply = self._complete(prompt)
        except Exception as exc:
            return CardValidation(card.id, card.title, Verdict.UNCONFIRMED, f"teacher call failed: {exc}")
        return CardValidation(card.id, card.title, parse_verdict(reply), _clip(reply, 160))


def _clip(text: Any, limit: int) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."
