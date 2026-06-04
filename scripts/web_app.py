#!/usr/bin/env python3
"""Simple web UI for the information retrieval project."""

from __future__ import annotations

import argparse
import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ir_core import IRSystem, default_paths

TOP_K = 20
SEARCH_METHODS = {
    "tfidf": ("TF-IDF", "余弦相似度"),
    "bm25": ("BM25", "BM25 评分"),
    "semantic": ("Semantic", "Sentence-BERT 语义相似度"),
}

PAGE_STYLE = """
<style>
  :root {
    --bg: #f6f1e8;
    --paper: #fffdfa;
    --ink: #1f2937;
    --muted: #6b7280;
    --line: #e5ded1;
    --accent: #b45309;
    --accent-dark: #7c2d12;
    --shadow: 0 16px 40px rgba(60, 41, 18, 0.08);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: Georgia, "Times New Roman", serif;
    color: var(--ink);
    background:
      radial-gradient(circle at top left, rgba(180, 83, 9, 0.15), transparent 30%),
      linear-gradient(180deg, #f8f3eb 0%, #f2ede4 100%);
    min-height: 100vh;
  }
  .wrap {
    max-width: 1080px;
    margin: 0 auto;
    padding: 32px 20px 64px;
  }
  .hero {
    background: linear-gradient(135deg, rgba(180, 83, 9, 0.12), rgba(124, 45, 18, 0.08));
    border: 1px solid rgba(124, 45, 18, 0.12);
    border-radius: 24px;
    padding: 32px;
    box-shadow: var(--shadow);
    margin-bottom: 24px;
  }
  .eyebrow {
    margin: 0 0 8px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent-dark);
    font-size: 12px;
    font-weight: 700;
  }
  h1 {
    margin: 0 0 10px;
    font-size: clamp(32px, 5vw, 52px);
    line-height: 1.05;
  }
  .hero p {
    margin: 0;
    max-width: 760px;
    color: var(--muted);
    font-size: 18px;
    line-height: 1.7;
  }
  .search-card, .result-card, .meta-card {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 20px;
    box-shadow: var(--shadow);
  }
  .search-card {
    padding: 24px;
    margin-bottom: 24px;
  }
  form {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 180px 140px;
    gap: 12px;
    align-items: end;
  }
  label {
    display: block;
    font-size: 14px;
    margin-bottom: 8px;
    color: var(--accent-dark);
    font-weight: 700;
  }
  input, select, button {
    width: 100%;
    border-radius: 14px;
    border: 1px solid #d6c9b5;
    padding: 14px 16px;
    font-size: 16px;
    background: #fffefb;
    color: var(--ink);
  }
  input:focus, select:focus {
    outline: 2px solid rgba(180, 83, 9, 0.25);
    border-color: var(--accent);
  }
  button {
    border: none;
    background: linear-gradient(135deg, var(--accent), var(--accent-dark));
    color: white;
    font-weight: 700;
    cursor: pointer;
  }
  .summary {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin: 16px 0 0;
    color: var(--muted);
    font-size: 14px;
  }
  .summary span {
    background: #f7efe3;
    border: 1px solid #ead9c0;
    padding: 8px 12px;
    border-radius: 999px;
  }
  .results {
    display: grid;
    gap: 16px;
  }
  .result-card {
    padding: 24px;
  }
  .result-head {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: start;
    margin-bottom: 12px;
  }
  .rank {
    display: inline-flex;
    min-width: 42px;
    justify-content: center;
    padding: 8px 10px;
    border-radius: 999px;
    background: #2f2419;
    color: white;
    font-weight: 700;
  }
  .score {
    color: var(--accent-dark);
    font-weight: 700;
    white-space: nowrap;
  }
  .result-card h2 {
    margin: 0 0 8px;
    font-size: 24px;
    line-height: 1.3;
  }
  .snippet {
    margin: 0 0 14px;
    color: #4b5563;
    line-height: 1.7;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 14px;
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 10px;
  }
  .terms {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .terms span {
    background: #fff6eb;
    border: 1px solid #f0d3ac;
    color: var(--accent-dark);
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 13px;
  }
  .empty {
    padding: 36px 24px;
    text-align: center;
    color: var(--muted);
  }
  .meta-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }
  .meta-card {
    padding: 18px 20px;
  }
  .meta-card strong {
    display: block;
    font-size: 28px;
    margin-top: 8px;
  }
  a {
    color: var(--accent-dark);
    text-decoration: none;
  }
  a:hover { text-decoration: underline; }
  @media (max-width: 760px) {
    form, .meta-grid { grid-template-columns: 1fr; }
    .result-head { flex-direction: column; }
  }
</style>
"""


