import os
import sys
from typing import List, Optional
import datetime
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from utils import (  # noqa: E402
    GTS_AUTHORIZATION,
    SUMMARY_URL,
    FILE_DEFAULT_LIMIT,
    INDUSTRIES_MAP,
    INSTITUTIONS_MAP,
    format_response,
    match_best,
    remove_html_tags,
    check_version,
)

SUMMARY_SOURCE_MAP = {
    "会议平台": 100100178,
    "网络资源": 100100262,
    "公司公告": 100100263,
}

SUMMARY_COLUMN_MAP = {
    "A股": 98,
    "港股": 99,
    "美股中概": 100,
    "美股": 101,
    "高管": 103,
    "专家": 104,
    "业绩会": 106,
    "策略会": 107,
    "公司分析": 108,
    "行业分析": 109,
    "基金路演": 110,
}


def _format_time_range(start_date: str = None, end_date: str = None):
    start_timestamp = None
    end_timestamp = None
    if start_date:
        start_timestamp = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    if end_date:
        end_timestamp = int(
            (datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)).timestamp() * 1000
        ) - 1
    return start_timestamp, end_timestamp


def _format_summary_item(summaries: List[dict]) -> List[dict]:
    _results = []
    for summary in summaries:
        summ_time = summary.get("summTime") or summary.get("msgTime")
        file_time = ""
        if summ_time:
            file_time = datetime.datetime.fromtimestamp(summ_time / 1000).strftime("%Y-%m-%d %H:%M:%S")

        stocks = summary.get("stock") or []
        stock_display = ", ".join(
            f"{s.get('scrAbbr', '')}({s.get('gtsCode', '')})" for s in stocks if s.get("gtsCode")
        )

        initiators = summary.get("initiator") or []
        initiator_display = ", ".join(
            i.get("cnName") or i.get("partyName", "") for i in initiators
        )

        essences = summary.get("essence") or []
        sentiment_map = {
            1: "正面",
            "1": "正面",
            0: "中性",
            "0": "中性",
            -1: "负面",
            "-1": "负面",
        }
        
        essence_display = "; ".join(
            "(" + sentiment_map[e.get("sentiment")] + ")" + e.get("brief", "") + ": " + e.get("content", "") for e in sorted(essences, key=lambda x: x.get("sort", 0))
        ) if essences else ""

        item = {
            "标题": remove_html_tags(summary.get("title", "")),
            "文件时间": file_time,
            "来源": summary.get("sourceName", ""),
            "分类": summary.get("category", ""),
            "发起方": initiator_display,
            "嘉宾": summary.get("guest", "") or "",
            "摘要": remove_html_tags(summary.get("brief", "")+"..." or ""),
            "关联股票": stock_display,
            "纪要精华": essence_display,
            "类型": "会议纪要",
            "类型中ID": str(summary.get("id", "")),
        }
        _results.append(item)
    return _results


def _resolve_industries(industries: List[str]) -> List[str]:
    if not industries:
        return []
    all_industries = {}
    for key, value in INDUSTRIES_MAP.items():
        all_industries.update(value.copy())
    results = []
    for industry in industries:
        result = match_best(industry, all_industries.keys())
        if result and result not in results:
            results.append(str(all_industries[result]))
    return results


def _resolve_institutions(institutions: List[str]) -> List[str]:
    if not institutions:
        return []
    results = []
    for institution in institutions:
        result = match_best(institution, INSTITUTIONS_MAP.keys())
        if result and result not in results:
            results.append(str(INSTITUTIONS_MAP[result]))
    return results


def _resolve_sources(source_types: List[str]) -> List[int]:
    if not source_types:
        return []
    return [SUMMARY_SOURCE_MAP[name] for name in source_types if name in SUMMARY_SOURCE_MAP]


def _resolve_columns(columns: List[str]) -> List[int]:
    if not columns:
        return []
    return [SUMMARY_COLUMN_MAP[name] for name in columns if name in SUMMARY_COLUMN_MAP]


def _clean_keyword(keyword: str, securities=None, source_types=None, institutions=None, industries=None, columns=None) -> str:
    if not keyword:
        return ""
    keyword = (
        keyword.replace("[", "").replace("]", "")
        .replace("、", " ").replace("，", " ")
        .replace(", ", " ").replace(",", " ")
    )
    keyword = (
        keyword.replace("的纪要", "").replace("的会议纪要", "")
        .replace("的调研纪要", "").replace("纪要", "")
        .replace("会议纪要", "").replace("调研纪要", "")
    )
    for items in [securities, source_types, institutions, industries, columns]:
        if items:
            for item in items:
                keyword = keyword.replace(item, "")
    return keyword.strip()


def _fetch_summaries(headers, payload_base, keyword, search_type, limit):
    max_page_size = 50
    all_results = []
    offset = 0
    remaining = limit

    while remaining > 0:
        page_size = min(remaining, max_page_size)
        data = {**payload_base, "from": offset, "size": page_size}
        if keyword:
            data["kw"] = keyword
            data["searchType"] = search_type

        response = requests.post(SUMMARY_URL, headers=headers, json=data)
        if response.status_code != 200:
            return None, response.text
        result = response.json()

        if result.get("code") not in [200, "000000"] and result.get("status") is not True:
            return None, result.get("msg", "请求失败")

        summary_data = result.get("data", {})
        summaries = summary_data.get("summList", [])
        if not summaries:
            break

        all_results.extend(_format_summary_item(summaries))

        if len(summaries) < page_size:
            break

        offset += page_size
        remaining -= len(summaries)

    return all_results, None


