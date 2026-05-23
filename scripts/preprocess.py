#!/usr/bin/env python3
"""Clean documents and tokenize English text."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+)*")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Preprocess crawled documents.")
    parser.add_argument("--input", default=str(root / "data" / "raw" / "documents.json"))
    parser.add_argument("--output", default=str(root / "data" / "processed" / "cleaned_documents.json"))
    return parser.parse_args()


def normalize_text(text: str) -> str:
    text = html.unescape(text or "")
    text = HTML_TAG_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def preprocess_document(document: dict) -> dict:
    clean_title = normalize_text(document.get("title", ""))
    clean_abstract = normalize_text(document.get("abstract", ""))
    combined_text = f"{clean_title} {clean_abstract}".strip()
    tokens = tokenize(combined_text)

    output = dict(document)
    output["clean_title"] = clean_title
    output["clean_abstract"] = clean_abstract
    output["tokens"] = tokens
    output["token_count"] = len(tokens)
    return output


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_payload = json.loads(input_path.read_text(encoding="utf-8"))
    cleaned_documents = [preprocess_document(doc) for doc in raw_payload.get("documents", [])]

    payload = {
        "source": raw_payload.get("source"),
        "category": raw_payload.get("category"),
        "document_count": len(cleaned_documents),
        "documents": cleaned_documents,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved {len(cleaned_documents)} cleaned documents to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
