#!/usr/bin/env python3
"""Rule-based information extraction for local arXiv abstracts."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from math import log
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "documents.json"
DEFAULT_OUTPUT_DIR = ROOT / "output"

ARXIV_ID_RE = re.compile(r"\b\d{4}\.\d{4,5}(?:v\d+)?\b")
YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
TOKEN_RE = re.compile(r"[a-z][a-z0-9.-]{2,}")

STOPWORDS = {
    "about", "across", "after", "against", "also", "although", "among",
    "approach", "based", "because", "been", "being", "between", "can",
    "could", "demonstrate", "different", "does", "each", "effective",
    "evaluate", "existing", "experiment", "framework", "from", "have",
    "however", "into", "large", "many", "method", "model", "more", "most",
    "new", "only", "paper", "performance", "propose", "provide", "results",
    "show", "significant", "such", "system", "than", "that", "their",
    "there", "these", "this", "through", "using", "with",
}

TASK_PATTERNS = {
    "autonomous agents": r"\b(agentic systems?|autonomous agents?|multi-agent)\b",
    "reasoning": r"\b(reasoning|chain-of-thought|logical inference|deduction)\b",
    "planning": r"\b(planning|task decomposition|decision making)\b",
    "retrieval": r"\b(retrieval|information retrieval|search|ranking|RAG)\b",
    "reinforcement learning": r"\b(reinforcement learning|RL|reward model)\b",
    "code generation": r"\b(code generation|program synthesis|software engineering)\b",
    "machine translation": r"\b(machine translation|translation)\b",
    "knowledge graphs": r"\b(knowledge graphs?|KGs?)\b",
    "robotics": r"\b(robotics?|embodied)\b",
    "alignment": r"\b(alignment|preference learning|AI safety)\b",
}

METHOD_PATTERNS = {
    "large language models": r"\b(LLMs?|large language models?|language models?)\b",
    "transformers": r"\b(transformers?|attention)\b",
    "retrieval augmented generation": r"\b(retrieval[- ]augmented generation|RAG)\b",
    "fine-tuning": r"\b(fine[- ]tuning|instruction tuning|LoRA)\b",
    "prompting": r"\b(prompting|prompt engineering|few-shot|zero-shot)\b",
    "graph neural networks": r"\b(graph neural networks?|GNNs?)\b",
    "Monte Carlo tree search": r"\b(Monte Carlo tree search|MCTS)\b",
    "Bayesian methods": r"\b(Bayesian|probabilistic model)\b",
    "benchmarking": r"\b(benchmark|evaluation suite|leaderboard)\b",
    "self-improvement": r"\b(self[- ]evolution|self[- ]improvement|self[- ]reflection)\b",
}

METRIC_PATTERNS = {
    "accuracy": r"\b(accuracy|acc\.)\b",
    "precision": r"\bprecision\b",
    "recall": r"\brecall\b",
    "F1": r"\bF1(?:[- ]score)?\b",
    "AUC": r"\bAUC\b",
    "BLEU": r"\bBLEU\b",
    "ROUGE": r"\bROUGE\b",
    "pass@k": r"\bpass@\d+|pass@k\b",
    "win rate": r"\bwin rate\b",
    "success rate": r"\bsuccess rate\b",
}

DATASET_HINT_RE = re.compile(
    r"\b(?:on|using|with|from|over)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9_.-]*(?:\s+[A-Z][A-Za-z0-9_.-]*){0,3})\s+"
    r"(?:dataset|benchmark|corpus|suite|leaderboard)s?\b"
)
KNOWN_DATASET_RE = re.compile(
    r"\b(MMLU|GSM8K|HumanEval|MBPP|ARC|HellaSwag|TruthfulQA|"
    r"ImageNet|COCO|SQuAD|GLUE|SuperGLUE|CIFAR-10|CIFAR-100|"
    r"HotpotQA|Natural Questions|WMT|BIG-bench|GAIA)\b"
)

DOMAIN_PATTERNS = {
    "healthcare": r"\b(healthcare|medical|clinical|biomedical|patient)\b",
    "education": r"\b(education|student|teaching|learning analytics)\b",
    "software": r"\b(software|programming|code|developer)\b",
    "science": r"\b(scientific|biology|chemistry|physics|mathematics)\b",
    "legal": r"\b(legal|law|contract|court)\b",
    "finance": r"\b(finance|financial|trading|market)\b",
    "robotics": r"\b(robotics?|embodied|navigation)\b",
    "social media": r"\b(social media|online community|misinformation)\b",
}

SUSTAINABILITY_PATTERNS = {
    "computing efficiency": r"\b(efficient|efficiency|low[- ]resource|lightweight|cost|compute|latency)\b",
    "energy/carbon": r"\b(energy|carbon|emission|sustainab(?:le|ility))\b",
    "fairness/bias": r"\b(fairness|bias|stereotype|discrimination)\b",
    "privacy/security": r"\b(privacy|security|confidential|attack|jailbreak)\b",
    "safety/robustness": r"\b(safety|safe|robustness|reliability|harmful)\b",
    "human/social impact": r"\b(human|user|societal|social impact|trust)\b",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract information points from arXiv abstracts.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Local JSON document file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for JSON/CSV/HTML outputs.")
    parser.add_argument("--limit", type=int, default=0, help="Optional document limit for debugging.")
    return parser.parse_args()


def clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]


def tokenize_for_tfidf(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def build_idf(documents: list[dict]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for document in documents:
        title = clean_text(document.get("clean_title") or document.get("title"))
        abstract = clean_text(document.get("clean_abstract") or document.get("abstract"))
        document_frequency.update(set(tokenize_for_tfidf(f"{title} {abstract}")))
    document_count = max(len(documents), 1)
    return {
        token: log((document_count + 1) / (frequency + 1)) + 1.0
        for token, frequency in document_frequency.items()
    }


def extract_tfidf_keyphrases(text: str, idf: dict[str, float] | None, top_k: int = 8) -> list[str]:
    if not idf:
        return []
    term_frequency = Counter(tokenize_for_tfidf(text))
    scores = {
        token: frequency * idf.get(token, 1.0)
        for token, frequency in term_frequency.items()
        if len(token) > 2
    }
    return [token for token, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]]


def find_labels(text: str, patterns: dict[str, str]) -> list[str]:
    labels = []
    for label, pattern in patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            labels.append(label)
    return labels


def find_datasets(text: str) -> list[str]:
    values = set(KNOWN_DATASET_RE.findall(text))
    for match in DATASET_HINT_RE.findall(text):
        candidate = re.sub(r"\s+", " ", match).strip(" .,;:")
        if len(candidate) > 1 and not candidate.lower().startswith(("this", "our", "a", "an")):
            values.add(candidate)
    return sorted(values)


def find_system_names(title: str, text: str) -> list[str]:
    values = set()
    title_prefix = title.split(":", 1)[0].strip()
    if re.fullmatch(r"[A-Z][A-Z0-9_.-]{1,12}", title_prefix):
        values.add(title_prefix)
    for token in re.findall(r"\b[A-Z][A-Z0-9_.-]{2,12}\b", f"{title} {text}"):
        if token not in {"IEEE", "API", "URL"}:
            values.add(token)
    return sorted(values)[:8]


def evidence_sentences(text: str, extracted_values: list[str], max_items: int = 3) -> list[str]:
    sentences = split_sentences(text)
    evidence = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(value.lower() in lower for value in extracted_values):
            evidence.append(sentence)
        if len(evidence) >= max_items:
            break
    return evidence


def confidence_score(fields: dict[str, list[str] | str | int]) -> float:
    weighted_keys = {
        "research_tasks": 0.16,
        "methods": 0.16,
        "tfidf_keyphrases": 0.14,
        "datasets": 0.14,
        "metrics": 0.12,
        "application_domains": 0.10,
        "sustainability_points": 0.10,
        "system_names": 0.08,
    }
    score = 0.0
    for key, weight in weighted_keys.items():
        values = fields.get(key, [])
        if isinstance(values, list) and values:
            score += weight
    return round(score, 3)


def extract_document(document: dict, idf: dict[str, float] | None = None) -> dict:
    title = clean_text(document.get("clean_title") or document.get("title"))
    abstract = clean_text(document.get("clean_abstract") or document.get("abstract"))
    full_text = f"{title}. {abstract}"
    url = clean_text(document.get("url"))
    arxiv_match = ARXIV_ID_RE.search(clean_text(document.get("arxiv_id")) or url)
    year_match = YEAR_RE.search(clean_text(document.get("published")) or clean_text(document.get("updated")))

    fields: dict[str, list[str] | str | int] = {
        "arxiv_id": arxiv_match.group(0) if arxiv_match else "",
        "publication_year": year_match.group(1) if year_match else "",
        "authors": document.get("authors", []),
        "author_count": len(document.get("authors", [])),
        "categories": document.get("categories", []),
        "research_tasks": find_labels(full_text, TASK_PATTERNS),
        "methods": find_labels(full_text, METHOD_PATTERNS),
        "datasets": find_datasets(full_text),
        "metrics": find_labels(full_text, METRIC_PATTERNS),
        "tfidf_keyphrases": extract_tfidf_keyphrases(full_text, idf),
        "application_domains": find_labels(full_text, DOMAIN_PATTERNS),
        "sustainability_points": find_labels(full_text, SUSTAINABILITY_PATTERNS),
        "system_names": find_system_names(title, abstract),
    }
    extracted_values = []
    for value in fields.values():
        if isinstance(value, list):
            extracted_values.extend(str(item) for item in value)
        elif value:
            extracted_values.append(str(value))

    return {
        "doc_id": document.get("doc_id"),
        "title": title,
        "url": url,
        "published": document.get("published", ""),
        "extracted": fields,
        "confidence": confidence_score(fields),
        "evidence": evidence_sentences(full_text, extracted_values),
    }


def load_documents(path: Path, limit: int = 0) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = payload.get("documents", [])
    return documents[:limit] if limit else documents


def write_csv(records: list[dict], path: Path) -> None:
    fieldnames = [
        "doc_id",
        "title",
        "arxiv_id",
        "publication_year",
        "author_count",
        "research_tasks",
        "methods",
        "datasets",
        "metrics",
        "tfidf_keyphrases",
        "application_domains",
        "sustainability_points",
        "system_names",
        "confidence",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            extracted = record["extracted"]
            row = {
                "doc_id": record["doc_id"],
                "title": record["title"],
                "confidence": record["confidence"],
            }
            for key in fieldnames:
                if key in row:
                    continue
                value = extracted.get(key, "")
                row[key] = "; ".join(map(str, value)) if isinstance(value, list) else value
            writer.writerow(row)


def summarize(records: list[dict]) -> dict:
    counters: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        for key, value in record["extracted"].items():
            if isinstance(value, list):
                counters[key].update(map(str, value))
            elif value not in ("", 0, None):
                counters[key].update([str(value)])
    return {
        "document_count": len(records),
        "average_confidence": round(sum(r["confidence"] for r in records) / max(len(records), 1), 3),
        "coverage": {
            key: sum(1 for r in records if r["extracted"].get(key))
            for key in [
                "research_tasks",
                "methods",
                "datasets",
                "metrics",
                "tfidf_keyphrases",
                "application_domains",
                "sustainability_points",
                "system_names",
            ]
        },
        "top_values": {key: counter.most_common(10) for key, counter in counters.items()},
    }


def write_html(records: list[dict], summary: dict, path: Path) -> None:
    rows = []
    for record in records:
        extracted = record["extracted"]
        rows.append(
            "<tr>"
            f"<td>{record['doc_id']}</td>"
            f"<td><a href='{html.escape(record['url'])}'>{html.escape(record['title'])}</a></td>"
            f"<td>{html.escape('; '.join(extracted['research_tasks']))}</td>"
            f"<td>{html.escape('; '.join(extracted['methods']))}</td>"
            f"<td>{html.escape('; '.join(extracted['datasets']))}</td>"
            f"<td>{html.escape('; '.join(extracted['metrics']))}</td>"
            f"<td>{html.escape('; '.join(extracted['tfidf_keyphrases']))}</td>"
            f"<td>{html.escape('; '.join(extracted['sustainability_points']))}</td>"
            f"<td>{record['confidence']}</td>"
            "</tr>"
        )
    content = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>arXiv 信息抽取结果</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 24px; color: #1f2933; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px; vertical-align: top; }}
    th {{ background: #f0f4f8; text-align: left; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }}
    .box {{ border: 1px solid #d9e2ec; padding: 12px; border-radius: 6px; background: #f8fafc; }}
  </style>
</head>
<body>
  <h1>arXiv cs.AI 信息抽取实验结果</h1>
  <div class="summary">
    <div class="box">文档数<br><strong>{summary['document_count']}</strong></div>
    <div class="box">平均置信度<br><strong>{summary['average_confidence']}</strong></div>
    <div class="box">任务覆盖<br><strong>{summary['coverage']['research_tasks']}</strong></div>
    <div class="box">可持续相关覆盖<br><strong>{summary['coverage']['sustainability_points']}</strong></div>
  </div>
  <table>
    <thead><tr><th>ID</th><th>论文</th><th>研究任务</th><th>方法/模型</th><th>数据集</th><th>指标</th><th>TF-IDF关键词</th><th>可持续/社会影响</th><th>置信度</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    documents = load_documents(input_path, args.limit)
    idf = build_idf(documents)
    records = [extract_document(document, idf) for document in documents]
    summary = summarize(records)

    (output_dir / "extraction_results.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(records, output_dir / "extraction_results.csv")
    write_html(records, summary, output_dir / "results.html")

    print(f"Loaded documents: {len(documents)}")
    print(f"Saved JSON/CSV/HTML outputs to: {output_dir}")
    print(f"Average confidence: {summary['average_confidence']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
