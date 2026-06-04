# arXiv 论文摘要信息检索系统

这是一个面向信息检索课程作业的 arXiv 论文摘要检索系统。项目从 arXiv `cs.AI` 分类抓取论文元数据，对标题和摘要做英文文本预处理，构建词表与倒排索引，并提供 TF-IDF、BM25 和 Sentence-BERT 语义检索三种查询方式。

## 功能

- 抓取 arXiv 指定分类的论文标题、摘要、作者、发布日期和 URL。
- 对标题和摘要做 HTML 清理、大小写归一化、英文 tokenization。
- 构建词表、文档频率、词频、位置信息和倒排索引。
- 支持 TF-IDF 余弦相似度检索和 BM25 排序。
- 支持基于 `sentence-transformers` 的语义检索，并缓存文档向量。
- 提供命令行检索、交互式检索、本地 Web 页面和 JSON API。
- 提供人工评测模板生成与 Precision@5、Precision@10 统计。

## 项目结构

```text
arxiv-IR-SYSTEM/
├── data/
│   ├── raw/documents.json                 # arXiv 原始论文数据
│   ├── processed/cleaned_documents.json   # 清洗和分词后的论文数据
│   └── index/
│       ├── vocab.json                     # 词表和词频统计
│       ├── inverted_index.json            # 倒排索引
│       └── semantic_embeddings.npy        # Sentence-BERT 文档向量缓存
├── docs/
│   ├── evaluation_queries.json            # 评测查询词
│   └── 作业报告.docx                       # 课程作业报告
├── output/
│   ├── pipeline_summary.json              # 数据和索引构建摘要
│   ├── evaluation_template.csv            # 人工标注评测表
│   └── evaluation_summary.json            # 评测结果
├── scripts/
│   ├── fetch_arxiv.py                     # 抓取 arXiv 数据
│   ├── preprocess.py                      # 文本清洗和分词
│   ├── build_index.py                     # 构建词表和倒排索引
│   ├── run_pipeline.py                    # 串联完整数据处理流程
│   ├── ir_core.py                         # TF-IDF 和 BM25 检索核心
│   ├── semantic_search.py                 # 语义检索
│   ├── search_cli.py                      # 命令行检索入口
│   ├── web_app.py                         # 本地 Web 检索页面和 API
│   └── evaluate_ir.py                     # 人工评测工具
├── requirements.txt
└── README.md
```

## 当前数据

当前仓库已包含一份可直接运行的数据和索引：

- 数据来源：arXiv Web Pages
- 分类：`cs.AI`
- 文档数：120 篇论文摘要
- 词项数：5302
- 平均文档长度：197.24 tokens

当前人工评测结果：

- 查询数：5
- 平均 Precision@5：0.92
- 平均 Precision@10：0.9314

## 安装

建议使用 Python 3.10 或更新版本。

```bash
pip install -r requirements.txt
```

如果只运行 TF-IDF 或 BM25 检索，核心依赖主要是 `numpy`；语义检索需要额外下载 Sentence-BERT 模型，首次运行会较慢。

## 使用方法

### 命令行检索

```bash
# TF-IDF 检索，默认方法
python scripts/search_cli.py --query "multi-agent reasoning" --top-k 5

# BM25 检索
python scripts/search_cli.py --query "multi-agent reasoning" --method bm25 --top-k 5

# 语义检索
python scripts/search_cli.py --query "multi-agent reasoning" --method semantic --top-k 5

# 输出 JSON
python scripts/search_cli.py --query "retrieval augmented generation" --method bm25 --json

# 交互式检索
python scripts/search_cli.py --interactive --method tfidf
```

### Web 页面

```bash
python scripts/web_app.py --host 127.0.0.1 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000
```

Web 页面支持在页面中选择 `TF-IDF`、`BM25` 或 `Semantic`。其中语义检索会在首次使用时加载 Sentence-BERT 模型；如果模型或依赖不可用，页面会返回错误提示。

### JSON API

```bash
curl "http://127.0.0.1:8000/api/search?q=multi-agent%20reasoning&method=bm25"
```

支持参数：

- `q`：查询文本。
- `method`：`tfidf`、`bm25` 或 `semantic`，默认 `tfidf`。

Web API 固定返回最多 20 条结果。

## 重新生成数据和索引

运行完整流程：

```bash
python scripts/run_pipeline.py --category cs.AI --max-results 120
```

该命令会依次执行：

1. `scripts/fetch_arxiv.py`：抓取原始论文数据到 `data/raw/documents.json`。
2. `scripts/preprocess.py`：生成 `data/processed/cleaned_documents.json`。
3. `scripts/build_index.py`：生成 `data/index/vocab.json`、`data/index/inverted_index.json` 和 `output/pipeline_summary.json`。

也可以单独运行每一步：

```bash
python scripts/fetch_arxiv.py --category cs.AI --max-results 120
python scripts/preprocess.py
python scripts/build_index.py
```

## 评测

生成待人工标注的评测表：

```bash
python scripts/evaluate_ir.py --mode generate --top-k 10
```

脚本会读取 `docs/evaluation_queries.json` 中的查询词，并把结果写入 `output/evaluation_template.csv`。人工在 `relevant` 列标注 `1` 表示相关，其它值或空值表示不相关。

计算评测指标：

```bash
python scripts/evaluate_ir.py --mode score
```

结果写入 `output/evaluation_summary.json`，包含每个查询的 Precision@5、Precision@10 和平均值。

## 检索方法说明

| 方法 | 实现位置 | 说明 |
| --- | --- | --- |
| TF-IDF | `scripts/ir_core.py` | 对查询和文档构建 TF-IDF 权重，用余弦相似度排序。 |
| BM25 | `scripts/ir_core.py` | 使用 `k1=1.2`、`b=0.75`，结合文档长度归一化计算得分。 |
| Semantic | `scripts/semantic_search.py` | 使用 `all-MiniLM-L6-v2` 编码标题和摘要，通过余弦相似度排序。 |

## 注意事项

- `fetch_arxiv.py` 使用 `curl` 抓取网页，重新抓取数据时需要网络可用。
- 语义检索首次运行会下载模型，并把文档向量缓存到 `data/index/semantic_embeddings.npy`。
- 当前项目数据已经预先生成；只做检索演示时不需要重新抓取或重建索引。
- `.idea/` 等 IDE 本地配置不属于项目交付内容，不应提交。
