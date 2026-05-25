#!/usr/bin/env python3
"""Command-line search interface for the IR project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ir_core import IRSystem, default_paths


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Search arXiv abstracts with TF-IDF and cosine similarity.")
    parser.add_argument("--query", help="One-shot query string")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results to return")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--interactive", action="store_true", help="Start an interactive query loop")
    parser.add_argument("--project-root", default=str(root), help="Project root path")
    return parser.parse_args()


def print_text_results(query: str, results: list[dict]) -> None:
    print(f"Query: {query}")
    print(f"Results: {len(results)}")
    print("-" * 80)
    if not results:
        print("No matching documents found.")
        return
    for item in results:
        print(f"Rank: {item['rank']}")
        print(f"Score: {item['score']:.6f}")
        print(f"Title: {item['title']}")
        print(f"Snippet: {item['snippet']}")
        print(f"URL: {item['url']}")
        print(f"Published: {item['published']}")
        print(f"Matched Terms: {', '.join(item['matched_terms'])}")
        print("-" * 80)


def run_single_query(system: IRSystem, query: str, top_k: int, as_json: bool) -> None:
    results = system.search_as_dicts(query, top_k=top_k)
    if as_json:
        print(json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2))
    else:
        print_text_results(query, results)


def run_interactive(system: IRSystem, top_k: int, as_json: bool) -> None:
    print("Interactive search mode. Type 'exit' to quit.")
    while True:
        query = input("Enter query: ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            continue
        run_single_query(system, query, top_k=top_k, as_json=as_json)


def main() -> int:
    args = parse_args()
    cleaned_documents_path, vocab_path, inverted_index_path = default_paths(args.project_root)
    system = IRSystem(cleaned_documents_path, vocab_path, inverted_index_path)

    if args.query:
        run_single_query(system, args.query, top_k=args.top_k, as_json=args.json)
        return 0
    if args.interactive:
        run_interactive(system, top_k=args.top_k, as_json=args.json)
        return 0

    raise SystemExit("Use --query for one-shot search or --interactive for interactive mode.")


if __name__ == "__main__":
    raise SystemExit(main())
