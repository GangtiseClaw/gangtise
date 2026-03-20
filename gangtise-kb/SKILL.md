---
name: gangtise-kb-api
description: Semantic search over Gangtise internal knowledge base (reports, opinions, meetings, etc.), returning high-relevance content chunks. Prefer this over gangtise-file when you need to read or reason about the actual document content and not care about locating files. When you roughly know the topic and just need the most relevant text segments, this skill is better. This skill search files without any filter. So if you want to filter the documents based on more detailed rules, you can use gangtise-file-api.
---

# Knowledge Base Search

## Overview

This skill performs deep semantic search on the Gangtise internal knowledge base and returns high‑relevance content chunks directly, with optional methods to download the full file by type and id. It is more efficient than `gangtise-file-api` when you mainly care about *what the document says* (arguments, conclusions, paragraphs) instead of only locating files.

Use this skill when:
- You need to read, quote, or summarize the *content* of internal documents (e.g. research reports, internal reports, meeting minutes, chief views, etc.).
- You want to quickly retrieve key paragraphs to support reasoning, drafting, or Q&A.
- You already roughly know the topic and just need the most relevant text segments.

Compared with other skills:
- Use **`gangtise-file-api`** if you mainly want to locate/filter documents by type, date, securities, etc., and then decide which ones to download or process further.

（中文说明：`gangtise-kb-api` 适合做“看内容”的检索，比如找观点、结论、段落；如果只是想先把某类文件筛出来看列表，用 `gangtise-file-api` 更合适。）

## 知识库调用指南

### 脚本

`scripts/kb.py`

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-q` / `--query` | 是 | 检索查询语句。 |
| `-sd` / `--start-date` | 否 | 开始日期，如 `2024-01-01`。 |
| `-ed` / `--end-date` | 否 | 结束日期，如 `2024-12-31`。 |
| `-l` / `--limit` | 否 | 返回结果数量上限。 |
| `-o` / `--output` | 否 | 搜索结果保存路径；若不指定，则默认保存在gangtise工作目录下的 `kb/kb_x.md`（自动编号）；仅当环境变量GTS_SAVE_FILE为True时生效；一般不建议使用，由后端统一管理。|
| `--file-types` | 否 | 文件类型，逗号分隔。可选：研究报告,外资研报,内部报告,AI云盘,首席观点,公司公告,产业公众号,会议纪要,调研纪要,网络纪要。 |

会议纪要,调研纪要,网络纪要的区别是：会议纪要是来自Gangtise会议平台，调研纪要来自公司调研公告，网络纪要来自网络资源搜集。

### 示例
示例 1（按关键词检索新能源汽车相关文件）：

```bash
python3 scripts/kb.py -q "新能源汽车销量与政策"
```

示例 2（限制结果数量为 10, 查询比亚迪相关的外资研报）：
```bash
python3 scripts/kb.py -q "新能源汽车销量与政策" -l 10 --file-types "外资研报"
```