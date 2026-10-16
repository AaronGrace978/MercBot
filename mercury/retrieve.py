"""Hybrid retrieval: hashing cosine + BM25 with reciprocal rank fusion."""

from __future__ import annotations

from dataclasses import dataclass

from mercury.embed import EmbedderProtocol, HashingEmbedder, cosine, tokenize
from mercury.models import CardKind, OperationalCard, TaskType
from mercury.store import KnowledgeStore

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "when",
    "then",
    "after",
    "before",
    "still",
}


@dataclass
class ScoredCard:
    card: OperationalCard
    score: float
    dense: float
    lexical: float


def retrieve(
    store: KnowledgeStore,
    query: str,
    *,
    embedder: EmbedderProtocol | None = None,
    task_type: TaskType | None = None,
    kinds: tuple[CardKind, ...] | None = None,
    error_signature: str | None = None,
    languages: list[str] | None = None,
    min_confidence: float = 0.3,
    limit: int = 8,
    dense_weight: float = 0.6,
) -> list[ScoredCard]:
    rows = store.cards_with_embeddings()
    if not rows:
        return []
    embedder = embedder or HashingEmbedder()
    q_text = _query_text(query, error_signature, languages)
    query_vec = embedder.embed(q_text)
    bm25 = store.bm25_index()
    lexical_scores = bm25.score(q_text)

    dense_list: list[float] = []
    for card, embedding in rows:
        vector = embedding if (embedding is not None and len(embedding) == len(query_vec)) else embedder.embed(card.searchable_text())
        dense_list.append(cosine(query_vec, vector))

    fused = _rrf(dense_list, lexical_scores, dense_weight=dense_weight)
    scored: list[ScoredCard] = []
    for index, ((card, _), score) in enumerate(zip(rows, fused)):
        eff_conf = card.effective_confidence
        if eff_conf < min_confidence:
            continue
        if kinds and card.kind not in kinds:
            continue
        if not _task_overlap(q_text, card) and card.kind is not CardKind.STANDING_ORDER:
            continue
        bonus = 0.0
        if task_type and card.task_type is task_type:
            bonus += 0.01
        if languages and any(lang in card.languages for lang in languages):
            bonus += 0.008
        if error_signature and card.error_signature:
            if error_signature[:40] in card.error_signature or card.error_signature[:40] in error_signature:
                bonus += 0.045
        scored.append(
            ScoredCard(
                card=card,
                score=(score * 10.0) + bonus + (eff_conf * 0.02) + (card.reinforcement_bonus * 0.15),
                dense=dense_list[index],
                lexical=lexical_scores[index],
            )
        )
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def _task_overlap(query: str, card: OperationalCard) -> bool:
    """Keep cards whose situation shares mass with the student task."""
    query_prefixes = _prefixes(query)
    if not query_prefixes:
        return True
    blob = " ".join(
        [
            card.situation,
            card.title,
            " ".join(card.languages),
            " ".join(card.tools),
            card.error_signature or "",
            card.task_type.value,
        ]
    )
    card_prefixes = _prefixes(blob)
    min_hits = 1 if len(query_prefixes) == 1 else 2
    return len(query_prefixes & card_prefixes) >= min_hits


def _prefixes(text: str) -> set[str]:
    out: set[str] = set()
    for token in tokenize(text):
        if token in _STOPWORDS:
            continue
        if len(token) >= 4:
            out.add(token[:5])
        elif len(token) >= 2 and (any(c.isdigit() for c in token) or "." in token or "/" in token or token in {"jwt", "sql", "sso", "tls", "dns", "api", "cli", "url", "dom", "css", "tsx", "jsx"}):
            out.add(token)
    return out


def _query_text(query: str, error_signature: str | None, languages: list[str] | None) -> str:
    parts = [query]
    if error_signature:
        parts.append(error_signature)
    if languages:
        parts.extend(languages)
    return " ".join(parts)


def _rrf(dense: list[float], lexical: list[float], *, dense_weight: float, k: int = 20) -> list[float]:
    dense_rank = _ranks(dense)
    lex_rank = _ranks(lexical)
    fused: list[float] = []
    lexical_weight = 1.0 - dense_weight
    for index in range(len(dense)):
        fused.append(
            dense_weight * (1.0 / (k + dense_rank[index]))
            + lexical_weight * (1.0 / (k + lex_rank[index]))
        )
    return fused


def _ranks(scores: list[float]) -> list[int]:
    """Competition ranks (1-based) where equal scores share the same rank."""
    order = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    ranks = [0] * len(scores)
    current_rank = 1
    for pos, index in enumerate(order, start=1):
        if pos > 1 and scores[index] < scores[order[pos - 2]]:
            current_rank = pos
        ranks[index] = current_rank
    return ranks
