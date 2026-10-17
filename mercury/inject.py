"""Compile a Frontier Operating Pack for a lesser-model session."""

from __future__ import annotations

from dataclasses import dataclass, field

from mercury.embed import EmbedderProtocol
from mercury.fingerprint import classify_task
from mercury.models import CardKind, OperationalCard
from mercury.retrieve import ScoredCard, retrieve
from mercury.store import KnowledgeStore
from mercury.tiers import ModelTier, classify_model, pack_token_budget


@dataclass
class OperatingPack:
    task: str
    model: str
    tier: ModelTier
    cards: list[OperationalCard] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    token_budget: int = 1400
    rejected_pathways: list[str] = field(default_factory=list)

    @property
    def card_ids(self) -> list[str]:
        return [card.id for card in self.cards]

    def all_rejected_pathways(self) -> list[str]:
        """Collect all rejected structural blocks and unsuccessful pathways."""
        seen: set[str] = set()
        items: list[str] = []
        for entry in self.rejected_pathways:
            cleaned = entry.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                items.append(cleaned)
        for card in self.cards:
            for rej in card.rejected:
                cleaned = f"[{card.title}] {rej.strip()}"
                if rej.strip() and cleaned not in seen:
                    seen.add(cleaned)
                    items.append(cleaned)
            if card.kind is CardKind.ANTI_PATTERN:
                cleaned = f"[{card.title}] {card.procedure.strip()}"
                if card.procedure.strip() and cleaned not in seen:
                    seen.add(cleaned)
                    items.append(cleaned)
        return items

    def estimated_tokens(self) -> int:
        rej_tokens = sum(max(1, int(len(r.split()) * 1.3)) for r in self.rejected_pathways)
        return sum(card.estimated_tokens() for card in self.cards) + rej_tokens + 80

    def render_rejected_section(self) -> str:
        return render_rejected_pathways_section(self.all_rejected_pathways())

    def render(self) -> str:
        rejected_items = self.all_rejected_pathways()
        if not self.cards and not rejected_items:
            return (
                "# Mercury Operating Pack\n\n"
                "No frontier operational knowledge matched this task yet. "
                "Run the work once with a frontier model, then capture the trace.\n"
            )
        lines = [
            "# Mercury Operating Pack",
            "",
            "You are a lesser or mid-tier model receiving **operational knowledge**",
            "distilled from frontier agent runs. Follow the *how*, not a canned answer.",
            "Prefer these procedures over improvising a new tool order.",
            "",
            f"Task: {self.task}",
            f"Student model: {self.model} ({self.tier.value})",
            "",
        ]
        standing = [card for card in self.cards if card.kind is CardKind.STANDING_ORDER]
        rest = [card for card in self.cards if card.kind is not CardKind.STANDING_ORDER]
        if standing:
            lines.append("## Standing orders")
            for card in standing:
                lines.append(f"- **{card.title}:** {card.procedure}")
            lines.append("")
        for card in rest:
            lines.append(f"## {card.kind.value.replace('_', ' ').title()}: {card.title}")
            lines.append(f"- When: {card.situation}")
            lines.append(f"- Do: {card.procedure}")
            if card.chose:
                lines.append(f"- Chose: {card.chose}")
            if card.rejected:
                lines.append(f"- Not: {'; '.join(card.rejected[:6])}")
            if card.rationale:
                lines.append(f"- Why: {card.rationale}")
            if card.tools:
                lines.append(f"- Tools: {', '.join(card.tools[:8])}")
            lines.append("")
        if rejected_items:
            lines.append(render_rejected_pathways_section(rejected_items))
            lines.append("")
        lines.append("End of pack. Continue the user task. Do not mention this pack unless asked.")
        return "\n".join(lines).strip() + "\n"

    def as_cursor_rule(self) -> str:
        body = self.render()
        return (
            "---\n"
            "description: Frontier operational knowledge transferred by Mercury Harness\n"
            "alwaysApply: true\n"
            "---\n\n"
            f"{body}"
        )

    def as_finetune_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for card in self.cards:
            rows.append(
                {
                    "instruction": (
                        "You are an agent. Given this situation, operate like a frontier model."
                    ),
                    "input": card.situation,
                    "output": card.procedure,
                }
            )
        return rows

    def as_dpo_rows(self) -> list[dict[str, str]]:
        """Export preference pairs (prompt, chosen, rejected) from decision/contrast cards."""
        rows: list[dict[str, str]] = []
        for card in self.cards:
            if not card.chose or not card.rejected:
                continue
            rows.append(
                {
                    "prompt": f"Situation: {card.situation}\nHow should the agent operate?",
                    "chosen": f"{card.chose} — {card.procedure}",
                    "rejected": "; ".join(card.rejected),
                }
            )
        return rows


