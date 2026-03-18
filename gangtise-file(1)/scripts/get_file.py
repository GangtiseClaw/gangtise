import os
import sys
import requests
from urllib.parse import unquote

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from utils import (
    GTS_AUTHORIZATION,
    FILE_URL,
    SUMMARY_DOWNLOAD_URL,
    COMPANY_ANNOUNCEMENT_DOWNLOAD_URL,
    REPORT_DOWNLOAD_URL,
    FILE_TYPE_MAP,
    file_dir,
    check_version,
)

def safe_file_title(file_item):
    title = file_item["title"]
    not_allow_title_symbol = [
        "\\", ":", "*", "?", "\"", "<", ">", "|", 
        "=", "&", "\0"
    ]
    for symbol in not_allow_title_symbol:
        title = title.replace(symbol, "")
    title = title.replace(" ", "_")
    return title

def get_file(
    file_id: str,
    file_type: str,
    output: str = None,
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
        task_status = False

        # 使用对应接口下载文件
        url_map = {
            "会议纪要": SUMMARY_DOWNLOAD_URL,
            "公司公告": COMPANY_ANNOUNCEMENT_DOWNLOAD_URL,
            "研究报告": REPORT_DOWNLOAD_URL,
        }
        params = {
            "id": file_id,
        }
        if file_type in url_map:
            response = requests.get(url_map[file_type], headers=headers, params=params, timeout=300)
            if response.status_code != 200:
                return f"获取文件失败：{response.status_code} {response.text}"
            return_message = ""
            if response.headers.get("Content-Type") == "application/json":
                return f"不存在文件，为网络地址：{response.json()['url']}"

        # 如果不行，尝试FILE_URL
        else:
            params = {
                "sourceId": file_id,
                "resourceType": FILE_TYPE_MAP[file_type],
            }
            response = requests.get(FILE_URL, headers=headers, params=params, timeout=300)
            if response.status_code != 200:
                return f"获取文件失败：{response.status_code} {response.text}"
            return_message = ""
            if response.headers.get("Content-Type") == "application/json":
                return f"不存在文件，为网络地址：{response.json()['url']}"
        if output:
            if output.split(".")[-1] != response.headers["Content-Disposition"].split("filename=")[1].split(".")[-1]:
                if len(response.headers["Content-Disposition"].split("filename=")) > 1:
                    output = ".".join(output.split(".")[:-1]) + "." + unquote(response.headers["Content-Disposition"].split("filename=")[1]).split(".")[-1]
                else:
                    output = ".".join(output.split(".")[:-1]) + "." + unquote(response.headers["Content-Disposition"].split("filename*=utf-8''")[1]).split(".")[-1]
            output = safe_file_title({"title": output, "url": "."+output.split(".")[-1]})
            return_message = f"文件保存路径已自动修正，并保存到：{output}"
        else:
            if len(response.headers["Content-Disposition"].split("filename=")) > 1:
                output = os.path.join(file_dir, unquote(response.headers["Content-Disposition"].split("filename=")[1]))
            else:
                output = os.path.join(file_dir, unquote(response.headers["Content-Disposition"].split("filename*=utf-8''")[1]))
            if output.startswith("\""):
                output = output[1:-1]
            output = safe_file_title({"title": output, "url": "."+output.split(".")[-1]})
            return_message = f"文件已保存到：{output}"
        with open(output, "wb") as f:
            f.write(response.content)
        return return_message
    except Exception as e:
        return f"获取文件失败：{str(e)}"


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="RAG 文件检索命令行：按查询语句检索相关文件。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-id", "--file-id", default="", help="文件ID")
    parser.add_argument("-type", "--file-type", default="", help="文件类型")
    parser.add_argument("-o", "--output", default="", help="输出文件路径")

    args = parser.parse_args()

    file_id = args.file_id.strip()
    if not file_id:
        parser.error("必须提供文件ID：-id/--file-id")

    file_type = args.file_type.strip()
    if not file_type:
        parser.error("必须提供文件类型：-type/--file-type")

    out = get_file(
        file_id=file_id,
        file_type=file_type,
        output=args.output,
    )
    print(out)


if __name__ == "__main__":
    main()