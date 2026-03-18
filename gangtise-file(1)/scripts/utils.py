import os
import re
from typing import Dict, List, Any, Optional
# import logging
# from logging.handlers import TimedRotatingFileHandler
from aiohttp.hdrs import AUTHORIZATION
import pandas as pd
import datetime
import requests
import json

GTS_AUTHORIZATION_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".authorization")

AUTHORIZATION_URL = f"https://open.gangtise.com/application/auth/oauth/open/loginV2"

def get_authorization(ak: str, sk: str):
    payload = {
        "accessKey": ak,
        "secretAccessKey": sk
    }
    response = requests.post(AUTHORIZATION_URL, json=payload)
    if response.status_code != 200:
        return None
    try:
        return response.json()["data"]["accessToken"]
    except Exception as e:
        return None

if os.path.exists(GTS_AUTHORIZATION_PATH):
    with open(GTS_AUTHORIZATION_PATH, "r", encoding="utf-8") as f:
        content = json.load(f)
        if content.get("long-term-token", None):
            long_term_token = content["long-term-token"]
            GTS_AUTHORIZATION = long_term_token if long_term_token.startswith("Bearer ") else "Bearer " + long_term_token
        elif content.get("accessKey", None) and content.get("secretAccessKey", None):
            GTS_AUTHORIZATION = get_authorization(content["accessKey"], content["secretAccessKey"])
        else:
            GTS_AUTHORIZATION = None

GTS_SAVE_FILE = os.getenv("GTS_SAVE_FILE", None)
if GTS_SAVE_FILE is None:
    GTS_SAVE_FILE = False

GANGTISE_DOMAIN = os.getenv("GANGTISE_DOMAIN", "https://open.gangtise.com/application/open-data")

REPORT_URL = f"{GANGTISE_DOMAIN}/research/getList"
REPORT_DOWNLOAD_URL = f"{GANGTISE_DOMAIN}/research/download/file"

COMPANY_ANNOUNCEMENT_URL = f"{GANGTISE_DOMAIN}/annc/getList"
COMPANY_ANNOUNCEMENT_DOWNLOAD_URL = f"{GANGTISE_DOMAIN}/annc/download/file"

SUMMARY_URL = f"{GANGTISE_DOMAIN}/summary/getList"
SUMMARY_DOWNLOAD_URL = f"{GANGTISE_DOMAIN}/summary/download/file"

FILE_URL = f"{GANGTISE_DOMAIN}/ai/resource/download"

FILE_DEFAULT_LIMIT = {
    "announcement": 20,
    "calendar": 500,
    "internal_report": 100,
    "opinion": 800,
    "report": 100,
    "summary": 100,
    "wechat_message": 1000,
}

def _find_openclaw_root():
    """向上遍历目录直到找到 .openclaw，返回其上级目录作为执行目录"""
    path = os.path.abspath(os.path.dirname(__file__))
    openclaw_dir_got = False
    while path != os.path.dirname(path):
        dir_name = os.path.basename(path)
        if dir_name in (".openclaw"):
            openclaw_dir_got = True
            return os.path.abspath(path)
        path = os.path.dirname(path)
    if not openclaw_dir_got:
        openclaw_dir_got = False
        while path != os.path.dirname(path):
            dir_name = os.path.basename(path)
            if dir_name in (".agent"):
                openclaw_dir_got = True
                return os.path.abspath(path)
            path = os.path.dirname(path)
    if not openclaw_dir_got:
        openclaw_dir_got = False
        while path != os.path.dirname(path):
            dir_name = os.path.basename(path)
            if dir_name in ("workspace"):
                openclaw_dir_got = True
                return os.path.abspath(path)
            path = os.path.dirname(path)
    return os.path.abspath(os.getcwd())

openclaw_root = _find_openclaw_root()
if openclaw_root.endswith("workspace"):
    gangtise_workspace_path = os.path.join(openclaw_root, "gangtise")
