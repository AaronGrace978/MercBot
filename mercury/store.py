"""SQLite-backed operational knowledge store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

from mercury.embed import BM25Index
from mercury.models import AgentTrace, CardKind, OperationalCard
from mercury.traceio import parse_trace

STALE_AFTER_DAYS = 30.0
STALE_CONFIDENCE_FACTOR = 0.5

SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    tier TEXT NOT NULL,
    task TEXT NOT NULL,
    outcome TEXT NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    situation TEXT NOT NULL,
    procedure TEXT NOT NULL,
    rationale TEXT NOT NULL,
    source_trace_id TEXT NOT NULL,
    source_model TEXT NOT NULL,
    confidence REAL NOT NULL,
    json TEXT NOT NULL,
    embedding TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_kind ON cards(kind);
CREATE INDEX IF NOT EXISTS idx_cards_confidence ON cards(confidence);
"""


class KnowledgeStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.path / "mercury.sqlite"
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._cards_cache: list[tuple[OperationalCard, list[float] | None]] | None = None
        self._bm25_cache: BM25Index | None = None
        self.stale_after_days: float | None = STALE_AFTER_DAYS

    def _invalidate_cache(self) -> None:
        self._cards_cache = None
        self._bm25_cache = None

    def close(self) -> None:
        self._invalidate_cache()
        self._conn.close()

    def put_trace(self, trace: AgentTrace) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO traces (id, model, tier, task, outcome, json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                model = excluded.model,
                tier = excluded.tier,
                task = excluded.task,
                outcome = excluded.outcome,
                json = excluded.json
            """,
            (
                trace.id,
                trace.model,
                trace.tier.value,
                trace.task,
                trace.outcome.status.value,
                trace.model_dump_json(),
                now,
            ),
        )
        self._conn.commit()

    def get_trace(self, trace_id: str) -> AgentTrace | None:
        row = self._conn.execute("SELECT json FROM traces WHERE id = ?", (trace_id,)).fetchone()
        if row is None:
            return None
        return parse_trace(json.loads(row["json"]))

    def traces(self) -> list[AgentTrace]:
        rows = self._conn.execute("SELECT json FROM traces ORDER BY created_at").fetchall()
        return [parse_trace(json.loads(row["json"])) for row in rows]

    def put_card(self, card: OperationalCard, embedding: list[float] | None = None) -> None:
        now = card.created_at
        self._conn.execute(
            """
            INSERT OR REPLACE INTO cards (
                id, kind, title, situation, procedure, rationale,
                source_trace_id, source_model, confidence, json, embedding, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card.id,
                card.kind.value,
                card.title,
                card.situation,
                card.procedure,
                card.rationale,
                card.source_trace_id,
                card.source_model,
                card.confidence,
                card.model_dump_json(),
                json.dumps(embedding) if embedding is not None else None,
                now,
            ),
        )
        self._conn.commit()
        self._invalidate_cache()

    def put_cards(self, cards: Iterable[OperationalCard], embeddings: dict[str, list[float]] | None = None) -> int:
        count = 0
        embeddings = embeddings or {}
        for card in cards:
            self.put_card(card, embeddings.get(card.id))
            count += 1
        return count

    def get_card(self, card_id: str) -> OperationalCard | None:
        row = self._conn.execute("SELECT json FROM cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            return None
        return OperationalCard.model_validate_json(row["json"])

    def record_outcome(self, card_ids: Iterable[str], *, succeeded: bool) -> int:
        """Reinforce or decay cards based on a student run outcome."""
        updated = 0
        for cid in set(card_ids):
            row = self._conn.execute(
                "SELECT json, embedding FROM cards WHERE id = ?", (cid,)
            ).fetchone()
            if row is None:
                continue
            card = OperationalCard.model_validate_json(row["json"])
            card.uses += 1
            card.last_used_at = datetime.now(timezone.utc).isoformat()
            if succeeded:
                card.successes += 1
            else:
                card.failures += 1
            embedding = json.loads(row["embedding"]) if row["embedding"] else None
            self.put_card(card, embedding)
            updated += 1
        return updated

    def mark_used(self, card_ids: Iterable[str], *, now: datetime | None = None) -> int:
        """Stamp cards as retrieved/used so they are not treated as stale."""
        stamp = (now or datetime.now(timezone.utc)).isoformat()
        return self._rewrite_cards(
            {cid: (lambda card: setattr(card, "last_used_at", stamp)) for cid in set(card_ids)}
        )

    def decay_stale(
        self,
        *,
        days: float | None = None,
        now: datetime | None = None,
    ) -> list[str]:
        """Halve the confidence of cards idle for `days` (default 30); returns decayed ids.

        Idle time runs from the latest of creation, last retrieval/use and the last decay,
        so a card loses half its confidence once per idle window, never on every call.
        Standing orders are recomputed from teacher traces and are exempt.
        """
        window = self.stale_after_days if days is None else days
        if not window or window <= 0:
            return []
        current = now or datetime.now(timezone.utc)
        cutoff = timedelta(days=window)
        stamp = current.isoformat()
        stale = [
            card.id
            for card, _ in self.cards_with_embeddings()
            if card.kind is not CardKind.STANDING_ORDER and current - card.last_active_at() >= cutoff
        ]

        def decay(card: OperationalCard) -> None:
            card.confidence = round(card.confidence * STALE_CONFIDENCE_FACTOR, 4)
            card.last_decayed_at = stamp

        self._rewrite_cards({cid: decay for cid in stale})
        return stale

    def _rewrite_cards(self, edits: dict[str, Callable[[OperationalCard], None]]) -> int:
        updated = 0
        for cid, edit in edits.items():
            row = self._conn.execute("SELECT json FROM cards WHERE id = ?", (cid,)).fetchone()
            if row is None:
                continue
            card = OperationalCard.model_validate_json(row["json"])
            edit(card)
            self._conn.execute(
                "UPDATE cards SET json = ?, confidence = ? WHERE id = ?",
                (card.model_dump_json(), card.confidence, cid),
            )
            updated += 1
        if updated:
            self._conn.commit()
            self._invalidate_cache()
        return updated

    def cards(self) -> list[OperationalCard]:
        return [card for card, _ in self.cards_with_embeddings()]

    def cards_with_embeddings(self) -> list[tuple[OperationalCard, list[float] | None]]:
        if self._cards_cache is not None:
            return list(self._cards_cache)
        rows = self._conn.execute("SELECT json, embedding FROM cards ORDER BY confidence DESC").fetchall()
        out: list[tuple[OperationalCard, list[float] | None]] = []
        for row in rows:
            card = OperationalCard.model_validate_json(row["json"])
            embedding = json.loads(row["embedding"]) if row["embedding"] else None
            out.append((card, embedding))
        self._cards_cache = out
        return list(out)

    def bm25_index(self) -> BM25Index:
        if self._bm25_cache is not None:
            return self._bm25_cache
        rows = self.cards_with_embeddings()
        texts = [card.searchable_text() for card, _ in rows]
        bm25 = BM25Index()
        bm25.fit(texts)
        self._bm25_cache = bm25
        return bm25

    def stats(self) -> dict[str, int | float]:
        trace_count = self._conn.execute("SELECT COUNT(*) AS n FROM traces").fetchone()["n"]
        card_count = self._conn.execute("SELECT COUNT(*) AS n FROM cards").fetchone()["n"]
        teachers = self._conn.execute(
            "SELECT COUNT(*) AS n FROM traces WHERE tier = 'frontier'"
        ).fetchone()["n"]
        by_kind = {
            row["kind"]: row["n"]
            for row in self._conn.execute(
                "SELECT kind, COUNT(*) AS n FROM cards GROUP BY kind"
            )
        }
        return {
            "traces": trace_count,
            "cards": card_count,
            "frontier_traces": teachers,
            "by_kind": by_kind,
        }