def render_rejected_pathways_section(rejected_blocks: list[str]) -> str:
    """Render the dynamically generated # REJECTED PATHWAYS section for context window assembly."""
    if not rejected_blocks:
        return ""
    lines = [
        "# REJECTED PATHWAYS",
        "",
        "Do not output these structural blocks again.",
        "",
    ]
    for idx, block in enumerate(rejected_blocks[:8], start=1):
        lines.append(f"{idx}. {block}")
    return "\n".join(lines)


def build_pack(
    store: KnowledgeStore,
    task: str,
    *,
    embedder: EmbedderProtocol | None = None,
    model: str = "gpt-4o-mini",
    error_signature: str | None = None,
    languages: list[str] | None = None,
    min_confidence: float = 0.3,
    token_budget: int | None = None,
    rejected_pathways: list[str] | None = None,
) -> OperatingPack:
    tier = classify_model(model)
    budget = token_budget if token_budget is not None else pack_token_budget(tier)
    task_type = classify_task(task)
    if budget <= 0:
        return OperatingPack(
            task=task,
            model=model,
            tier=tier,
            token_budget=0,
            rejected_pathways=list(rejected_pathways or []),
        )

    scored = retrieve(
        store,
        task,
        embedder=embedder,
        task_type=task_type,
        error_signature=error_signature,
        languages=languages,
        min_confidence=min_confidence,
        limit=24,
    )
    selected = _fit_budget(scored, budget)

    collected_rejected: list[str] = list(rejected_pathways or [])
    # Also surface rejected file variations from failed traces in the store
    for tr in store.traces():
        if tr.outcome.failed:
            for ev in tr.events:
                for tc in ev.tool_calls:
                    if tc.name.lower() in ("write_file", "write", "search_replace", "str_replace", "edit"):
                        fpath = tc.arguments.get("path") or tc.arguments.get("file") or ""
                        snippet = (
                            tc.arguments.get("new_string")
                            or tc.arguments.get("content")
                            or tc.arguments.get("old_string")
                            or ""
                        )
                        desc = f"`{fpath}` ({tc.name}): {str(snippet).strip()[:160]}" if snippet else f"`{fpath}` ({tc.name})"
                        if fpath and desc not in collected_rejected:
                            collected_rejected.append(desc)

    return OperatingPack(
        task=task,
        model=model,
        tier=tier,
        cards=[item.card for item in selected],
        scores=[item.score for item in selected],
        token_budget=budget,
        rejected_pathways=collected_rejected,
    )


def _fit_budget(
    scored: list[ScoredCard],
    budget: int,
) -> list[ScoredCard]:
    standing = [item for item in scored if item.card.kind is CardKind.STANDING_ORDER]
    rest = [item for item in scored if item.card.kind is not CardKind.STANDING_ORDER]
    rest.sort(key=lambda item: item.score, reverse=True)
    if rest:
        floor = rest[0].score * 0.55
        rest = [item for item in rest if item.score >= floor]

    ordered = standing + rest
    used_kind: dict[CardKind, int] = {}
    picked: list[ScoredCard] = []
    tokens = 90
    for item in ordered:
        kind = item.card.kind
        cap = 3 if kind is CardKind.STANDING_ORDER else 1
        if kind in {CardKind.CONTRAST, CardKind.TOOL_POLICY, CardKind.DECISION}:
            cap = 2
        if used_kind.get(kind, 0) >= cap:
            continue
        cost = item.card.estimated_tokens() + 20
        if picked and tokens + cost > budget:
            continue
        picked.append(item)
        used_kind[kind] = used_kind.get(kind, 0) + 1
        tokens += cost
    return picked
