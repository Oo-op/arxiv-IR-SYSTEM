# A 部分基础说明文档

## 1. 数据源与主题

- 数据源：arXiv 公共 API
- 主题：默认选择 `cs.AI`
- 文档类型：论文元数据 + 摘要
- 原因：
  - 数据字段结构稳定
  - 可稳定获取 100 篇以上文档
  - 自带标题、摘要、URL、发布日期
  - 英文文本适合直接按空格/词边界切分

## 2. 本地数据结构

### 原始文档 `documents.json`

每篇文档包含以下主要字段：

- `doc_id`: 本地文档编号
- `arxiv_id`: arXiv 编号
- `title`: 标题
- `abstract`: 摘要原文
- `url`: 论文链接
- `published`: 发布时间
- `updated`: 更新时间
- `authors`: 作者列表
- `categories`: 主题分类

### 清洗后文档 `cleaned_documents.json`

在原始字段基础上增加：

- `clean_title`
- `clean_abstract`
- `tokens`
- `token_count`

## 3. 预处理方式

- 去除多余空白符
- 统一小写
- 英文按正则提取单词和数字
- 保留每个词在文档中的位置，便于构建倒排索引

## 4. 词项词典 `vocab.json`

每个词项记录：

- `term`
- `term_id`
- `document_frequency`
- `collection_frequency`

## 5. 倒排索引 `inverted_index.json`

每个词项映射到一个 posting list，posting 中包含：

- `doc_id`
- `tf`
- `positions`

这可以直接支持后续 B 部分的：

- TF 计算
- IDF 计算
- 向量空间模型
- 查询词匹配

## 6. 交接说明

交付给 B 的核心文件：

- `data/raw/documents.json`
- `data/processed/cleaned_documents.json`
- `data/index/vocab.json`
- `data/index/inverted_index.json`

后续 B 可以在此基础上继续完成：

- 查询预处理
- TF-IDF 权重计算
- 余弦相似度排序
- 检索结果展示
- Precision@5 / Precision@10 人工评估
