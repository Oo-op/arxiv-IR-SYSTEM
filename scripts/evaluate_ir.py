#!/usr/bin/env python3
"""Create manual evaluation templates and compute Precision@K."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ir_core import IRSystem, default_paths


DEFAULT_QUERIES = [
    "agent",
    "reasoning",
    "alignment",
    "retrieval",
    "multi-agent",
]


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Manual evaluation helper for the IR system.")
    parser.add_argument(
        "--mode",
        choices=["generate", "score"],
        default="generate",
        help="Generate labeling template or score a filled template",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Number of results per query")
    parser.add_argument("--project-root", default=str(root), help="Project root path")
    parser.add_argument(
        "--queries-file",
        default=str(root / "docs" / "evaluation_queries.json"),
        help="JSON file with query list",
    )
    parser.add_argument(
        "--csv-path",
        default=str(root / "output" / "evaluation_template.csv"),
        help="CSV template path",
    )
    parser.add_argument(
        "--summary-path",
        default=str(root / "output" / "evaluation_summary.json"),
        help="Evaluation summary output path",
    )
    return parser.parse_args()


def load_queries(path: Path) -> list[str]:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("queries", DEFAULT_QUERIES)
    return DEFAULT_QUERIES


def generate_template(system: IRSystem, queries: list[str], top_k: int, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "query",
                "rank",
                "doc_id",
                "score",
                "title",
                "snippet",
                "url",
                "published",
                "relevant",
                "note",
            ],
        )
        writer.writeheader()
        for query in queries:
            results = system.search_as_dicts(query, top_k=top_k)
            for item in results:
                writer.writerow(
                    {
                        "query": query,
                        "rank": item["rank"],
                        "doc_id": item["doc_id"],
                        "score": item["score"],
                        "title": item["title"],
                        "snippet": item["snippet"],
                        "url": item["url"],
                        "published": item["published"],
                        "relevant": "",
                        "note": "",
                    }
                )


def precision_at_k(rows: list[dict], k: int) -> float:
    top_rows = [row for row in rows if int(row["rank"]) <= k]
    if not top_rows:
        return 0.0
    relevant_count = sum(1 for row in top_rows if row["relevant"].strip() == "1")
    return relevant_count / len(top_rows)


def score_template(csv_path: Path, summary_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["query"], []).append(row)

    per_query = []
    for query, query_rows in grouped.items():
        query_rows.sort(key=lambda row: int(row["rank"]))
        per_query.append(
            {
                "query": query,
                "precision_at_5": round(precision_at_k(query_rows, 5), 4),
                "precision_at_10": round(precision_at_k(query_rows, 10), 4),
            }
        )

    avg_p5 = round(sum(item["precision_at_5"] for item in per_query) / len(per_query), 4) if per_query else 0.0
    avg_p10 = round(sum(item["precision_at_10"] for item in per_query) / len(per_query), 4) if per_query else 0.0
    summary = {
        "query_count": len(per_query),
        "average_precision_at_5": avg_p5,
        "average_precision_at_10": avg_p10,
        "per_query": per_query,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    queries_file = Path(args.queries_file)
    csv_path = Path(args.csv_path)
    summary_path = Path(args.summary_path)
    cleaned_documents_path, vocab_path, inverted_index_path = default_paths(args.project_root)

    if args.mode == "generate":
        queries = load_queries(queries_file)
        system = IRSystem(cleaned_documents_path, vocab_path, inverted_index_path)
        generate_template(system, queries, args.top_k, csv_path)
        print(f"Saved evaluation template to {csv_path}")
        return 0

    score_template(csv_path, summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
