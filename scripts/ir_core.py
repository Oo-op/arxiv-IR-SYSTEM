#!/usr/bin/env python3
"""Core retrieval logic for the information retrieval course project."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+)*")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass
class SearchResult:
    rank: int
    doc_id: int
    score: float
    title: str
    snippet: str
    url: str
    published: str
    matched_terms: list[str]


class IRSystem:
    """A small TF-IDF vector space retrieval system built on inverted index."""

    def __init__(
        self,
        cleaned_documents_path: str | Path,
        vocab_path: str | Path,
        inverted_index_path: str | Path,
    ) -> None:
        self.cleaned_documents_path = Path(cleaned_documents_path)
        self.vocab_path = Path(vocab_path)
        self.inverted_index_path = Path(inverted_index_path)

        self.documents_payload = json.loads(self.cleaned_documents_path.read_text(encoding="utf-8"))
        self.vocab_payload = json.loads(self.vocab_path.read_text(encoding="utf-8"))
        self.index_payload = json.loads(self.inverted_index_path.read_text(encoding="utf-8"))

        self.documents = self.documents_payload["documents"]
        self.doc_map = {doc["doc_id"]: doc for doc in self.documents}
        self.document_count = self.index_payload["document_count"]
        self.inverted_index = self.index_payload["index"]
        self.term_stats = {
            item["term"]: {
                "term_id": item["term_id"],
                "df": item["document_frequency"],
                "cf": item["collection_frequency"],
            }
            for item in self.vocab_payload["terms"]
        }
        self.idf_map = {term: self.compute_idf(stats["df"]) for term, stats in self.term_stats.items()}
        self.doc_norms = self._build_document_norms()

    @staticmethod
    def normalize_text(text: str) -> str:
        text = HTML_TAG_PATTERN.sub(" ", text or "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def tokenize(cls, text: str) -> list[str]:
        return TOKEN_PATTERN.findall(cls.normalize_text(text).lower())

    def compute_idf(self, document_frequency: int) -> float:
        if document_frequency <= 0:
            return 0.0
        return math.log(self.document_count / document_frequency) + 1.0

    def _build_document_norms(self) -> dict[int, float]:
        doc_squared_sum: dict[int, float] = {}
        for term, postings in self.inverted_index.items():
            idf = self.idf_map.get(term, 0.0)
            for posting in postings:
                weight = posting["tf"] * idf
                doc_id = posting["doc_id"]
                doc_squared_sum[doc_id] = doc_squared_sum.get(doc_id, 0.0) + weight * weight
        return {doc_id: math.sqrt(value) for doc_id, value in doc_squared_sum.items()}

    def build_query_vector(self, query: str) -> tuple[list[str], dict[str, float], float]:
        tokens = self.tokenize(query)
        query_tf: dict[str, int] = {}
        for token in tokens:
            if token in self.term_stats:
                query_tf[token] = query_tf.get(token, 0) + 1

        query_weights = {
            token: tf * self.idf_map[token]
            for token, tf in query_tf.items()
        }
        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
        return tokens, query_weights, query_norm

    def build_snippet(self, doc: dict, matched_terms: list[str], max_chars: int = 220) -> str:
        abstract = doc.get("clean_abstract") or doc.get("abstract", "")
        abstract = self.normalize_text(abstract)
        if not abstract:
            return ""

        sentences = SENTENCE_SPLIT_PATTERN.split(abstract)
        if not sentences:
            return abstract[:max_chars]

        best_sentence = ""
        best_score = -1
        lowered_terms = {term.lower() for term in matched_terms}
        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = sum(1 for term in lowered_terms if term in sentence_lower)
            if score > best_score:
                best_score = score
                best_sentence = sentence

        snippet = best_sentence if best_score > 0 else abstract[:max_chars]
        if len(snippet) > max_chars:
            snippet = snippet[: max_chars - 3].rstrip() + "..."
        return snippet

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        raw_tokens, query_weights, query_norm = self.build_query_vector(query)
        if not query_weights or query_norm == 0.0:
            return []

        numerator_scores: dict[int, float] = {}
        matched_terms_by_doc: dict[int, set[str]] = {}
        for term, query_weight in query_weights.items():
            postings = self.inverted_index.get(term, [])
            idf = self.idf_map[term]
            for posting in postings:
                doc_id = posting["doc_id"]
                doc_weight = posting["tf"] * idf
                numerator_scores[doc_id] = numerator_scores.get(doc_id, 0.0) + query_weight * doc_weight
                matched_terms_by_doc.setdefault(doc_id, set()).add(term)

        ranked_items: list[tuple[int, float]] = []
        for doc_id, numerator in numerator_scores.items():
            doc_norm = self.doc_norms.get(doc_id, 0.0)
            if doc_norm == 0.0:
                continue
            score = numerator / (query_norm * doc_norm)
            ranked_items.append((doc_id, score))

        ranked_items.sort(key=lambda item: item[1], reverse=True)

        results: list[SearchResult] = []
        for rank, (doc_id, score) in enumerate(ranked_items[:top_k], start=1):
            doc = self.doc_map[doc_id]
            matched_terms = sorted(matched_terms_by_doc.get(doc_id, set()))
            results.append(
                SearchResult(
                    rank=rank,
                    doc_id=doc_id,
                    score=score,
                    title=doc["title"],
                    snippet=self.build_snippet(doc, matched_terms),
                    url=doc["url"],
                    published=doc["published"],
                    matched_terms=matched_terms,
                )
            )
        return results

    def search_as_dicts(self, query: str, top_k: int = 10) -> list[dict]:
        return [
            {
                "rank": result.rank,
                "doc_id": result.doc_id,
                "score": round(result.score, 6),
                "title": result.title,
                "snippet": result.snippet,
                "url": result.url,
                "published": result.published,
                "matched_terms": result.matched_terms,
            }
            for result in self.search(query, top_k=top_k)
        ]


def default_paths(project_root: str | Path) -> tuple[Path, Path, Path]:
    root = Path(project_root)
    return (
        root / "data" / "processed" / "cleaned_documents.json",
        root / "data" / "index" / "vocab.json",
        root / "data" / "index" / "inverted_index.json",
    )
