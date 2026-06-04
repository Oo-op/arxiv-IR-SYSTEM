#!/usr/bin/env python3
"""Generate and score a manual evaluation template for extraction results."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "output" / "extraction_results.json"
DEFAULT_TEMPLATE = ROOT / "output" / "manual_evaluation_template.csv"
DEFAULT_SCORE = ROOT / "output" / "manual_evaluation_summary.json"
EVAL_FIELDS = [
    "research_tasks",
    "methods",
    "datasets",
    "metrics",
    "tfidf_keyphrases",
    "application_domains",
    "sustainability_points",
    "system_names",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual evaluation helper for IE results.")
    parser.add_argument("--mode", choices=["generate", "score"], default="generate")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--summary", default=str(DEFAULT_SCORE))
    parser.add_argument("--max-docs", type=int, default=30)
    return parser.parse_args()


def generate_template(results_path: Path, template_path: Path, max_docs: int) -> None:
    records = json.loads(results_path.read_text(encoding="utf-8"))
    rows = []
    for record in records[:max_docs]:
        for field in EVAL_FIELDS:
            values = record["extracted"].get(field, [])
            if not values:
                continue
            rows.append(
                {
                    "doc_id": record["doc_id"],
                    "title": record["title"],
                    "field": field,
                    "extracted_value": "; ".join(map(str, values)),
                    "evidence": " | ".join(record.get("evidence", [])),
                    "manual_correct": "",
                    "comment": "",
                }
            )
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with template_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["doc_id", "title", "field", "extracted_value", "evidence", "manual_correct", "comment"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved manual evaluation template with {len(rows)} rows to: {template_path}")
    print("Fill manual_correct with 1 for correct and 0 for wrong, then run --mode score.")


def score_template(template_path: Path, summary_path: Path) -> None:
    total = 0
    correct = 0
    by_field: dict[str, dict[str, int]] = {}
    with template_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            label = (row.get("manual_correct") or "").strip()
            if label not in {"0", "1"}:
                continue
            field = row["field"]
            by_field.setdefault(field, {"labeled": 0, "correct": 0})
            by_field[field]["labeled"] += 1
            by_field[field]["correct"] += int(label)
            total += 1
            correct += int(label)

    summary = {
        "labeled_items": total,
        "correct_items": correct,
        "accuracy": round(correct / total, 4) if total else None,
        "by_field": {
            field: {
                **counts,
                "accuracy": round(counts["correct"] / counts["labeled"], 4) if counts["labeled"] else None,
            }
            for field, counts in by_field.items()
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    if args.mode == "generate":
        generate_template(Path(args.results), Path(args.template), args.max_docs)
    else:
        score_template(Path(args.template), Path(args.summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