else:
    gangtise_workspace_path = os.path.join(openclaw_root, "workspace", "gangtise")
if not os.path.exists(gangtise_workspace_path):
    os.makedirs(gangtise_workspace_path, exist_ok=True)

usage_dir = os.path.join(gangtise_workspace_path, ".usage")
if not os.path.exists(usage_dir):
    os.makedirs(usage_dir, exist_ok=True)

file_dir = os.path.join(gangtise_workspace_path, "files")
if not os.path.exists(file_dir):
    os.makedirs(file_dir, exist_ok=True)

FILE_TYPE_MAP = {
    "研究报告": 10,
    "外资研报": 11,
    "内部报告": 20,
    "AI云盘": 30,
    "首席观点": 40,
    "公司公告": 50,
    "会议纪要": 60,
    "调研纪要": 70,
    "网络纪要": 80,
    "产业公众号": 90,
}

FILE_TYPE_MAP_REVERSE = {
    v: k for k, v in FILE_TYPE_MAP.items()
}

INDUSTRIES_MAP = {
    "中信行业分类":{
        "石油石化": 100800101,
        "煤炭": 100800102,
        "有色金属": 100800103,
        "电公": 100800104,
        "钢铁": 100800105,
        "基础化工": 100800106,
        "建筑": 100800107,
        "建材": 100800108,
        "轻工制造": 100800109,
        "机械": 100800110,
        "电新": 100800111,
        "国防军工": 100800112,
        "汽车": 100800113,
        "商贸零售": 100800114,
        "消服": 100800115,
        "家电": 100800116,
        "纺织服装": 100800117,
        "医药": 100800118,
        "食品饮料": 100800119,
        "农林牧渔": 100800120,
        "银行": 100800121,
        "非银": 100800122,
        "房地产": 100800123,
        "综合金融": 100800124,
        "交通运输": 100800125,
        "电子": 100800126,
        "通信": 100800127,
        "计算机": 100800128,
        "传媒": 100800129,
        "综合": 100800130,
    },
    # 申万行业分类
    "申万行业分类": {
        "公用事业": 104410000,
        "机械设备": 104640000,
        "电力设备": 104630000,
        "美容护理": 104770000,
        "商贸零售": 104450000,
        "通信": 104730000,
        "房地产": 104430000,
        "交通运输": 104420000,
        "国防军工": 104650000,
        "轻工制造": 104360000,
        "汽车": 104280000,
        "煤炭": 104740000,
        "环保": 104760000,
        "食品饮料": 104340000,
        "计算机": 104710000,
        "有色金属": 104240000,
        "非银金融": 104490000,
        "综合": 104510000,
        "建筑装饰": 104620000,
        "纺织服饰": 104350000,
        "家用电器": 104330000,
        "医药生物": 104370000,
        "钢铁": 104230000,
        "社会服务": 104460000,
        "农林牧渔": 104110000,
        "银行": 104480000,
        "传媒": 104720000,
        "基础化工": 104220000,
        "建筑材料": 104610000,
        "石油石化": 104750000,
        "电子": 104270000,
    }
}

