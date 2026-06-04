#!/usr/bin/env python3
"""Interactive web UI for local, TF-IDF, and optional LLM information extraction."""

from __future__ import annotations

import argparse
import html
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from extract_ie import build_idf, extract_document, load_documents

try:
    from llm_extractor import extract_with_llm
except ImportError:
    extract_with_llm = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "documents.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the interactive IE web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--llm-model", default="glm-5")
    return parser.parse_args()


def make_custom_document(title: str, abstract: str) -> dict:
    return {
        "doc_id": "custom",
        "title": title.strip() or "Custom input",
        "abstract": abstract.strip(),
        "authors": [],
        "categories": ["custom"],
        "url": "",
        "published": "",
        "updated": "",
    }


def field_list(values: object) -> str:
    if isinstance(values, list):
        if not values:
            return "<span class='empty'>未抽取到</span>"
        return "".join(f"<li>{html.escape(str(value))}</li>" for value in values)
    if values in ("", None, 0):
        return "<span class='empty'>未抽取到</span>"
    return f"<li>{html.escape(str(values))}</li>"


def attach_llm(record: dict, document: dict, model: str) -> dict:
    if extract_with_llm is None:
        record["llm_extracted"] = {"error": "llm_extractor.py is unavailable."}
        return record
    record["llm_extracted"] = extract_with_llm(document, model=model)
    return record


def render_llm_result(record: dict) -> str:
    llm_data = record.get("llm_extracted")
    if not llm_data:
        return ""
    if llm_data.get("error"):
        return f"""
      <section class="evidence">
        <h3>大模型增强抽取</h3>
        <p class="message">{html.escape(llm_data['error'])}</p>
      </section>
      """
    fields = [
        ("研究问题", "research_problem"),
        ("方法/模型", "method"),
        ("数据集/基准", "datasets"),
        ("评价指标", "metrics"),
        ("主要贡献", "main_contribution"),
        ("关键结论", "key_findings"),
        ("可持续/社会影响", "sustainability_or_social_impact"),
        ("证据片段", "evidence_sentences"),
    ]
    items = "\n".join(
        f"<section class='field'><h3>{label}</h3><ul>{field_list(llm_data.get(key))}</ul></section>"
        for label, key in fields
    )
    confidence = html.escape(str(llm_data.get("confidence", "")))
    model = html.escape(str(llm_data.get("model", "")))
    return f"""
      <section class="evidence">
        <h3>大模型增强抽取</h3>
        <p>模型：{model}　置信度：{confidence}</p>
        <div class="grid">{items}</div>
      </section>
    """


def render_result(record: dict | None) -> str:
    if not record:
        return ""
    extracted = record["extracted"]
    fields = [
        ("论文编号", "arxiv_id"),
        ("发表年份", "publication_year"),
        ("作者数量", "author_count"),
        ("研究任务", "research_tasks"),
        ("方法/模型", "methods"),
        ("数据集/基准", "datasets"),
        ("评价指标", "metrics"),
        ("TF-IDF 关键词", "tfidf_keyphrases"),
        ("应用领域", "application_domains"),
        ("可持续/社会影响", "sustainability_points"),
        ("系统名称", "system_names"),
    ]
    items = "\n".join(
        f"<section class='field'><h3>{label}</h3><ul>{field_list(extracted.get(key))}</ul></section>"
        for label, key in fields
    )
    evidence = "".join(f"<li>{html.escape(sentence)}</li>" for sentence in record.get("evidence", []))
    evidence_html = evidence or "<li class='empty'>暂无证据句</li>"
    return f"""
    <article class="result panel">
      <div class="result-head">
        <div>
          <h2>{html.escape(record['title'])}</h2>
          <p>{html.escape(record.get('published') or '')}</p>
        </div>
        <strong>{record['confidence']}</strong>
      </div>
      <div class="grid">{items}</div>
      <section class="evidence">
        <h3>规则/TF-IDF 证据句</h3>
        <ul>{evidence_html}</ul>
      </section>
      {render_llm_result(record)}
    </article>
    """


