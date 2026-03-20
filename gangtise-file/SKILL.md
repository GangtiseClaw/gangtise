---
name: gangtise-file-api
description: Search the Gangtise file center for different types of documents (reports, announcements, summaries), returning file ids and key metadata/abstracts, plus helpers to download full files by type and id. Most types of documents has abstract in search result, so you can also get the main content of the documents directly (but in limited length). Use when you need to locate or filter specific documents rather than directly analyze their content. When the user asks specific search rule for certain document type, this skill can filter the documents based on more detailed rules.
---

# Search

## Overview

This skill queries the Gangtise file center for various types of documents, such as research reports, company announcements, and meeting summaries. It returns file ids together with key metadata and short abstracts, and provides methods to download the full file with its type and id. Note that most results are limited to 100 (maximum) due to API limitations. You are recommended to limit the number of results to 10 for most cases.

Use this skill when:
- You need to **locate, filter, or organize** documents by type, date, securities, or other metadata.
- You want to build a **candidate document list** (e.g. recent reports on a given stock, all announcements in a period).
- You plan to **download full files** and process them outside this skill (e.g. downstream parsing or separate reading).

Compared with other skills:
- Prefer **`gangtise-kb-api`** when you mainly care about the *text content itself* (for summarization, Q&A, extracting arguments), and do not need to browse long file lists.

（中文说明：`gangtise-file-api` 更像"文件目录/索引"，解决"有哪些文件、ID 是什么、按条件筛一批出来"的问题；真正看内容、抽段落建议用 `gangtise-kb-api`。）

## Instructions

各文档类型的**主脚本**用于执行检索并返回文件列表；部分参数提供**枚举值脚本**（如行业、机构等），调用前可先执行对应脚本获取可选值。**无枚举值接口的参数**（如关键词、证券、日期等）会由后端**智能匹配**，直接传入用户意图相关文本即可。证券代码需传入标准格式（如 `000001.SZ`）。

### 1. Search from reports

按关键词、证券、日期、机构、行业、来源类型、荣誉类型等条件检索研究报告。

示例（关键词"比亚迪"，限定时间范围与数量）：

```bash
python3 scripts/report.py -k 比亚迪 -sd 2024-01-01 -ed 2024-12-31 -l 20
```

行业、机构枚举值可通过 `scripts/get_industries.py`、`scripts/get_institutions.py` 获取。详见 [研究报告调用指导](./references/report.md)。

### 2. Search from company announcements

按证券、关键词、日期等条件检索公司公告。

示例（证券 + 关键词 + 时间）：

```bash
python3 scripts/announcement.py --securities 000858.SZ -k 业绩 -sd 2024-01-01 -ed 2024-12-31
```

详见 [公司公告调用指导](./references/announcement.md)。

### 3. Search from summaries

按关键词、证券、机构、行业、来源类型、栏目等条件检索会议纪要。

示例（关键词 + 栏目）：

```bash
python3 scripts/summary.py -k 锂电 --columns 业绩会 -l 20
```

行业、机构枚举值可通过 `scripts/get_industries.py`、`scripts/get_institutions.py` 获取。详见 [会议纪要调用指导](./references/summary.md)。

### 4. Get enum values

获取行业、机构的枚举值列表，用于为上述检索脚本提供参数可选值。

```bash
python3 scripts/get_industries.py
python3 scripts/get_institutions.py
```

### 5. Download file

根据文件 ID 与文件类型下载完整文件至本地。

示例（下载文件）：

```bash
python3 scripts/get_file.py --file-id 1234567890 --file-type "研究报告"
```

详见 [文件下载调用指导](./references/get_file.md)。
