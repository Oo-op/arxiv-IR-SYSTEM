# arXiv 论文摘要信息抽取实验系统

本项目用于课程“信息与知识获取”的信息抽取实验。系统基于本地 arXiv `cs.AI` 论文摘要语料，使用规则匹配、领域词典和 TF-IDF 统计方法抽取论文中的结构化信息，并提供结果导出、人工评估和本地 Web 交互页面。

当前数据集位于 `data/documents.json`，共包含 120 篇 arXiv `cs.AI` 论文摘要，满足实验要求中“不少于 100 篇文档”的规模要求。

## 功能概览

- 对本地 arXiv 论文标题和摘要进行信息抽取。
- 抽取论文编号、发表年份、作者数、研究任务、方法/模型、数据集/基准、评价指标、应用领域、可持续发展/社会影响、系统名称等信息点。
- 使用正则表达式和领域词典作为主要抽取方法，保留课程要求的可解释规则抽取流程。
- 使用 TF-IDF 抽取每篇论文的区分性关键词，补充规则词典覆盖不足的问题。
- 生成 JSON、CSV、HTML 三类结果文件，便于分析和展示。
- 提供人工评估模板生成与准确率统计脚本。
- 提供本地 Web 页面，支持选择语料中的论文抽取，也支持输入自定义标题和摘要即时抽取。
- 可选接入 DashScope OpenAI 兼容接口，使用 `glm-5` 进行大模型增强抽取。

## 项目结构

```text
ie_homework/
  data/
    documents.json                  # 本地 arXiv cs.AI 论文摘要语料，120 篇
  output/
    extraction_results.json         # 规则/TF-IDF 抽取结果
    extraction_results.csv          # 表格格式抽取结果
    summary.json                    # 统计摘要
    results.html                    # 抽取结果展示页面
    manual_evaluation_template.csv  # 人工评估模板
    manual_evaluation_summary.json  # 人工评估统计结果
    llm_extraction_samples.json     # 大模型增强抽取样例
  scripts/
    extract_ie.py                   # 规则和 TF-IDF 信息抽取主程序
    evaluate_ie.py                  # 人工评估模板生成与评分
    llm_extractor.py                # 可选的大模型增强抽取
    web_app.py                      # 本地交互式 Web 页面
  requirements.txt                  # Python 依赖说明
  实验3报告.docx                    # 实验报告
```

## 环境准备

推荐使用 Python 3.10 或以上版本。

基础的规则抽取、TF-IDF 抽取、结果导出和 Web 页面只依赖 Python 标准库。若需要使用 `llm_extractor.py` 或 Web 页面中的大模型增强抽取，建议安装 `requirements.txt` 中的可选依赖：

```bash
pip install -r requirements.txt
```

如需使用 DashScope 大模型接口，需要设置环境变量：

```bash
set DASHSCOPE_API_KEY=你的 DashScope API Key
```

PowerShell 中可使用：

```powershell
$env:DASHSCOPE_API_KEY="你的 DashScope API Key"
```

## 运行信息抽取

在项目根目录执行：

```bash
python scripts/extract_ie.py
```

默认读取 `data/documents.json`，并将结果写入 `output/`：

- `output/extraction_results.json`：完整结构化抽取结果。
- `output/extraction_results.csv`：表格格式结果，适合用 Excel 或 WPS 打开。
- `output/summary.json`：文档数量、平均置信度、字段覆盖率和高频值统计。
- `output/results.html`：可直接用浏览器打开的结果展示页。

常用参数：

```bash
python scripts/extract_ie.py --limit 10
python scripts/extract_ie.py --input data/documents.json --output-dir output
```

## 运行本地 Web 页面

```bash
python scripts/web_app.py --host 127.0.0.1 --port 8010
```

然后在浏览器打开：

```text
http://127.0.0.1:8010
```

页面支持两种抽取方式：

- 从本地 120 篇论文中选择一篇，点击抽取。
- 输入自定义论文标题和摘要，进行即时抽取。

如果勾选“使用 glm-5 大模型增强抽取”，系统会在规则/TF-IDF 抽取之外调用 DashScope 接口，补充研究问题、主要贡献、关键结论、社会影响和证据片段等语义字段。该功能需要提前配置 `DASHSCOPE_API_KEY`。

## 大模型增强抽取

大模型增强是可选功能，不替代课程要求中的正则表达式和规则抽取。其作用是补充规则方法较难覆盖的语义信息。

命令行示例：

```bash
python scripts/llm_extractor.py --doc-id 1
python scripts/llm_extractor.py --limit 3
```

默认配置：

- API Key：读取环境变量 `DASHSCOPE_API_KEY`，Windows 下也会尝试读取用户环境变量。
- 模型：`glm-5`。
- 接口地址：`https://dashscope.aliyuncs.com/compatible-mode/v1`。
- 输出文件：`output/llm_extraction_samples.json`。

可选参数：

```bash
python scripts/llm_extractor.py --model glm-5 --limit 5
python scripts/llm_extractor.py --base-url https://dashscope.aliyuncs.com/compatible-mode/v1
python scripts/llm_extractor.py --output output/llm_extraction_samples.json
```

## 人工评估

先确保已经运行过主抽取脚本，生成 `output/extraction_results.json`。

生成前 30 篇论文的人工评估模板：

```bash
python scripts/evaluate_ie.py --mode generate --max-docs 30
```

打开 `output/manual_evaluation_template.csv`，在 `manual_correct` 列填写：

- `1`：该字段抽取结果正确。
- `0`：该字段抽取结果错误。

填写完成后计算准确率：

```bash
python scripts/evaluate_ie.py --mode score
```

评分结果会写入 `output/manual_evaluation_summary.json`，包括总体准确率和各字段准确率。

## 抽取字段说明

主程序 `scripts/extract_ie.py` 输出的每条记录包含：

- `doc_id`、`title`、`url`、`published`：论文基础信息。
- `extracted`：结构化抽取字段。
- `confidence`：根据多个字段是否抽取得到计算的启发式置信度。
- `evidence`：与抽取值相关的证据句。

`extracted` 中的主要字段包括：

- `arxiv_id`：论文 arXiv 编号。
- `publication_year`：发表年份。
- `authors`、`author_count`：作者列表和作者数量。
- `categories`：arXiv 分类。
- `research_tasks`：研究任务。
- `methods`：方法、模型或算法。
- `datasets`：数据集或基准。
- `metrics`：评价指标。
- `tfidf_keyphrases`：TF-IDF 关键词。
- `application_domains`：应用领域。
- `sustainability_points`：可持续发展、安全、隐私、公平性或社会影响相关信息。
- `system_names`：论文标题或摘要中出现的系统名称。

## 实验设计说明

系统面向人工智能论文摘要，围绕“论文研究什么、使用什么方法、在哪些数据集和指标上评价、涉及哪些应用和社会影响”进行信息点设计。正则表达式和词典匹配提供可解释的基础抽取能力，TF-IDF 用于补充主题关键词，大模型增强作为可选扩展用于抽取更偏语义化的内容。

如果只需要复现实验的基础结果，运行 `scripts/extract_ie.py` 即可；如果需要展示交互效果，运行 `scripts/web_app.py`；如果需要人工评估，使用 `scripts/evaluate_ie.py`。
