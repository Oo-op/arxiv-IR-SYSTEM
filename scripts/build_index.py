#!/usr/bin/env python3
"""Build vocabulary and inverted index from cleaned documents."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build vocabulary and inverted index.")
    parser.add_argument("--input", default=str(root / "data" / "processed" / "cleaned_documents.json"))
    parser.add_argument("--vocab-output", default=str(root / "data" / "index" / "vocab.json"))
    parser.add_argument("--index-output", default=str(root / "data" / "index" / "inverted_index.json"))
    parser.add_argument("--summary-output", default=str(root / "output" / "pipeline_summary.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    vocab_output_path = Path(args.vocab_output)
    index_output_path = Path(args.index_output)
    summary_output_path = Path(args.summary_output)

    vocab_output_path.parent.mkdir(parents=True, exist_ok=True)
    index_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    cleaned_payload = json.loads(input_path.read_text(encoding="utf-8"))
    documents = cleaned_payload.get("documents", [])

    document_frequency: Counter[str] = Counter()
    collection_frequency: Counter[str] = Counter()
    postings_map: defaultdict[str, list[dict]] = defaultdict(list)

    for doc in documents:
        doc_id = doc["doc_id"]
        tokens = doc.get("tokens", [])
        positions_map: defaultdict[str, list[int]] = defaultdict(list)
        for position, token in enumerate(tokens):
            positions_map[token].append(position)
        for term, positions in positions_map.items():
            document_frequency[term] += 1
            collection_frequency[term] += len(positions)
            postings_map[term].append(
                {
                    "doc_id": doc_id,
                    "tf": len(positions),
                    "positions": positions,
                }
            )

    sorted_terms = sorted(postings_map)
    vocab = {
        "document_count": len(documents),
        "term_count": len(sorted_terms),
        "terms": [
            {
                "term_id": index,
                "term": term,
                "document_frequency": document_frequency[term],
                "collection_frequency": collection_frequency[term],
            }
            for index, term in enumerate(sorted_terms, start=1)
        ],
    }

    inverted_index = {
        "document_count": len(documents),
        "term_count": len(sorted_terms),
        "index": {term: postings_map[term] for term in sorted_terms},
    }

    summary = {
        "source": cleaned_payload.get("source"),
        "category": cleaned_payload.get("category"),
        "document_count": len(documents),
        "term_count": len(sorted_terms),
        "avg_document_length": round(
            sum(doc.get("token_count", 0) for doc in documents) / len(documents), 2
        )
        if documents
        else 0.0,
        "files": {
            "cleaned_documents": str(input_path),
            "vocab": str(vocab_output_path),
            "inverted_index": str(index_output_path),
        },
    }

    vocab_output_path.write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding="utf-8")
    index_output_path.write_text(json.dumps(inverted_index, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved vocabulary to {vocab_output_path}")
    print(f"Saved inverted index to {index_output_path}")
    print(f"Saved summary to {summary_output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
