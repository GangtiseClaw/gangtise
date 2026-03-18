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
    REPORT_URL,
    FILE_DEFAULT_LIMIT,
    INDUSTRIES_MAP,
    INSTITUTIONS_MAP,
    format_response,
    match_best,
    remove_html_tags,
    check_version,
)

REPORT_SOURCE_MAP = {
    "研报": 0,
    "公众号": 1,
}

HONOR_TYPE_MAP = {
    "新财富": "125100001",
    "金牛": "125100002",
    "水晶球": "125100003",
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


def _format_report_item(reports: List[dict]) -> List[dict]:
    _results = []
    for report in reports:
        print(report)
        author_obj = report.get("author")
        if isinstance(author_obj, dict):
            author_display = author_obj.get("display", "")
        elif isinstance(author_obj, str):
            author_display = author_obj
        else:
            author_display = ""

        issuer_name = report.get("issuerStmt", "") or ""

        pub_time = report.get("pubDate") or report.get("rptTime")
        file_time = ""
        if pub_time:
            file_time = datetime.datetime.fromtimestamp(pub_time / 1000).strftime("%Y-%m-%d %H:%M:%S")
        elif report.get("rptDate"):
            rpt_date_str = str(report["rptDate"])
            file_time = f"{rpt_date_str[:4]}-{rpt_date_str[4:6]}-{rpt_date_str[6:8]}"

        rpt_scr = report.get("aflScr",{}).get("display", "") if report.get("aflScr", {}) else ""
        rpt_block = report.get("aflBlock",{}).get("display", "") if report.get("aflBlock", {}) else ""

        item = {
            "标题": remove_html_tags(report.get("title", "")),
            "文件时间": file_time,
            "作者": author_display,
            "来源机构": issuer_name,
            "所属证券": rpt_scr,
            "所属板块": rpt_block,
            "网络连接": report.get("url", ""),
            "摘要": remove_html_tags(report.get("brief", "") or ""),
            "类型": "研究报告",
            "类型中ID": str(report.get("rptId", "") or report.get("id", "")),
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
    return [REPORT_SOURCE_MAP[name] for name in source_types if name in REPORT_SOURCE_MAP]


def _resolve_honor_types(honor_types: List[str]) -> List[str]:
    if not honor_types:
        return []
    return [HONOR_TYPE_MAP[name] for name in honor_types if name in HONOR_TYPE_MAP]


def _clean_keyword(keyword: str, securities=None, source_types=None, institutions=None, industries=None) -> str:
    if not keyword:
        return ""
    keyword = (
        keyword.replace("[", "").replace("]", "")
        .replace("、", " ").replace("，", " ")
        .replace(", ", " ").replace(",", " ")
    )
    keyword = (
        keyword.replace("的研报", "").replace("的研究报告", "")
        .replace("的报告", "").replace("研报", "")
        .replace("研究报告", "").replace("报告", "")
    )
    for items in [securities, source_types, institutions, industries]:
        if items:
            for item in items:
                keyword = keyword.replace(item, "")
    return keyword.strip()


def _fetch_reports(headers, payload_base, keyword, search_type, limit):
    """分页获取研报，返回格式化后的结果列表"""
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

        response = requests.post(REPORT_URL, headers=headers, json=data)
        if response.status_code != 200:
            return None, response.text
        result = response.json()

        if result.get("code") not in [200, "000000"] and result.get("status") is not True:
            return None, result.get("msg", "请求失败")

        report_data = result.get("data", {})
        reports = report_data.get("data", [])
        if not reports:
            break

        all_results.extend(_format_report_item(reports))

        if len(reports) < page_size:
            break

        offset += page_size
        remaining -= len(reports)

    return all_results, None


def report_finder(
    keyword: str = "",
    securities: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    institutions: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    source_types: Optional[List[str]] = None,
    honor_types: Optional[List[str]] = None,
    deep: Optional[bool] = None,
    limit: int = FILE_DEFAULT_LIMIT["report"],
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
        org_ids = _resolve_institutions(institutions) if institutions else []
        source_ids = _resolve_sources(source_types) if source_types else []
        honor_ids = _resolve_honor_types(honor_types) if honor_types else []

        if securities:
            securities = [security.upper() for security in securities]

        if securities and industries:
            industry_ids = []

        start_timestamp, end_timestamp = _format_time_range(start_date, end_date)

        keyword_str = _clean_keyword(keyword, securities, source_types, institutions, industries)

        payload_base = {}
        if start_timestamp:
            payload_base["startTime"] = start_timestamp
        if end_timestamp:
            payload_base["endTime"] = end_timestamp
        if source_ids:
            payload_base["source"] = source_ids
        if securities:
            payload_base["stockList"] = securities
        if industry_ids:
            payload_base["industryList"] = industry_ids
        if org_ids:
            payload_base["orgList"] = org_ids
        if honor_ids:
            payload_base["honorTypeList"] = honor_ids
        if deep is not None:
            payload_base["deep"] = 1 if deep else 0

        all_results, err = _fetch_reports(headers, payload_base, keyword_str, 1, limit)
        if err:
            return format_response({"state": "error", "message": err}, "report")

        if not all_results and keyword_str:
            all_results, err = _fetch_reports(headers, payload_base, keyword_str, 2, limit)
            if err:
                return format_response({"state": "error", "message": err}, "report")

        if not all_results:
            return format_response(
                {"state": "error", "message": "未找到相关研报，建议修改查询条件", "data": []},
                "report",
            )

        all_results = all_results[:limit]

        response_data = {
            "state": "success",
            "message": "已找到相关研报",
            "data": [{"data": all_results, "module": "report", "type": "files"}],
        }
        return format_response(response_data, "report")
    except Exception as e:
        return format_response(
            {"state": "error", "message": str(e), "data": [], "usage": {}},
            "report",
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
        description="研报检索命令行：根据关键词、证券、机构等条件查找研究报告。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-k", "--keyword", default="", help="检索查询关键词，可为空")
    parser.add_argument("-sd", "--start_date", default="", help="开始日期，格式YYYY-MM-DD")
    parser.add_argument("-ed", "--end_date", default="", help="结束日期，格式YYYY-MM-DD")
    parser.add_argument(
        "-l",
        "--limit",
        default=FILE_DEFAULT_LIMIT["report"],
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
        help="来源类型列表，逗号分隔（研报/公众号）",
    )
    parser.add_argument(
        "--honor_types",
        default="",
        help="荣誉类型列表，逗号分隔（新财富/金牛/水晶球）",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        default=False,
        help="是否仅限深度报告",
    )

    args = parser.parse_args()

    keyword = args.keyword or ""
    securities = _parse_str_list(args.securities)
    institutions = _parse_str_list(args.institutions)
    industries = _parse_str_list(args.industries)
    source_types = _parse_str_list(args.source_types)
    honor_types = _parse_str_list(args.honor_types)
    start_date = args.start_date or None
    end_date = args.end_date or None
    limit = int(args.limit)
    deep = args.deep if args.deep else None

    out = report_finder(
        keyword=keyword,
        securities=securities,
        start_date=start_date,
        end_date=end_date,
        institutions=institutions,
        industries=industries,
        source_types=source_types,
        honor_types=honor_types,
        deep=deep,
        limit=limit,
    )
    print(out)


if __name__ == "__main__":
    main()
