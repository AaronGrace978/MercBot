"""Stable local embeddings, pluggable Embedder protocol, and inverted-index BM25."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

TOKEN_RE = re.compile(r"[a-z0-9_./+-]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


@runtime_checkable
class EmbedderProtocol(Protocol):
    """Pluggable embedder interface (local hashing, ONNX, sentence-transformers, etc.)."""

    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    """Hybrid word-unigram + word-bigram + char n-gram hashing vector.

    Deterministic across processes, zero network/model downloads.
    """

    def __init__(
        self,
        dim: int = 256,
        ngram_range: tuple[int, int] = (3, 5),
        word_weight: float = 2.0,
        bigram_weight: float = 1.5,
    ) -> None:
        self.dim = dim
        self.ngram_range = ngram_range
        self.word_weight = word_weight
        self.bigram_weight = bigram_weight

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        lowered = (text or "").lower()

        # 1. Word unigrams & bigrams for strong semantic/token separation
        tokens = tokenize(lowered)
        for token in tokens:
            self._accumulate(vector, f"w:{token}", self.word_weight)
        for idx in range(len(tokens) - 1):
            self._accumulate(vector, f"b:{tokens[idx]}_{tokens[idx + 1]}", self.bigram_weight)

        # 2. Character n-grams for morphological / path / identifier resilience
        blob = f" {lowered} "
        low, high = self.ngram_range
        for n in range(low, high + 1):
            if len(blob) < n:
                continue
            for index in range(len(blob) - n + 1):
                gram = blob[index : index + n]
                self._accumulate(vector, gram, 1.0)
        return _l2_normalize(vector)

    def _accumulate(self, vector: list[float], feature: str, weight: float) -> None:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        slot = int.from_bytes(digest, "little") % self.dim
        sign = weight if digest[-1] % 2 == 0 else -weight
        vector[slot] += sign


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


@dataclass
class BM25Index:
    k1: float = 1.5
    b: float = 0.75
    documents: list[list[str]] = field(default_factory=list)
    doc_lens: list[int] = field(default_factory=list)
    doc_freq: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    postings: dict[str, list[tuple[int, int]]] = field(default_factory=lambda: defaultdict(list))
    avg_len: float = 0.0

    def fit(self, texts: list[str]) -> None:
        self.documents = [tokenize(text) for text in texts]
        self.doc_lens = [len(tokens) for tokens in self.documents]
        self.doc_freq = defaultdict(int)
        self.postings = defaultdict(list)
        total = sum(self.doc_lens)
        for doc_idx, tokens in enumerate(self.documents):
            counts = Counter(tokens)
            for token, tf in counts.items():
                self.doc_freq[token] += 1
                self.postings[token].append((doc_idx, tf))
        self.avg_len = (total / len(self.documents)) if self.documents else 0.0

    def score(self, query: str) -> list[float]:
        q_tokens = tokenize(query)
        if not self.documents:
            return []
        n_docs = len(self.documents)
        scores = [0.0] * n_docs
        query_counts = Counter(q_tokens)
        avg_len = self.avg_len or 1.0
        for token, qtf in query_counts.items():
            df = self.doc_freq.get(token, 0)
            if df == 0:
                continue
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            for doc_idx, tf in self.postings.get(token, ()):
                doc_len = self.doc_lens[doc_idx]
                denom = tf + self.k1 * (1 - self.b + self.b * (doc_len / avg_len))
                scores[doc_idx] += idf * qtf * ((tf * (self.k1 + 1)) / denom)
        return scores
