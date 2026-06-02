# arXiv 论文摘要信息检索系统

基于 arXiv 学术论文摘要构建的信息检索系统，支持 TF-IDF、BM25 和语义检索三种算法。

## 功能特点

- **多种检索算法**：支持 TF-IDF、BM25 和基于 Sentence-BERT 的语义检索
- **命令行界面**：支持单次查询和交互式查询模式
- **Web 界面**：提供简洁的浏览器检索界面
- **人工评价**：支持生成评价模板和计算 Precision@K 指标
- **高效索引**：倒排索引持久化存储，支持快速查询

## 项目结构

```
arxiv-IR-SYSTEM/
├── data/
│   ├── raw/
│   │   └── documents.json          # 原始论文数据
│   ├── processed/
│   │   └── cleaned_documents.json  # 预处理后的数据
│   └── index/
│       ├── vocab.json              # 词汇表
│       ├── inverted_index.json     # 倒排索引
│       └── semantic_embeddings.npy # 语义嵌入缓存（可选）
├── scripts/
│   ├── fetch_arxiv.py              # 数据爬取
│   ├── preprocess.py               # 文本预处理
│   ├── build_index.py              # 索引构建
│   ├── run_pipeline.py             # 完整流程运行
│   ├── ir_core.py                  # 检索核心模块
│   ├── semantic_search.py          # 语义检索模块
│   ├── search_cli.py               # 命令行检索
│   ├── web_app.py                  # Web 界面
│   └── evaluate_ir.py              # 人工评价
├── output/
│   ├── evaluation_template.csv     # 评价模板
│   └── evaluation_summary.json     # 评价结果
├── docs/
│   └── evaluation_queries.json     # 测试查询词
└── requirements.txt                # 依赖配置
```

## 数据说明

- **数据源**：arXiv `cs.AI` 分类
- **文档数量**：120 篇论文摘要
- **包含字段**：标题、摘要、作者、发布日期、URL 等

## 安装说明

```bash
# 进入项目目录
cd arxiv-IR-SYSTEM

# 安装语义检索依赖（如使用语义检索）
pip install sentence-transformers torch numpy
```

## 使用方式

### 1. 命令行检索

```bash
# TF-IDF 检索（默认）
python scripts/search_cli.py --query "machine learning" --top-k 5

# BM25 检索
python scripts/search_cli.py --query "machine learning" --method bm25 --top-k 5

# 语义检索
python scripts/search_cli.py --query "machine learning" --method semantic --top-k 5

# 交互式模式
python scripts/search_cli.py --interactive --method bm25
```

### 2. Web 界面

```bash
# 启动 Web 服务
python scripts/web_app.py --host 127.0.0.1 --port 8000

# 访问地址
# 浏览器打开: http://127.0.0.1:8000
```

**注意**：Web 界面默认使用 **TF-IDF** 检索算法。如需使用其他算法，请参考下方"高级配置"部分。

### 3. API 接口

```bash
# 调用 API
curl "http://127.0.0.1:8000/api/search?q=machine%20learning&top_k=5"
```

### 4. 重新生成索引（可选）

```bash
# 完整流程：爬取 -> 预处理 -> 构建索引
python scripts/run_pipeline.py --category cs.AI --max-results 120
```

## 检索算法

| 算法 | 描述 | 特点 |
|------|------|------|
| **TF-IDF** | 向量空间模型 + 余弦相似度 | 经典词袋模型，简单高效 |
| **BM25** | 概率检索模型 | 考虑文档长度归一化，效果更优 |
| **Semantic** | Sentence-BERT 语义嵌入 | 基于语义理解，支持自然语言查询 |

## 人工评价

```bash
# 生成评价模板
python scripts/evaluate_ir.py --mode generate --top-k 10

# 计算评价指标（先手动标注 evaluation_template.csv）
python scripts/evaluate_ir.py --mode score
```

## 示例输出

```
Query: machine learning
Method: BM25
Results: 5
--------------------------------------------------------------------------------
Rank: 1
Score: 6.455302
Title: Moral Semantics Survive Machine Translation
Snippet: Recent advances in machine learning have demonstrated...
URL: https://arxiv.org/abs/2605.22660
Published: 21 May 2026
Matched Terms: machine, learning, translation
--------------------------------------------------------------------------------
```

## 配置说明

- **端口配置**：Web 服务默认端口 8000，可通过 `--port` 参数修改
- **检索数量**：默认返回 10 条结果，可通过 `--top-k` 参数修改
- **算法选择**：通过 `--method` 参数选择检索算法（tfidf/bm25/semantic）

## 高级配置

### 在 Web 界面中使用其他算法

Web 界面默认使用 TF-IDF 算法。如需在前端使用 BM25 算法，需要修改 `web_app.py` 文件：

1. **修改检索调用**（第 331 行附近）：
   ```python
   # 将
   results = system.search_as_dicts(query, top_k=top_k) if query else []
   # 修改为
   results = system.search_as_dicts(query, top_k=top_k, method="bm25") if query else []
   ```

2. **修改页面显示**（第 292-293 行附近）：
   ```html
   <!-- 将
   <span>检索模型：TF-IDF</span>
   <span>排序方式：余弦相似度</span>
   修改为
   <span>检索模型：BM25</span>
   <span>排序方式：BM25 评分</span> -->
   ```

3. **重新启动 Web 服务**：
   ```bash
   python scripts/web_app.py
   ```

**注意**：
- 语义检索由于需要加载 Sentence-BERT 模型（约 150MB），首次加载较慢，不建议集成到 Web 前端
- 如需使用语义检索，推荐通过命令行方式运行

## 注意事项

1. 语义检索首次运行需要下载预训练模型（约 150MB）
2. 建议在网络稳定的环境下运行语义检索
3. 数据文件已预先生成，直接运行检索即可，无需重新爬取

## 许可证

本项目仅供学习和研究使用，数据来源于 arXiv 开放获取平台。
