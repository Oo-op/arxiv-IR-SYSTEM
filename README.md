# 信息检索课程项目说明

本目录为课程信息检索作业的完整实现，包含：

- A 部分：数据采集、文本预处理、词表构建、倒排索引构建
- B 部分：TF-IDF 权重计算、向量空间检索、余弦相似度排序、命令行查询、人工评价

## 1. 项目目标

A 部分主要完成以下工作：

1. 确定数据源和主题
2. 编写网络爬虫，获取不少于 100 篇文档
3. 将文档保存到本地
4. 对文本进行清洗和预处理
5. 构建词项词典
6. 构建倒排索引
7. 编写基础说明文档，方便后续成员继续开发

本项目选择的语料为：

- 数据源：arXiv
- 主题：`cs.AI`
- 文档单位：单篇论文
- 文本内容：论文标题 + 摘要

## 2. arXiv 论文摘要简介

### 2.1 arXiv 是什么

arXiv 是一个国际上广泛使用的开放学术论文预印本平台，主要收录计算机、数学、物理、统计等领域的研究论文。研究人员会在正式发表前或发表过程中，将论文上传到 arXiv，供其他研究者浏览、检索和下载。

对于信息检索课程作业来说，arXiv 有几个明显优势：

- 数据公开，便于获取
- 文档数量充足，容易达到 100 篇以上
- 每篇论文都带有稳定的标题、摘要、作者、链接、日期等字段
- 文本内容规范，适合构建词表、倒排索引和 TF-IDF 检索模型

### 2.2 什么是“论文摘要”

论文摘要是对整篇论文核心内容的简要概括，通常包含：

- 研究问题
- 方法或模型
- 实验设置
- 主要结果
- 结论或贡献

摘要虽然比全文短，但已经能较好地反映论文主题，因此非常适合作为课程项目中的“文档正文”来构建检索系统。与直接抓取整篇 PDF 相比，摘要还有这些优点：

- 文本更规整，清洗难度更低
- 字段提取更稳定
- 抓取和本地存储成本更小
- 更容易做关键词匹配和相关度排序

### 2.3 本项目为什么选择 arXiv 论文摘要

本项目最终选择 `arXiv + cs.AI`，主要基于以下考虑：

1. `cs.AI` 属于人工智能方向，主题集中，适合做专题检索
2. 摘要文本长度适中，便于后续进行分词、词频统计和向量表示
3. 数据字段标准化程度高，适合小组协作开发
4. 后续 B 部分实现查询、排序、结果展示时，标题和摘要已经足够支撑一个完整的检索系统演示

### 2.4 当前项目中抓取了哪些信息

在本项目中，每篇 arXiv 论文记录至少包含以下内容：

- `title`：论文标题
- `abstract`：论文摘要
- `url`：论文页面链接
- `published`：提交日期
- `authors`：作者列表
- `categories`：所属分类

这些字段已经足够支持：

- 文档展示
- 文本预处理
- 倒排索引构建
- TF-IDF 权重计算
- 检索结果排序与输出

## 3. 当前完成情况

已经完成并生成以下成果：

- 抓取 `120` 篇 arXiv 论文摘要文档
- 保存原始文档数据 `documents.json`
- 保存清洗后的文档数据 `cleaned_documents.json`
- 构建词表 `vocab.json`
- 构建倒排索引 `inverted_index.json`
- 实现 TF-IDF 检索核心模块
- 实现命令行查询系统
- 实现人工评价模板与 Precision@5 / Precision@10 统计脚本
- 生成运行摘要 `pipeline_summary.json`
- 编写 A 部分说明文档 `docs/A_report.md`
- 编写 B 部分说明文档 `docs/B_report.md`

当前统计信息：

- 文档数：`120`
- 词项数：`5302`
- 平均文档长度：`197.24`

## 4. 目录结构

```text
Information/
├── README.md
├── docs/
│   └── A_report.md
├── data/
│   ├── raw/
│   │   └── documents.json
│   ├── processed/
│   │   └── cleaned_documents.json
│   └── index/
│       ├── vocab.json
│       └── inverted_index.json
├── scripts/
│   ├── fetch_arxiv.py
│   ├── preprocess.py
│   ├── build_index.py
│   └── run_pipeline.py
│   ├── ir_core.py
│   ├── search_cli.py
│   └── evaluate_ir.py
└── output/
    ├── pipeline_summary.json
    ├── evaluation_template.csv
    └── evaluation_summary.json
```

## 5. 主要文件说明

### `data/raw/documents.json`

原始抓取结果，包含每篇论文的基础信息：

- `doc_id`：本地文档编号
- `arxiv_id`：arXiv 论文编号
- `title`：标题
- `abstract`：摘要
- `url`：论文页面链接
- `published`：提交日期
- `updated`：当前与提交日期保持一致
- `authors`：作者列表
- `categories`：分类列表
- `source`：数据源标识
- `topic`：主题分类