INSTITUTIONS_MAP = {
    "渤海证券": "C100000001",
    "华福证券": "C100000004",
    "粤开证券": "C100000005",
    "国金证券": "C100000006",
    "山西证券": "C100000007",
    "海通证券": "C100000008",
    "西南证券": "C100000009",
    "南京证券": "C100000010",
    "华泰证券": "C100000014",
    "东北证券": "C100000015",
    "东吴证券": "C100000016",
    "东海证券": "C100000017",
    "中山证券": "C100000018",
    "国海证券": "C100000019",
    "招商证券": "C100000020",
    "广发证券": "C100000021",
    "开源证券": "C100000022",
    "国信证券": "C100000023",
    "方正证券": "C100000024",
    "麦高证券": "C100000025",
    "中金公司": "C100000026",
    "中信证券": "C100000027",
    "英大证券": "C100000028",
    "光大证券": "C100000029",
    "长城证券": "C100000030",
    "平安证券": "C100000031",
    "湘财证券": "C100000032",
    "民生证券": "C100000034",
    "长城国瑞证券": "C100000035",
    "国元证券": "C100000036",
    "东莞证券": "C100000037",
    "长江证券": "C100000039",
    "川财证券": "C100000041",
    "东方证券": "C100000042",
    "第一创业": "C100000043",
    "大同证券": "C100000044",
    "国联证券": "C100000046",
    "国泰君安": "C100000047",
    "首创证券": "C100000048",
    "东方财富证券": "C100000049",
    "天风证券": "C100000050",
    "兴业证券": "C100000051",
    "华西证券": "C100000052",
    "五矿证券": "C100000053",
    "华金证券": "C100000054",
    "华安证券": "C100000055",
    "西部证券": "C100000056",
    "联储证券": "C100000057",
    "华鑫证券": "C100000058",
    "上海证券": "C100000060",
    "华龙证券": "C100000061",
    "中泰证券": "C100000062",
    "宏信证券": "C100000063",
    "万联证券": "C100000064",
    "国都证券": "C100000065",
    "万和证券": "C100000067",
    "华创证券": "C100000068",
    "红塔证券": "C100000069",
    "中银证券": "C100000070",
    "华宝证券": "C100000071",
    "国融证券": "C100000072",
    "财达证券": "C100000073",
    "浙商证券": "C100000075",
    "财信证券": "C100000077",
    "爱建证券": "C100000078",
    "中邮证券": "C100000079",
    "中航证券": "C100000080",
    "中原证券": "C100000081",
    "华源证券": "C100000082",
    "国盛证券": "C100000083",
    "德邦证券": "C100000084",
    "财通证券": "C100000085",
    "诚通证券": "C100000086",
    "江海证券": "C100000088",
    "国开证券": "C100000089",
    "太平洋": "C100000090",
    "中信建投证券": "C100000095",
    "国投证券": "C100000096",
    "银泰证券": "C100000097",
    "瑞银证券": "C100000098",
    "中国银河": "C100000099",
    "信达证券": "C100000100",
    "国新证券": "C100000101",
    "东兴证券": "C100000102",
    "申万宏源证券": "C100000119",
    "申港证券": "C100000126",
    "华兴证券": "C100000128",
    "甬兴证券": "C100000135",
}

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def data_to_md(data: pd.DataFrame, range: List[int]=None, max_cell_length: int=None):
    data_copy = data.copy()
    if "metadata" in data_copy.columns:
        data_copy = data_copy.drop(columns=["metadata"])
    content = "| " + " | ".join(data_copy.columns) + " |\n"
    content += "| " + " | ".join(["-" for _ in data_copy.columns]) + " |\n"
    omitted = False
    for i, row in enumerate(data_copy.to_dict(orient="records")):
        if range:
            if i in range:
                if max_cell_length:
                    content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "")[:max_cell_length]+"..." if len(re.sub(r"\s+", " ", str(row[key])).replace("|", "")) > max_cell_length else re.sub(r"\s+", " ", str(row[key])).replace("|", "") for key in row.keys()]) + " |\n"
                else:
                    content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "") for key in row.keys()]) + " |\n"
            elif not omitted:
                content += "| ... |\n"
                omitted = True
        else:
            if max_cell_length:
                content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "")[:max_cell_length]+"..." if len(re.sub(r"\s+", " ", str(row[key])).replace("|", "")) > max_cell_length else re.sub(r"\s+", " ", str(row[key])).replace("|", "") for key in row.keys()]) + " |\n"
            else:
                content += "| " + " | ".join([re.sub(r"\s+", " ", str(row[key]).replace("\n"," ")).replace("|", "") for key in row.keys()]) + " |\n"
    content = content[:-1]
    return content.strip()

def add_usages(usages_list: List[Dict[str, Any]]):
    usages = {}
    for usages_item in usages_list:
        if len(usages_item) == 0:
            continue
        for k,v in usages_item.items():
            if k not in usages:
                usages[k] = v
            else:
                usages[k] = usages[k] + v
    return usages

