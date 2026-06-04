#!/usr/bin/env python3
"""Optional LLM-enhanced extraction through DashScope OpenAI-compatible API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from extract_ie import load_documents


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "documents.json"
DEFAULT_OUTPUT = ROOT / "output" / "llm_extraction_samples.json"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "glm-5"


LLM_SCHEMA_KEYS = [
    "research_problem",
    "method",
    "datasets",
    "metrics",
    "main_contribution",
    "key_findings",
    "sustainability_or_social_impact",
    "evidence_sentences",
    "confidence",
]


def get_dashscope_api_key() -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        return api_key
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, "DASHSCOPE_API_KEY")
            return str(value)
    except OSError:
        return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run optional LLM-enhanced IE on local arXiv abstracts.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--limit", type=int, default=5, help="Limit calls to control quota usage.")
    parser.add_argument("--doc-id", default="", help="Extract one local document by doc_id.")
    return parser.parse_args()


def build_prompt(document: dict) -> list[dict[str, str]]:
    title = document.get("clean_title") or document.get("title") or ""
    abstract = document.get("clean_abstract") or document.get("abstract") or ""
    system = (
        "You are an information extraction system for academic paper abstracts. "
        "Return strict JSON only. Do not include markdown. "
        "If an item is not mentioned, use an empty list or empty string."
    )
    user = f"""
Extract structured information from this arXiv paper.

Required JSON keys:
{", ".join(LLM_SCHEMA_KEYS)}

Field requirements:
- research_problem: one short sentence.
- method: list of methods, models, or algorithms.
- datasets: list of datasets or benchmarks.
- metrics: list of evaluation metrics.
- main_contribution: one short sentence.
- key_findings: list of experimental or analytical conclusions.
- sustainability_or_social_impact: list of environmental, safety, privacy, fairness, or social impacts.
- evidence_sentences: 1-3 exact sentences or sentence fragments from the abstract.
- confidence: number from 0 to 1.

Title: {title}
Abstract: {abstract}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user.strip()}]


def parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        cleaned = cleaned[first : last + 1]
    data = json.loads(cleaned)
    return {key: data.get(key, [] if key.endswith("s") or key in {"method", "key_findings"} else "") for key in LLM_SCHEMA_KEYS}


def call_with_openai_sdk(api_key: str, base_url: str, model: str, messages: list[dict[str, str]], timeout: int) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    return completion.choices[0].message.content or "{}"


def call_with_stdlib_http(api_key: str, base_url: str, model: str, messages: list[dict[str, str]], timeout: int) -> str:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({"model": model, "messages": messages, "temperature": 0.1}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"] or "{}"


def extract_with_llm(
    document: dict,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = 60,
) -> dict:
    api_key = get_dashscope_api_key()
    if not api_key:
        return {"error": "DASHSCOPE_API_KEY is not configured."}

    try:
        messages = build_prompt(document)
        try:
            content = call_with_openai_sdk(api_key, base_url, model, messages, timeout)
            client_type = "openai-sdk"
        except ImportError:
            content = call_with_stdlib_http(api_key, base_url, model, messages, timeout)
            client_type = "stdlib-http"
        result = parse_json_response(content)
        result["model"] = model
        result["client"] = client_type
        return result
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {exc.code}: {detail}", "model": model}
    except Exception as exc:
        return {"error": str(exc), "model": model}


def select_documents(documents: list[dict], doc_id: str, limit: int) -> list[dict]:
    if doc_id:
        return [document for document in documents if str(document.get("doc_id")) == str(doc_id)]
    return documents[: max(limit, 0)]


def main() -> int:
    args = parse_args()
    documents = load_documents(Path(args.input))
    selected = select_documents(documents, args.doc_id, args.limit)
    records = []
    for document in selected:
        records.append(
            {
                "doc_id": document.get("doc_id"),
                "title": document.get("title"),
                "llm_extracted": extract_with_llm(document, model=args.model, base_url=args.base_url),
            }
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(records)} LLM extraction records to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
