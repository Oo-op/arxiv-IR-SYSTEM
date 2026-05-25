# B 部分检索系统实现说明

## 1. 实现目标

B 部分在 A 部分已生成的数据和倒排索引基础上，实现一个可运行的信息检索系统，支持：

1. 读取本地文档和倒排索引
2. 对用户查询进行预处理
3. 计算 TF-IDF 权重
4. 基于向量空间模型进行匹配
5. 按余弦相似度输出排序结果
6. 提供命令行查询入口
7. 提供简单 Web 查询界面
8. 提供人工评价模板与 Precision@5 / Precision@10 统计脚本

## 2. 使用的数据输入

系统直接读取以下 A 部分产物：

- `data/processed/cleaned_documents.json`
- `data/index/vocab.json`
- `data/index/inverted_index.json`

其中：

- `cleaned_documents.json` 用于展示标题、摘要、URL、日期
- `vocab.json` 用于读取 `df` 并计算 `idf`
- `inverted_index.json` 用于快速定位候选文档和读取词频 `tf`

## 3. 查询处理流程

用户输入自然语言查询后，系统执行以下步骤：

1. 去除 HTML 标签和多余空白
2. 转换为小写
3. 使用与文档相同的正则规则分词
4. 只保留出现在词表中的词项
5. 构建查询向量

这样可以保证查询侧和文档侧采用一致的分词规则，避免因为 token 形式不一致而漏检。

## 4. TF-IDF 权重计算

本系统采用基础 TF-IDF 模型：

- `tf(t, d)`：词项 `t` 在文档 `d` 中出现的次数
- `idf(t) = log(N / df(t)) + 1`
- `w(t, d) = tf(t, d) * idf(t)`

其中：

- `N` 是语料总文档数
- `df(t)` 来自词表中的 `document_frequency`

查询向量也使用同样方式构建：

- 先统计查询词频
- 再乘对应的 `idf`

## 5. 向量空间匹配与排序

系统使用余弦相似度计算查询向量与文档向量之间的相关度：

`cos(q, d) = (q · d) / (||q|| * ||d||)`

实现上没有为每篇文档显式存完整稠密向量，而是使用倒排索引进行稀疏计算：

1. 遍历查询词
2. 根据倒排表找到命中文档
3. 累计点积分子
4. 使用预先计算的文档向量模长完成归一化
5. 得到每个候选文档的最终分数

这种实现更贴合实际搜索系统，也更节省空间。

## 6. 检索结果输出

命令行检索结果包括：

- `rank`
- `score`
- `title`
- `snippet`
- `url`
- `published`
- `matched_terms`

其中 `snippet` 优先从摘要中选取包含查询词的句子；如果没有明显匹配句，则截取摘要前部作为展示片段。

## 7. 可运行脚本

### 7.1 命令行检索

脚本：

- `scripts/search_cli.py`

示例：

```bash
cd /Users/yumo.li/HMWK/Information
python3 scripts/search_cli.py --query "multi-agent reasoning" --top-k 5
```

交互式模式：

```bash
python3 scripts/search_cli.py --interactive
```

JSON 输出：

```bash
python3 scripts/search_cli.py --query "retrieval" --top-k 10 --json
```

### 7.2 人工评价

### 7.2 Web 页面

脚本：

- `scripts/web_app.py`

启动方式：

```bash
cd /Users/yumo.li/HMWK/Information
python3 scripts/web_app.py --host 127.0.0.1 --port 8000
```

浏览器访问：

- `http://127.0.0.1:8000`

页面支持：

- 输入查询字符串
- 选择 Top K
- 展示相关度、标题、摘要片段、URL、日期和匹配词

同时提供 JSON 接口：

- `http://127.0.0.1:8000/api/search?q=reasoning&top_k=5`

### 7.3 人工评价

脚本：

- `scripts/evaluate_ir.py`

先生成评价模板：

```bash
python3 scripts/evaluate_ir.py --mode generate --top-k 10
```

生成文件：

- `output/evaluation_template.csv`

人工阅读后，在 `relevant` 列中填写：

- `1`：相关
- `0`：不相关

再计算 Precision@5 和 Precision@10：

```bash
python3 scripts/evaluate_ir.py --mode score
```

输出文件：

- `output/evaluation_summary.json`

## 8. 建议的实验展示方式

可以选取若干查询词进行演示，例如：

- `agent`
- `reasoning`
- `alignment`
- `retrieval`
- `multi-agent`

展示时可以截图以下内容：

1. 命令行输入查询
2. Top 5 或 Top 10 检索结果
3. 人工评价表
4. Precision@5 / Precision@10 统计结果

## 9. 当前状态

B 部分已经具备一个最小可运行版本：

- 可加载索引
- 可处理查询
- 可计算 TF-IDF
- 可按余弦相似度排序
- 可输出检索结果
- 可生成人工评价模板

如果后续还有时间，可以继续扩展：

- 简单 Web 界面
- 更好的摘要高亮
- 停用词处理
- 短语检索
- 布尔检索或 BM25 对比
