#!/usr/bin/env python3
"""Command-line search interface for the IR project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ir_core import IRSystem, default_paths as ir_core_paths


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Search arXiv abstracts with multiple retrieval methods.")
    parser.add_argument("--query", help="One-shot query string")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results to return")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--interactive", action="store_true", help="Start an interactive query loop")
    parser.add_argument("--project-root", default=str(root), help="Project root path")
    parser.add_argument(
        "--method",
        choices=["tfidf", "bm25", "semantic"],
        default="tfidf",
        help="Retrieval method: tfidf (default), bm25, or semantic"
    )
    return parser.parse_args()


def print_text_results(query: str, results: list[dict], method: str) -> None:
    print(f"Query: {query}")
    print(f"Method: {method.upper()}")
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
        if item.get("matched_terms"):
            print(f"Matched Terms: {', '.join(item['matched_terms'])}")
        print("-" * 80)


def run_single_query_tfidf(system: IRSystem, query: str, top_k: int, as_json: bool, method: str) -> None:
    results = system.search_as_dicts(query, top_k=top_k, method="tfidf")
    if as_json:
        print(json.dumps({"query": query, "method": method, "results": results}, ensure_ascii=False, indent=2))
    else:
        print_text_results(query, results, method)


def run_single_query_bm25(system: IRSystem, query: str, top_k: int, as_json: bool, method: str) -> None:
    results = system.search_as_dicts(query, top_k=top_k, method="bm25")
    if as_json:
        print(json.dumps({"query": query, "method": method, "results": results}, ensure_ascii=False, indent=2))
    else:
        print_text_results(query, results, method)


def run_single_query_semantic(system: SemanticIRSystem, query: str, top_k: int, as_json: bool, method: str) -> None:
    results = system.search_as_dicts(query, top_k=top_k)
    if as_json:
        print(json.dumps({"query": query, "method": method, "results": results}, ensure_ascii=False, indent=2))
    else:
        print_text_results(query, results, method)


def main() -> int:
    args = parse_args()
    method = args.method

    if method == "semantic":
        from semantic_search import SemanticIRSystem, default_paths as semantic_paths
        documents_path, embedding_path = semantic_paths(args.project_root)
        system = SemanticIRSystem(documents_path, embedding_cache_path=embedding_path)
    else:
        documents_path, vocab_path, index_path = ir_core_paths(args.project_root)
        system = IRSystem(documents_path, vocab_path, index_path)

    if args.query:
        if method == "tfidf":
            run_single_query_tfidf(system, args.query, top_k=args.top_k, as_json=args.json, method=method)
        elif method == "bm25":
            run_single_query_bm25(system, args.query, top_k=args.top_k, as_json=args.json, method=method)
        else:
            run_single_query_semantic(system, args.query, top_k=args.top_k, as_json=args.json, method=method)
        return 0

    if args.interactive:
        print(f"Interactive search mode ({method.upper()}). Type 'exit' to quit.")
        while True:
            query = input("Enter query: ").strip()
            if query.lower() in {"exit", "quit"}:
                break
            if not query:
                continue
            if method == "tfidf":
                run_single_query_tfidf(system, query, top_k=args.top_k, as_json=args.json, method=method)
            elif method == "bm25":
                run_single_query_bm25(system, query, top_k=args.top_k, as_json=args.json, method=method)
            else:
                run_single_query_semantic(system, query, top_k=args.top_k, as_json=args.json, method=method)
        return 0

    raise SystemExit("Use --query for one-shot search or --interactive for interactive mode.")


if __name__ == "__main__":
    raise SystemExit(main())
