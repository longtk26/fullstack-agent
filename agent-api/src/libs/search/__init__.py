"""Small text ranking helpers (BM25 and a light suffix stripper), shared by the design direction (Story 12.6) and the
icon resolver (Story 20.5)."""

import math
from collections import Counter

# A light suffix stripper (not a full stemmer): photographer / photography, branding / brand, studios / studio.
SUFFIXES = ("ings", "ing", "ers", "er", "ies", "s", "y")


def stem(word: str) -> str:
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


class Bm25:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.documents = [Counter(doc) for doc in documents]
        self.lengths = [len(doc) for doc in documents]
        self.average = sum(self.lengths) / max(len(documents), 1)
        frequency = Counter(term for doc in self.documents for term in doc)
        count = len(documents)
        self.idf = {term: math.log(1 + (count - n + 0.5) / (n + 0.5)) for term, n in frequency.items()}
        self.k1, self.b = k1, b

    def scores(self, query: list[str], weights: dict[str, float] | None = None) -> list[float]:
        """One score per document; `weights` multiplies a query term's part (default 1)."""
        terms = set(query)
        weights = weights or {}
        out = []
        for doc, length in zip(self.documents, self.lengths, strict=True):
            score = 0.0
            for term in terms & doc.keys():
                tf = doc[term]
                score += (
                    weights.get(term, 1.0)
                    * self.idf[term]
                    * tf
                    * (self.k1 + 1)
                    / (tf + self.k1 * (1 - self.b + self.b * length / self.average))
                )
            out.append(score)
        return out