def summary_finder(
    keyword: str = "",
    securities: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    institutions: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    source_types: Optional[List[str]] = None,
    columns: Optional[List[str]] = None,
    limit: int = FILE_DEFAULT_LIMIT["summary"],
):
    try:
        try:
            if not check_version():
                update_sh = os.path.join(script_dir, "update.sh")
                print(f"[WARNING] 存在 Gangtise skills 版本更新，可以执行 {update_sh} 更新，请与用户确认是否更新\n")
        except Exception as e:
            print(f"[WARNING] 检查 Gangtise skills 版本失败\n")
        headers = {
            "Authorization": GTS_AUTHORIZATION,
        }

        industry_ids = _resolve_industries(industries) if industries else []
        broker_ids = _resolve_institutions(institutions) if institutions else []
        source_ids = _resolve_sources(source_types) if source_types else []
        column_ids = _resolve_columns(columns) if columns else []

        if securities:
            securities = [security.upper() for security in securities]

        if securities and industries:
            industry_ids = []

        start_timestamp, end_timestamp = _format_time_range(start_date, end_date)

        keyword_str = _clean_keyword(keyword, securities, source_types, institutions, industries, columns)

        payload_base = {}
        if start_timestamp:
            payload_base["startTime"] = start_timestamp
        if end_timestamp:
            payload_base["endTime"] = end_timestamp
        if source_ids:
            payload_base["sourceList"] = source_ids
        if securities:
            payload_base["stockList"] = securities
        if industry_ids:
            payload_base["industryList"] = industry_ids
        if broker_ids:
            payload_base["brokerList"] = broker_ids
        if column_ids:
            payload_base["columnIdList"] = column_ids

        all_results, err = _fetch_summaries(headers, payload_base, keyword_str, 1, limit)
        if err:
            return format_response({"state": "error", "message": err}, "summary")

        if not all_results and keyword_str:
            all_results, err = _fetch_summaries(headers, payload_base, keyword_str, 2, limit)
            if err:
                return format_response({"state": "error", "message": err}, "summary")

        if not all_results:
            return format_response(
                {"state": "error", "message": "未找到相关纪要，建议修改查询条件", "data": []},
                "summary",
            )

        all_results = all_results[:limit]

        response_data = {
            "state": "success",
            "message": "已找到相关纪要",
            "data": [{"data": all_results, "module": "summary", "type": "files"}],
        }
        return format_response(response_data, "summary")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return format_response(
            {"state": "error", "message": str(e), "data": [], "usage": {}},
            "summary",
        )


def _parse_str_list(raw: str) -> Optional[List[str]]:
    if not raw:
        return None
    items = [
        x.strip()
        for x in raw.replace("，", ",").split(",")
        if x.strip()
    ]
    return items or None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="纪要检索命令行：根据关键词、证券、行业、机构等条件查找会议纪要。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-k", "--keyword", default="", help="检索查询关键词，可为空")
    parser.add_argument("-sd", "--start_date", default="", help="开始日期，格式YYYY-MM-DD")
    parser.add_argument("-ed", "--end_date", default="", help="结束日期，格式YYYY-MM-DD")
    parser.add_argument(
        "-l",
        "--limit",
        default=FILE_DEFAULT_LIMIT["summary"],
        type=int,
        help="返回文件数量上限",
    )
    parser.add_argument(
        "--securities",
        default="",
        help="证券代码列表，逗号分隔，必须为标准证券代码，如 000001.SZ",
    )
    parser.add_argument(
        "--institutions",
        default="",
        help="机构列表，逗号分隔",
    )
    parser.add_argument(
        "--industries",
        default="",
        help="行业列表，逗号分隔",
    )
    parser.add_argument(
        "--source_types",
        default="",
        help="来源类型列表，逗号分隔（会议平台/网络资源/公司公告）",
    )
    parser.add_argument(
        "--columns",
        default="",
        help="栏目列表，逗号分隔（A股/港股/美股中概/美股/高管/专家/业绩会/策略会/公司分析/行业分析/基金路演）",
    )

    args = parser.parse_args()

    keyword = args.keyword or ""
    securities = _parse_str_list(args.securities)
    institutions = _parse_str_list(args.institutions)
    industries = _parse_str_list(args.industries)
    source_types = _parse_str_list(args.source_types)
    columns = _parse_str_list(args.columns)
    start_date = args.start_date or None
    end_date = args.end_date or None
    limit = int(args.limit)

    out = summary_finder(
        keyword=keyword,
        securities=securities,
        start_date=start_date,
        end_date=end_date,
        institutions=institutions,
        industries=industries,
        source_types=source_types,
        columns=columns,
        limit=limit,
    )
    print(out)


if __name__ == "__main__":
    main()