### `data/processed/cleaned_documents.json`

在原始字段基础上增加了预处理结果：

- `clean_title`：清洗后的标题
- `clean_abstract`：清洗后的摘要
- `tokens`：分词结果
- `token_count`：词数

预处理规则：

- 去除 HTML 标签
- 处理 HTML 转义字符
- 合并多余空白
- 转为小写后分词
- 英文按正则规则提取单词和数字

### `data/index/vocab.json`

词项词典文件。每个词项包含：

- `term_id`
- `term`
- `document_frequency`
- `collection_frequency`

含义：

- `document_frequency`：包含该词的文档数
- `collection_frequency`：该词在整个语料中出现的总次数

### `data/index/inverted_index.json`

倒排索引文件。结构如下：

- 最外层 `index`
- 每个 `term` 对应一个 posting list
- posting list 中每项包含：
  - `doc_id`
  - `tf`
  - `positions`

含义：

- `doc_id`：该词出现在哪篇文档中
- `tf`：该词在该文档中的词频
- `positions`：该词在该文档 token 序列中的位置列表

### `output/pipeline_summary.json`

记录本次数据处理的统计摘要，例如：

- 文档数
- 词项数
- 平均文档长度
- 关键文件路径

### `output/evaluation_template.csv`

人工评价模板文件，用于填写每个查询结果是否相关。

### `output/evaluation_summary.json`

人工评价统计结果文件，用于保存 `Precision@5` 和 `Precision@10`。

## 6. 脚本说明

### `scripts/fetch_arxiv.py`

作用：

- 从 arXiv 页面抓取论文标题、摘要、作者、日期和链接
- 支持按 `max-results` 控制抓取篇数

### `scripts/preprocess.py`

作用：

- 对原始文本进行清洗
- 生成分词结果
- 输出清洗后的文档文件

### `scripts/build_index.py`

作用：

- 从清洗后的文档构建词表
- 构建倒排索引
- 输出统计摘要

### `scripts/run_pipeline.py`

作用：

- 串联执行抓取、清洗、建索引三个步骤

### `scripts/ir_core.py`

作用：

- 加载文档、词表和倒排索引
- 计算 `idf`
- 计算文档向量模长
- 实现查询向量构建和余弦相似度排序

### `scripts/search_cli.py`

作用：

- 提供命令行检索入口
- 支持单次查询和交互式查询
- 输出相关度、标题、摘要片段、URL、日期和匹配词

### `scripts/evaluate_ir.py`

作用：

- 生成人工评价模板
- 统计 `Precision@5` 和 `Precision@10`

### `scripts/web_app.py`

作用：

- 提供一个简单的本地 Web 查询界面
- 支持在浏览器中输入查询词并展示排序结果
- 提供 `/api/search` 接口返回 JSON 结果

运行方式：

```bash
cd /Users/yumo.li/HMWK/Information
python3 scripts/run_pipeline.py --category cs.AI --max-results 120
```

## 7. 给组员 B 的详细交接说明

如果需要继续优化或扩展系统，可以在现有 B 部分实现基础上继续开发；如果只是完成课程要求，则当前代码已经具备最小可运行检索系统。

B 部分的目标是在当前 A 部分产物上完成“可查询的检索系统”。为了避免重复劳动，建议直接以 `cleaned_documents.json`、`vocab.json`、`inverted_index.json` 为输入。

### 6.1 推荐优先使用的输入文件

后续最建议直接读取这三个文件：

- [cleaned_documents.json](/Users/yumo.li/HMWK/Information/data/processed/cleaned_documents.json)
- [vocab.json](/Users/yumo.li/HMWK/Information/data/index/vocab.json)
- [inverted_index.json](/Users/yumo.li/HMWK/Information/data/index/inverted_index.json)

其中：

- `cleaned_documents.json` 适合用来做文档展示、摘要截取、标题/URL/日期输出
- `vocab.json` 适合用来计算 `idf`
- `inverted_index.json` 适合用来快速定位包含查询词的候选文档，并读取词频

### 6.2 B 部分建议实现流程

建议按下面顺序继续实现：

1. 读取 `cleaned_documents.json`
2. 读取 `vocab.json`
3. 读取 `inverted_index.json`
4. 实现查询预处理
5. 计算查询词的 TF-IDF
6. 计算文档向量或按倒排表累计得分
7. 使用余弦相似度排序
8. 输出检索结果

### 6.3 查询预处理建议

查询输入为自然语言字符串时，建议和 A 部分保持一致的预处理逻辑，否则会出现词项不一致的问题。

建议步骤：

1. 转小写
2. 去除多余空白
3. 按和文档相同的正则规则分词

也就是说，B 部分最好复用 `preprocess.py` 中的分词规则，至少保持同样的 token 形式。

### 6.4 TF-IDF 计算建议