def render_page(documents: list[dict], result: dict | None = None, message: str = "") -> bytes:
    options = "\n".join(
        f"<option value='{doc['doc_id']}'>{doc['doc_id']} - {html.escape(doc.get('title', '')[:90])}</option>"
        for doc in documents[:120]
    )
    body = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>arXiv 信息抽取系统</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; color: #20242a; background: #f6f8fb; }}
    header {{ background: #223044; color: #fff; padding: 18px 28px; }}
    h1 {{ font-size: 22px; margin: 0; letter-spacing: 0; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 22px; }}
    .panel {{ background: #fff; border: 1px solid #d8dee8; border-radius: 6px; padding: 18px; margin-bottom: 16px; }}
    .controls {{ display: grid; grid-template-columns: minmax(260px, 1fr) 120px; gap: 10px; align-items: end; }}
    label {{ display: block; font-weight: 700; margin-bottom: 6px; }}
    select, input, textarea {{ width: 100%; border: 1px solid #b8c2d1; border-radius: 4px; padding: 9px; font: inherit; background: #fff; }}
    textarea {{ min-height: 160px; resize: vertical; }}
    button {{ border: 0; border-radius: 4px; background: #245b8f; color: #fff; padding: 10px 14px; font-weight: 700; cursor: pointer; }}
    button:hover {{ background: #1b4a76; }}
    .two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .check {{ display: flex; align-items: center; gap: 8px; margin-top: 10px; font-weight: 400; }}
    .check input {{ width: auto; }}
    .message {{ color: #9a3412; margin: 0 0 12px; }}
    .result-head {{ display: flex; justify-content: space-between; gap: 16px; border-bottom: 1px solid #d8dee8; padding-bottom: 12px; }}
    .result-head h2 {{ font-size: 20px; margin: 0 0 6px; }}
    .result-head p {{ margin: 0; color: #64748b; }}
    .result-head strong {{ display: inline-flex; align-items: center; justify-content: center; min-width: 70px; height: 38px; border-radius: 4px; background: #e6f0fa; color: #16456f; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
    .field {{ border: 1px solid #d8dee8; border-radius: 6px; padding: 12px; background: #fbfcfe; }}
    .field h3, .evidence h3 {{ font-size: 15px; margin: 0 0 8px; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin: 4px 0; overflow-wrap: anywhere; }}
    .empty {{ color: #778292; }}
    .evidence {{ margin-top: 14px; border-top: 1px solid #d8dee8; padding-top: 12px; }}
    @media (max-width: 800px) {{
      .controls, .two, .grid {{ grid-template-columns: 1fr; }}
      main {{ padding: 14px; }}
    }}
  </style>
</head>
<body>
  <header><h1>arXiv 论文摘要信息抽取系统</h1></header>
  <main>
    <section class="panel">
      <form method="get" action="/">
        <label for="doc_id">从本地 120 篇论文中选择一篇抽取</label>
        <div class="controls">
          <select id="doc_id" name="doc_id">{options}</select>
          <button type="submit">抽取</button>
        </div>
        <label class="check"><input type="checkbox" name="use_llm" value="1"> 使用 glm-5 大模型增强抽取</label>
      </form>
    </section>
    <section class="panel">
      <form method="post" action="/extract">
        <div class="two">
          <div>
            <label for="title">自定义论文标题</label>
            <input id="title" name="title" placeholder="输入标题">
          </div>
          <div>
            <label for="abstract">自定义摘要</label>
            <textarea id="abstract" name="abstract" placeholder="粘贴英文论文摘要"></textarea>
          </div>
        </div>
        <label class="check"><input type="checkbox" name="use_llm" value="1"> 使用 glm-5 大模型增强抽取</label>
        <p style="margin: 12px 0 0;"><button type="submit">抽取自定义文本</button></p>
      </form>
    </section>
    {f"<p class='message'>{html.escape(message)}</p>" if message else ""}
    {render_result(result)}
  </main>
</body>
</html>
"""
    return body.encode("utf-8")


def make_handler(documents: list[dict], idf: dict[str, float], llm_model: str):
    by_id = {str(document.get("doc_id")): document for document in documents}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = parse_qs(urlparse(self.path).query)
            result = None
            message = ""
            doc_id = (query.get("doc_id") or [""])[0]
            use_llm = (query.get("use_llm") or [""])[0] == "1"
            if doc_id:
                document = by_id.get(doc_id)
                if document:
                    result = extract_document(document, idf)
                    if use_llm:
                        result = attach_llm(result, document, llm_model)
                else:
                    message = f"未找到 doc_id={doc_id} 的本地论文。"
            self.respond(render_page(documents, result, message))

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/extract":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(length).decode("utf-8")
            form = parse_qs(payload)
            title = (form.get("title") or [""])[0]
            abstract = (form.get("abstract") or [""])[0]
            use_llm = (form.get("use_llm") or [""])[0] == "1"
            result = None
            message = ""
            if title.strip() or abstract.strip():
                document = make_custom_document(title, abstract)
                result = extract_document(document, idf)
                if use_llm:
                    result = attach_llm(result, document, llm_model)
            else:
                message = "请输入标题或摘要。"
            self.respond(render_page(documents, result, message))

        def respond(self, content: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> int:
    args = parse_args()
    documents = load_documents(Path(args.data))
    idf = build_idf(documents)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(documents, idf, args.llm_model))
    print(f"Web app running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