def build_page(
    query: str,
    method: str,
    results: list[dict],
    system: IRSystem,
    error_message: str = "",
) -> str:
    escaped_query = html.escape(query)
    selected_method = method if method in SEARCH_METHODS else "tfidf"
    method_name, score_label = SEARCH_METHODS[selected_method]
    result_count = len(results)
    result_cards = []
    for item in results:
        terms_html = "".join(f"<span>{html.escape(term)}</span>" for term in item["matched_terms"])
        result_cards.append(
            f"""
            <article class="result-card">
              <div class="result-head">
                <span class="rank">#{item['rank']}</span>
                <span class="score">Score: {item['score']:.6f}</span>
              </div>
              <h2>{html.escape(item['title'])}</h2>
              <p class="snippet">{html.escape(item['snippet'])}</p>
              <div class="meta">
                <span>Doc ID: {item['doc_id']}</span>
                <span>Date: {html.escape(item['published'])}</span>
                <span><a href="{html.escape(item['url'])}" target="_blank" rel="noopener noreferrer">Open arXiv page</a></span>
              </div>
              <div class="terms">{terms_html}</div>
            </article>
            """
        )

    if error_message:
        result_cards.append(f'<div class="result-card empty">{html.escape(error_message)}</div>')
    elif not result_cards and query:
        result_cards.append('<div class="result-card empty">没有找到匹配结果，请尝试更换关键词。</div>')
    elif not query:
        result_cards.append(
            '<div class="result-card empty">输入英文查询词，例如 <strong>reasoning</strong>、<strong>agent</strong>、<strong>retrieval</strong>。</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Information Retrieval System</title>
  {PAGE_STYLE}
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <p class="eyebrow">Course Project</p>
      <h1>arXiv 论文摘要信息检索系统</h1>
      <p>基于 120 篇 <code>cs.AI</code> 论文摘要构建倒排索引，支持 TF-IDF、BM25 与语义检索。该页面直接复用命令行版本的检索核心。</p>
    </section>

    <section class="meta-grid">
      <div class="meta-card">语料库文档数<strong>{system.document_count}</strong></div>
      <div class="meta-card">词项数<strong>{len(system.term_stats)}</strong></div>
      <div class="meta-card">当前返回结果数<strong>{result_count}</strong></div>
    </section>

    <section class="search-card">
      <form method="get" action="/">
        <div>
          <label for="q">查询内容</label>
          <input id="q" name="q" value="{escaped_query}" placeholder="例如：multi-agent reasoning" />
        </div>
        <div>
          <label for="method">检索方式</label>
          <select id="method" name="method">
            {build_method_options(selected_method)}
          </select>
        </div>
        <div>
          <button type="submit">执行检索</button>
        </div>
      </form>
      <div class="summary">
        <span>查询字段：标题 + 摘要</span>
        <span>返回数量：Top {TOP_K}</span>
        <span>检索模型：{method_name}</span>
        <span>排序方式：{score_label}</span>
      </div>
    </section>

    <section class="results">
      {''.join(result_cards)}
    </section>
  </div>
</body>
</html>"""


def build_method_options(current_method: str) -> str:
    options = []
    for value, (label, _) in SEARCH_METHODS.items():
        selected = " selected" if value == current_method else ""
        options.append(f'<option value="{value}"{selected}>{label}</option>')
    return "".join(options)


def make_handler(system: IRSystem, project_root: Path):
    semantic_system = None

    def run_search(query: str, method: str) -> tuple[list[dict], str, str]:
        nonlocal semantic_system
        selected_method = method if method in SEARCH_METHODS else "tfidf"
        if not query:
            return [], selected_method, ""
        if selected_method in {"tfidf", "bm25"}:
            return system.search_as_dicts(query, top_k=TOP_K, method=selected_method), selected_method, ""
        try:
            if semantic_system is None:
                from semantic_search import SemanticIRSystem, default_paths as semantic_paths

                documents_path, embedding_path = semantic_paths(project_root)
                semantic_system = SemanticIRSystem(documents_path, embedding_cache_path=embedding_path)
            return semantic_system.search_as_dicts(query, top_k=TOP_K), selected_method, ""
        except Exception as exc:
            message = f"语义检索暂不可用：{exc}。当前 Python：{sys.executable}"
            return [], selected_method, message

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/search":
                self.handle_api(parsed)
                return
            if parsed.path != "/":
                self.send_error(404, "Not Found")
                return

            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            method = params.get("method", ["tfidf"])[0].strip().lower()
            results, selected_method, error_message = run_search(query, method)
            page = build_page(query, selected_method, results, system, error_message=error_message)
            payload = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def handle_api(self, parsed) -> None:
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            method = params.get("method", ["tfidf"])[0].strip().lower()
            results, selected_method, error_message = run_search(query, method)
            payload = json.dumps(
                {
                    "query": query,
                    "method": selected_method,
                    "top_k": TOP_K,
                    "result_count": len(results),
                    "error": error_message,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:
            return

    return RequestHandler


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run a simple local web UI for the IR system.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--project-root", default=str(root))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cleaned_documents_path, vocab_path, inverted_index_path = default_paths(args.project_root)
    system = IRSystem(cleaned_documents_path, vocab_path, inverted_index_path)
    handler = make_handler(system, Path(args.project_root))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