def format_response(response: dict, method_name: str, output: Optional[str] = None):
    
    # 保存usage
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now = datetime.datetime.now().strftime("%H%M%S")
    usage_path = os.path.join(usage_dir, f"{today}.json")
    if response.get("usage", None):
        if os.path.exists(usage_path):
            with open(usage_path, "r", encoding="utf-8") as f:
                usage = json.load(f)
            if now in usage:
                now_usage = add_usages([response["usage"], usage[now]])
            else:
                now_usage = response["usage"]
            usage.update({now: now_usage})
        else:
            usage = {now: response["usage"]}
        with open(usage_path, "w", encoding="utf-8") as f:
            json.dump(usage, f, ensure_ascii=False)

    # 保存结果
    return_message = ""
    method_name_map = {
        "report": "研究报告",
        "inner_report": "内部报告",
        "opinion": "首席观点",
        "announcement": "公司公告",
        "summary": "会议纪要",
        "calendar": "投研日程",
        "wechat_message": "微信消息",
    }
    if response["state"] == "success":
        for item in response["data"]:
            module_name = item["module"]
            data = item["data"]
            if GTS_SAVE_FILE:
                if output:
                    process_path = output
                    if os.path.exists(process_path):
                        return_message = "错误信息：文件已存在"
                        return return_message
                else:
                    extension = "md"
                    process_dir = os.path.join(gangtise_workspace_path, method_name)
                    if not os.path.exists(process_dir):
                        os.makedirs(process_dir, exist_ok=True)
                    # now = datetime.datetime.now().strftime("%H%M%S")
                    now = 1
                    process_path = os.path.join(process_dir, f"{module_name}_{now}.{extension}")
                    max_retries = 10
                    for file in os.listdir(process_dir):
                        if file.startswith(f"{module_name}_") and file.endswith(f".{extension}"):
                            max_retries = max(max_retries, int(file.split("_")[-1].split(".")[0])+10)
                    while os.path.exists(process_path) and max_retries > 0:
                        # now = datetime.datetime.now().strftime("%H%M%S")
                        now += 1
                        process_path = os.path.join(process_dir, f"{module_name}_{now}.{extension}")
                        max_retries -= 1
                        # sleep(1)
                    if max_retries == 0:
                        return_message = "错误信息：文件存储系统繁忙，请稍后再试"
                        return return_message
                with open(process_path, "w", encoding="utf-8") as f:
                    for i, file in enumerate(data):
                        f.write(f"标题：{file['标题']}\n")
                        f.write(f"文件时间：{file['文件时间']}\n")
                        for key, value in file.items():
                            if key not in ["标题", "文件时间", "类型", "类型中ID"] and value:
                                if key == "摘要":
                                    f.write(f"摘要：\"\"\"\n{value}\n\"\"\"\n")
                                else:
                                    f.write(f"{key}：{value}\n")
                        f.write(f"file-type：{file['类型']}\n")
                        f.write(f"file-id：{file['类型中ID']}")
                        if i < len(data) - 1:
                            f.write("\n\n---\n\n")
                sample_data = ""
                for file in data:
                    sample_data += f"标题：{file['标题']}\n"
                    sample_data += f"文件时间：{file['文件时间']}\n"
                    for key, value in file.items():
                        if key not in ["标题", "文件时间", "类型", "类型中ID"] and value:
                            if key == "摘要":
                                sample_data += f"摘要：\"\"\"\n{value}\n\"\"\"\n"
                            else:
                                sample_data += f"{key}：{value}\n"
                    sample_data += f"file-type：{file['类型']}\n"
                    sample_data += f"file-id：{file['类型中ID']}"
                    sample_data += "\n\n---\n\n"
                return_message += "### " + method_name_map[method_name] + " 查询结果:\n\n---\n\n" + sample_data + "所有查询结果已保存到md：\"" + os.path.abspath(process_path) + "\""
                return_message += f"\n查询结果共计{len(data)}条"
            else:
                sample_data = ""
                for i, file in enumerate(data):
                    sample_data += f"标题：{file['标题']}\n"
                    sample_data += f"文件时间：{file['文件时间']}\n"
                    for key, value in file.items():
                        if key not in ["标题", "文件时间", "类型", "类型中ID"] and value:
                            if key == "摘要":
                                sample_data += f"摘要：\"\"\"\n{value}\n\"\"\"\n"
                            else:
                                sample_data += f"{key}：{value}\n"
                    sample_data += f"file-type：{file['类型']}\n"
                    sample_data += f"file-id：{file['类型中ID']}"
                    sample_data += "\n\n---\n\n"
                return_message += "### " + method_name_map[method_name] + "查询结果:\n\n---\n\n" + sample_data
                return_message += f"查询结果共计{len(data)}条"
    else:
        return_message = "调用gangtise服务端失败，错误信息：" + response["message"]
    return return_message

