"""Ingest traces from Mercury, OpenAI, Anthropic, and Cursor-like payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mercury.fingerprint import enrich_trace, looks_like_error
from mercury.models import (
    AgentTrace,
    EventType,
    OutcomeStatus,
    ToolCall,
    TraceEvent,
    TraceOutcome,
    trace_id_for,
)


def load_trace(source: str | Path | dict[str, Any]) -> AgentTrace:
    if isinstance(source, dict):
        payload = source
    else:
        path = Path(source)
        raw_text = path.read_text(encoding="utf-8").strip()
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            # Support JSONL trace logs (one event/message JSON object per line)
            lines = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
            if lines and isinstance(lines[0], dict) and "role" in lines[0]:
                payload = {"messages": lines}
            else:
                payload = {"task": "", "events": lines}
    return parse_trace(payload)


def parse_trace(payload: dict[str, Any]) -> AgentTrace:
    if "events" in payload and "task" in payload:
        return enrich_trace(_parse_canonical(payload))
    if "messages" in payload:
        return enrich_trace(_parse_messages(payload))
    raise ValueError("Unrecognized trace format: expected Mercury canonical or chat messages")


def _parse_canonical(payload: dict[str, Any]) -> AgentTrace:
    events = [_parse_event(raw) for raw in payload.get("events", [])]
    outcome_raw = payload.get("outcome") or {}
    if isinstance(outcome_raw, str):
        outcome = TraceOutcome(status=_outcome_status(outcome_raw))
    else:
        outcome = TraceOutcome(
            status=_outcome_status(outcome_raw.get("status", "unknown")),
            summary=str(outcome_raw.get("summary", "")),
        )
    model = str(payload.get("model") or "unknown")
    task = str(payload.get("task") or _task_from_events(events))
    trace_id = str(payload.get("id") or trace_id_for(model, task))
    return AgentTrace(
        id=trace_id,
        model=model,
        task=task,
        events=events,
        outcome=outcome,
        started_at=payload.get("started_at"),
        files_touched=list(payload.get("files_touched") or []),
        languages=list(payload.get("languages") or []),
        metadata=dict(payload.get("metadata") or {}),
    )


def _parse_messages(payload: dict[str, Any]) -> AgentTrace:
    messages = payload["messages"]
    events: list[TraceEvent] = []
    call_id_to_name: dict[str, str] = {}
    for message in messages:
        role = str(message.get("role") or "assistant").lower()
        raw_content = message.get("content")
        if role == "tool":
            content = _content_to_text(raw_content)
            call_id = message.get("tool_call_id")
            t_name = message.get("name") or message.get("tool_name") or (call_id_to_name.get(str(call_id)) if call_id else None)
            events.append(
                TraceEvent(
                    type=EventType.TOOL,
                    content=content,
                    tool_name=t_name,
                    tool_call_id=call_id,
                    is_error=bool(message.get("is_error")) or looks_like_error(content),
                )
            )
            continue

        # Handle Anthropic-style tool_result blocks inside user messages
        if role == "user" and isinstance(raw_content, list) and any(
            isinstance(part, dict) and part.get("type") == "tool_result" for part in raw_content
        ):
            text_parts: list[str] = []
            for part in raw_content:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    res_text = _content_to_text(part.get("content"))
                    t_use_id = part.get("tool_use_id")
                    t_name = part.get("name") or part.get("tool_name") or (call_id_to_name.get(str(t_use_id)) if t_use_id else None)
                    events.append(
                        TraceEvent(
                            type=EventType.TOOL,
                            content=res_text,
                            tool_name=t_name,
                            tool_call_id=t_use_id,
                            is_error=bool(part.get("is_error")) or looks_like_error(res_text),
                        )
                    )
                elif isinstance(part, dict) and "text" in part:
                    text_parts.append(str(part["text"]))
                elif isinstance(part, str):
                    text_parts.append(part)
            if text_parts:
                events.append(TraceEvent(type=EventType.USER, content="\n".join(text_parts)))
            continue

        event_type = {
            "user": EventType.USER,
            "system": EventType.SYSTEM,
            "assistant": EventType.ASSISTANT,
        }.get(role, EventType.ASSISTANT)
        tool_calls = [_parse_tool_call(raw) for raw in message.get("tool_calls") or []]
        # Extract Anthropic-style tool_use blocks from assistant content list
        if isinstance(raw_content, list):
            for part in raw_content:
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    tc = _parse_tool_call(
                        {
                            "id": part.get("id"),
                            "name": part.get("name"),
                            "arguments": part.get("input") or part.get("arguments") or {},
                        }
                    )
                    tool_calls.append(tc)
        for tc in tool_calls:
            if tc.call_id:
                call_id_to_name[tc.call_id] = tc.name
        content = _content_to_text(raw_content)
        events.append(
            TraceEvent(
                type=event_type,
                content=content,
                tool_calls=tool_calls,
            )
        )
    model = str(payload.get("model") or "unknown")
    task = str(payload.get("task") or _task_from_events(events))
    outcome = payload.get("outcome") or {}
    if isinstance(outcome, str):
        parsed_outcome = TraceOutcome(status=_outcome_status(outcome))
    else:
        parsed_outcome = TraceOutcome(
            status=_outcome_status((outcome or {}).get("status", "unknown")),
            summary=str((outcome or {}).get("summary", "")),
        )
    return AgentTrace(
        id=str(payload.get("id") or trace_id_for(model, task)),
        model=model,
        task=task,
        events=events,
        outcome=parsed_outcome,
        files_touched=list(payload.get("files_touched") or []),
        languages=list(payload.get("languages") or []),
        metadata=dict(payload.get("metadata") or {}),
    )


def _parse_event(raw: dict[str, Any]) -> TraceEvent:
    event_type = EventType(str(raw.get("type") or "assistant"))
    content = _content_to_text(raw.get("content"))
    tool_calls = [_parse_tool_call(item) for item in raw.get("tool_calls") or []]
    is_error = bool(raw.get("is_error"))
    if event_type is EventType.TOOL:
        is_error = is_error or looks_like_error(content)
    return TraceEvent(
        type=event_type,
        content=content,
        tool_calls=tool_calls,
        tool_name=raw.get("tool_name") or raw.get("name"),
        tool_call_id=raw.get("tool_call_id"),
        is_error=is_error,
        timestamp=raw.get("timestamp"),
    )


def _parse_tool_call(raw: Any) -> ToolCall:
    if not isinstance(raw, dict):
        return ToolCall(name=str(raw))
    fn = raw.get("function") if isinstance(raw.get("function"), dict) else {}
    name = raw.get("name") or fn.get("name") or "unknown"
    arguments = raw.get("arguments") or fn.get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {"raw": arguments}
    if not isinstance(arguments, dict):
        arguments = {"value": arguments}
    return ToolCall(name=str(name), arguments=arguments, call_id=raw.get("id") or raw.get("call_id"))


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, str):
                chunks.append(part)
            elif isinstance(part, dict):
                if "text" in part:
                    chunks.append(str(part["text"]))
                elif part.get("type") == "tool_use":
                    chunks.append(str(part.get("name") or ""))
        return "\n".join(chunk for chunk in chunks if chunk)
    return str(content)


def _task_from_events(events: list[TraceEvent]) -> str:
    for event in events:
        if event.type is EventType.USER and event.content.strip():
            return event.content.strip().splitlines()[0][:400]
    return "untitled task"


def _outcome_status(raw: str | None) -> OutcomeStatus:
    try:
        return OutcomeStatus(str(raw or "unknown").lower())
    except ValueError:
        return OutcomeStatus.UNKNOWN
