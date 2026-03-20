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
    COMPANY_ANNOUNCEMENT_URL,
    FILE_DEFAULT_LIMIT,
    format_response,
    remove_html_tags,
    check_version,
)


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


def _format_announcement_item(announcements: List[dict]) -> List[dict]:
    _results = []
    for ann in announcements:
        pub_time = ann.get("pubTime")
        file_time = ""
        if pub_time:
            file_time = datetime.datetime.fromtimestamp(pub_time / 1000).strftime("%Y-%m-%d %H:%M:%S")
        elif ann.get("annDate"):
            ann_date_str = str(ann["annDate"])
            file_time = f"{ann_date_str[:4]}-{ann_date_str[4:6]}-{ann_date_str[6:8]}"

        category_obj = ann.get("category")
        category_display = ""
        if isinstance(category_obj, dict):
            category_display = category_obj.get("display", "")

        item = {
            "标题": remove_html_tags(ann.get("title", "")),
            "文件时间": file_time,
            "所属证券": ann.get("scrAbbr", "") or "",
            "公告类型": category_display,
            "来源": ann.get("sourceStmt", "") or "",
            "摘要": remove_html_tags(ann.get("brief", "") or ""),
            "类型": "公司公告",
            "类型中ID": str(ann.get("id", "")),
        }
        _results.append(item)
    return _results


def _clean_keyword(keyword: str, securities=None) -> str:
    if not keyword:
        return ""
    keyword = (
        keyword.replace("[", "").replace("]", "")
        .replace("、", " ").replace("，", " ")
        .replace(", ", " ").replace(",", " ")
    )
    keyword = (
        keyword.replace("的公告", "").replace("的公司公告", "")
        .replace("公司公告", "").replace("公告", "")
    )
    if securities:
        for item in securities:
            keyword = keyword.replace(item, "")
    return keyword.strip()


def _fetch_announcements(headers, payload_base, keyword, search_type, limit):
    """分页获取公告，返回格式化后的结果列表"""
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

        response = requests.post(COMPANY_ANNOUNCEMENT_URL, headers=headers, json=data)
        if response.status_code != 200:
            return None, response.text
        result = response.json()

        if result.get("code") not in [200, "000000"] and result.get("status") is not True:
            return None, result.get("msg", "请求失败")

        ann_data = result.get("data", {})
        announcements = ann_data.get("data", [])
        if not announcements:
            break

        all_results.extend(_format_announcement_item(announcements))

        if len(announcements) < page_size:
            break

        offset += page_size
        remaining -= len(announcements)

    return all_results, None


def announcement_finder(
    keyword: str = "",
    securities: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = FILE_DEFAULT_LIMIT["announcement"],
):
    try:
        headers = {
            "Authorization": GTS_AUTHORIZATION,
        }

        if securities:
            securities = [security.upper() for security in securities]

        start_timestamp, end_timestamp = _format_time_range(start_date, end_date)

        keyword_str = _clean_keyword(keyword, securities)

        payload_base = {}
        if start_timestamp:
            payload_base["startTime"] = start_timestamp
        if end_timestamp:
            payload_base["endTime"] = end_timestamp
        if securities:
            payload_base["stockList"] = securities

        all_results, err = _fetch_announcements(headers, payload_base, keyword_str, 1, limit)
        if err:
            return format_response({"state": "error", "message": err}, "announcement")

        if not all_results and keyword_str:
            all_results, err = _fetch_announcements(headers, payload_base, keyword_str, 2, limit)
            if err:
                return format_response({"state": "error", "message": err}, "announcement")

        if not all_results:
            return format_response(
                {"state": "error", "message": "未找到相关公告，建议修改查询条件", "data": []},
                "announcement",
            )

        all_results = all_results[:limit]

        response_data = {
            "state": "success",
            "message": "已找到相关公告",
            "data": [{"data": all_results, "module": "announcement", "type": "files"}],
        }
        return format_response(response_data, "announcement")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return format_response(
            {"state": "error", "message": str(e), "data": [], "usage": {}},
            "announcement",
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
        description="公告检索命令行：根据关键词、证券代码等条件查找公司公告。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-k", "--keyword", default="", help="检索查询关键词，可为空")
    parser.add_argument("-sd", "--start_date", default="", help="开始日期，格式YYYY-MM-DD")
    parser.add_argument("-ed", "--end_date", default="", help="结束日期，格式YYYY-MM-DD")
    parser.add_argument(
        "-l",
        "--limit",
        default=FILE_DEFAULT_LIMIT["announcement"],
        type=int,
        help="返回文件数量上限",
    )
    parser.add_argument(
        "--securities",
        default="",
        help="证券代码列表，逗号分隔，必须为标准证券代码，如 000001.SZ",
    )
    try:
        if not check_version():
            update_sh = os.path.join(script_dir, "update.sh")
            print(f"[WARNING] 存在 Gangtise skills 版本更新，可以执行 {update_sh} 更新，请与用户确认是否更新\n")
    except Exception as e:
        print(f"[WARNING] 检查 Gangtise skills 版本失败\n")

    args = parser.parse_args()
    keyword = args.keyword or ""
    securities = _parse_str_list(args.securities)
    start_date = args.start_date or None
    end_date = args.end_date or None
    limit = int(args.limit)

    out = announcement_finder(
        keyword=keyword,
        securities=securities,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    print(out)


if __name__ == "__main__":
    main()