可以采用最基础的向量空间模型：

- `tf(t, d)`：词 `t` 在文档 `d` 中出现次数
- `idf(t) = log(N / df(t))`
- `w(t, d) = tf(t, d) * idf(t)`

其中：

- `N` 为文档总数，可从 `vocab.json` 或 `inverted_index.json` 顶层读取
- `df(t)` 可从 `vocab.json` 中读取 `document_frequency`

查询向量也使用相同方式构建：

- 先统计查询词频
- 再乘对应 `idf`

### 6.5 排序实现建议

两种实现都可以：

1. 先为每篇文档构建完整向量，再与查询向量做余弦相似度
2. 利用倒排索引只遍历命中词项的候选文档，再累计分数

如果想实现更快、更省空间的版本，推荐第 2 种。

推荐做法：

1. 对查询分词
2. 对每个查询词查倒排表
3. 找到出现该词的所有文档
4. 按 `tf-idf` 累加每个候选文档的分子部分
5. 再除以查询向量和文档向量模长，得到余弦相似度

### 6.6 文档展示建议

作业要求输出：

- 相关度
- 题目
- 主要匹配内容
- URL
- 日期

这些字段建议这样取：

- 相关度：余弦相似度
- 题目：`title`
- 主要匹配内容：可从 `clean_abstract` 中截取前 150 到 250 个字符，或优先截取包含查询词的句子
- URL：`url`
- 日期：`published`

### 6.7 数据结构使用建议

#### 文档映射

B 部分建议先把文档列表转成字典：

```python
doc_map = {doc["doc_id"]: doc for doc in documents}
```

这样查 `doc_id` 时可以快速拿到：

- 标题
- 摘要
- URL
- 日期

#### 词项映射

建议把 `vocab.json` 转成：

```python
term_stats = {
    item["term"]: {
        "df": item["document_frequency"],
        "cf": item["collection_frequency"],
        "term_id": item["term_id"],
    }
    for item in vocab["terms"]
}
```

这样查 `idf` 会比较方便。

### 6.8 可能直接复用的字段

B 部分通常只需要重点使用这些字段：

- 文档侧：
  - `doc_id`
  - `title`
  - `clean_abstract`
  - `published`
  - `url`
  - `tokens`
  - `token_count`

- 索引侧：
  - `term`
  - `document_frequency`
  - `tf`
  - `positions`

### 6.9 推荐的最小可运行检索系统

如果时间紧，建议 B 部分至少完成一个命令行版本：

1. 用户输入查询字符串
2. 系统分词
3. 基于倒排索引找到候选文档
4. 计算 TF-IDF + 余弦相似度
5. 输出 Top 10

输出示例字段建议：

- `rank`
- `score`
- `title`
- `snippet`
- `url`
- `published`

### 6.10 人工评价建议

如果后续要补 `Precision@5` 或 `Precision@10`，建议：

1. 选 5 到 10 个查询词
2. 每个查询看前 5 或前 10 个结果
3. 人工标注“相关 / 不相关”
4. 统计平均准确率

例如查询可以选：

- `agent`
- `reasoning`
- `alignment`
- `retrieval`
- `multi-agent`

## 8. 当前项目运行方式

### 8.1 重新生成数据与索引

```bash
cd /Users/yumo.li/HMWK/Information
python3 scripts/run_pipeline.py --category cs.AI --max-results 120
```

### 8.2 执行查询

```bash
python3 scripts/search_cli.py --query "multi-agent reasoning" --top-k 5
```

交互式：

```bash
python3 scripts/search_cli.py --interactive
```

### 8.3 启动 Web 页面

```bash
python3 scripts/web_app.py --host 127.0.0.1 --port 8000
```

浏览器访问：

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/api/search?q=reasoning&top_k=5`

### 8.4 生成人工评价模板

```bash
python3 scripts/evaluate_ir.py --mode generate --top-k 10
```

### 8.5 统计评价结果

先在 `output/evaluation_template.csv` 中手动填写 `relevant` 列，再运行：

```bash
python3 scripts/evaluate_ir.py --mode score
```

## 9. 当前交接状态

当前 A 部分已经可以直接交给 B 开发，B 不需要再做：

- 爬虫
- 文本清洗
- 基础分词
- 词表构建
- 倒排索引构建

B 部分现在也已经实现完成，后续如果继续分工，建议直接在以下方向上扩展：

- Web 界面
- 停用词处理
- BM25 对比实验
- 更细致的人工评价和结果分析

## 10. 说明

- 本项目目前只使用 Python 标准库
- 当前实现面向课程作业，重点是结构清晰、便于继续开发
- 如需重新抓取不同主题，可以修改 `--category` 参数，例如：

```bash
python3 scripts/run_pipeline.py --category cs.CL --max-results 120
python3 scripts/run_pipeline.py --category cs.IR --max-results 120
```
