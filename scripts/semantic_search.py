#!/usr/bin/env python3
"""Semantic search module using Sentence-BERT for semantic similarity matching."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer, util


@dataclass
class SemanticSearchResult:
    rank: int
    doc_id: int
    score: float
    title: str
    snippet: str
    url: str
    published: str


class SemanticIRSystem:
    """A semantic retrieval system using Sentence-BERT embeddings."""

    def __init__(
        self,
        cleaned_documents_path: str | Path,
        model_name: str = "all-MiniLM-L6-v2",
        embedding_cache_path: str | Path | None = None,
    ) -> None:
        self.cleaned_documents_path = Path(cleaned_documents_path)
        self.model_name = model_name
        self.embedding_cache_path = Path(embedding_cache_path) if embedding_cache_path else None

        self.documents_payload = json.loads(self.cleaned_documents_path.read_text(encoding="utf-8"))
        self.documents = self.documents_payload["documents"]
        self.doc_map = {doc["doc_id"]: doc for doc in self.documents}
        self.document_count = len(self.documents)

        self.model = SentenceTransformer(model_name)
        self.doc_embeddings = self._load_or_compute_embeddings()

    def _get_document_text(self, doc: dict) -> str:
        title = doc.get("clean_title", "")
        abstract = doc.get("clean_abstract", "")
        return f"{title} {abstract}".strip()

    def _compute_embeddings(self) -> np.ndarray:
        texts = [self._get_document_text(doc) for doc in self.documents]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings

    def _load_or_compute_embeddings(self) -> np.ndarray:
        if self.embedding_cache_path and self.embedding_cache_path.exists():
            print(f"Loading cached embeddings from {self.embedding_cache_path}")
            return np.load(str(self.embedding_cache_path))
        
        embeddings = self._compute_embeddings()
        
        if self.embedding_cache_path:
            self.embedding_cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(str(self.embedding_cache_path), embeddings)
            print(f"Saved embeddings to {self.embedding_cache_path}")
        
        return embeddings

    def search(self, query: str, top_k: int = 10) -> list[SemanticSearchResult]:
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        cos_scores = util.cos_sim(query_embedding, self.doc_embeddings)[0]
        
        top_results = np.argsort(-cos_scores)[:top_k]
        
        results: list[SemanticSearchResult] = []
        for rank, idx in enumerate(top_results, start=1):
            doc = self.documents[idx]
            results.append(
                SemanticSearchResult(
                    rank=rank,
                    doc_id=doc["doc_id"],
                    score=float(cos_scores[idx]),
                    title=doc["title"],
                    snippet=doc.get("clean_abstract", "")[:220] + "..." if len(doc.get("clean_abstract", "")) > 220 else doc.get("clean_abstract", ""),
                    url=doc["url"],
                    published=doc["published"],
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
                "matched_terms": [],
            }
            for result in self.search(query, top_k=top_k)
        ]


def default_paths(project_root: str | Path) -> tuple[Path, Path]:
    root = Path(project_root)
    return (
        root / "data" / "processed" / "cleaned_documents.json",
        root / "data" / "index" / "semantic_embeddings.npy",
    )