def load_securities_from_file(path: str) -> List[str]:
    full_path = path
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"证券文件不存在: {path}")
    df = pd.read_csv(full_path)
    if "security_code" in df.columns:
        return [str(x) for x in df["security_code"].dropna().tolist()]
    if "security_abbr" in df.columns:
        return [str(x) for x in df["security_abbr"].dropna().tolist()]
    raise ValueError("证券文件必须包含 security_code 或 security_abbr 列")

def match_best(item: str, candidates, threshold: float = 0.6):
    """
    candidates: List[str] 时返回匹配的字符串，Dict[str, Any] 时返回匹配 key 的 {k: v}。
    无匹配返回 None。
    """
    from difflib import SequenceMatcher

    if not item or not candidates:
        return None
    if item in candidates:
        return item

    is_dict = isinstance(candidates, dict)
    keys = list(candidates.keys()) if is_dict else candidates

    if item in keys:
        return {item: candidates[item]} if is_dict else item

    best_score = 0.0
    best_key = None

    for key in keys:
        if item in key or key in item:
            overlap = min(len(item), len(key))
            score = overlap / max(len(item), len(key))
            score = max(score, 0.8)
        else:
            score = SequenceMatcher(None, item, key).ratio()

        if score > best_score:
            best_score = score
            best_key = key

    if best_score >= threshold and best_key is not None:
        return {best_key: candidates[best_key]} if is_dict else best_key
    return None

SKILL_VERSION = "1.0.0"
SKILL_CHECK_URL = "https://open.gangtise.com/application/skills-backend/version?skill=openapi"

def check_version():
    response = requests.get(SKILL_CHECK_URL)
    if response.status_code == 200:
        return response.json()["state"] == "success" and response.json()["version"] == SKILL_VERSION
    else:
        return False

if __name__ == "__main__":
    print("检查 gangtise-file 相关配置")
    if not os.path.exists(GTS_AUTHORIZATION_PATH):
        print("  无法检测到gangtise授权文件, gangtise-file 无法正常工作")
    elif GTS_AUTHORIZATION is None:
        print("  授权文件存在, 但无法获取gangtise授权, 请检查授权文件内容中是否含有 long-term-token 或者 accessKey 和 secretAccessKey, gangtise-file 无法正常工作")
    else:
        print("  检测到gangtise授权文件, gangtise-file 可以正常工作")
    if GTS_SAVE_FILE is None:
        print("  环境变量 GTS_SAVE_FILE 未配置, 默认值为 False, gangtise服务端 将不保存查询结果到文件中")
    elif GTS_SAVE_FILE == "True":
        print("  环境变量 GTS_SAVE_FILE 为 True, gangtise服务端 将保存查询结果到文件中")
    else:
        print("  环境变量 GTS_SAVE_FILE 为 False, gangtise服务端 将不保存查询结果到文件中")
    print(f"  gangtise-file 工作文件目录: {gangtise_workspace_path}")