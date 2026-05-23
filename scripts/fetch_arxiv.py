#!/usr/bin/env python3
"""Scrape paper metadata from arXiv category and abstract pages."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path


LIST_URL_TEMPLATE = "https://arxiv.org/list/{category}/recent?skip={skip}&show={show}"
ABS_URL_TEMPLATE = "https://arxiv.org/abs/{paper_id}"
USER_AGENT = "InformationRetrievalCourseProject/1.0 ([email protected])"

ABS_LINK_PATTERN = re.compile(r'href\s*=\s*"/abs/([^"/?#]+)"')
TITLE_PATTERN = re.compile(
    r'<h1 class="title mathjax"><span class="descriptor">Title:</span>(.*?)</h1>',
    re.DOTALL,
)
AUTHORS_PATTERN = re.compile(
    r'<div class="authors"><span class="descriptor">Authors:</span>(.*?)</div>',
    re.DOTALL,
)
AUTHOR_NAME_PATTERN = re.compile(r">([^<]+)</a>")
ABSTRACT_PATTERN = re.compile(
    r'<blockquote class="abstract mathjax">\s*<span class="descriptor">Abstract:</span>(.*?)</blockquote>',
    re.DOTALL,
)
SUBMITTED_PATTERN = re.compile(r"\[Submitted on (.*?)\]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch documents from arXiv pages.")
    parser.add_argument("--category", default="cs.AI", help="arXiv category, e.g. cs.AI")
    parser.add_argument("--max-results", type=int, default=120, help="Number of documents to fetch")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[1] / "data" / "raw" / "documents.json"),
        help="Output JSON path",
    )
    return parser.parse_args()


def normalize_whitespace(text: str) -> str:
    return " ".join(html.unescape(text or "").split())


def fetch_html(url: str, retries: int = 4) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-Lk", "-A", USER_AGENT, url],
                check=True,
                capture_output=True,
                text=True,
            )
            if "Rate exceeded." in result.stdout:
                raise RuntimeError("arXiv rate limit exceeded")
            return result.stdout
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            last_error = exc
            message = str(exc)
            if "rate limit" in message.lower() and attempt < retries - 1:
                time.sleep(8 * (attempt + 1))
                continue
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"Failed to fetch URL: {url}. Last error: {last_error}")


def extract_paper_ids(list_html: str, max_results: int) -> list[str]:
    paper_ids: list[str] = []
    seen: set[str] = set()
    for match in ABS_LINK_PATTERN.findall(list_html):
        if match not in seen:
            seen.add(match)
            paper_ids.append(match)
        if len(paper_ids) >= max_results:
            break
    return paper_ids


def extract_first(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return normalize_whitespace(match.group(1)) if match else ""


def parse_abstract_page(paper_id: str, page_html: str, category: str, doc_id: int) -> dict:
    title = extract_first(TITLE_PATTERN, page_html)
    authors_html = extract_first(AUTHORS_PATTERN, page_html)
    abstract = extract_first(ABSTRACT_PATTERN, page_html)
    published = extract_first(SUBMITTED_PATTERN, page_html)
    authors = [normalize_whitespace(name) for name in AUTHOR_NAME_PATTERN.findall(authors_html)]

    return {
        "doc_id": doc_id,
        "arxiv_id": paper_id,
        "title": title,
        "abstract": abstract,
        "url": ABS_URL_TEMPLATE.format(paper_id=paper_id),
        "published": published,
        "updated": published,
        "authors": [name for name in authors if name],
        "categories": [category],
        "source": "arXiv",
        "topic": category,
    }


def fetch_documents(category: str, max_results: int) -> list[dict]:
    page_size = 100
    paper_ids: list[str] = []
    skip = 0
    while len(paper_ids) < max_results:
        list_url = LIST_URL_TEMPLATE.format(category=category, skip=skip, show=page_size)
        list_html = fetch_html(list_url)
        page_ids = extract_paper_ids(list_html, max_results=page_size)
        if not page_ids:
            break
        for paper_id in page_ids:
            if paper_id not in paper_ids:
                paper_ids.append(paper_id)
            if len(paper_ids) >= max_results:
                break
        skip += page_size

    documents: list[dict] = []
    for index, paper_id in enumerate(paper_ids, start=1):
        page_html = fetch_html(ABS_URL_TEMPLATE.format(paper_id=paper_id))
        documents.append(parse_abstract_page(paper_id, page_html, category=category, doc_id=index))
        time.sleep(0.5)
    return documents


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    documents = fetch_documents(category=args.category, max_results=args.max_results)
    payload = {
        "source": "arXiv Web Pages",
        "category": args.category,
        "document_count": len(documents),
        "documents": documents,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved {len(documents)} documents to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
