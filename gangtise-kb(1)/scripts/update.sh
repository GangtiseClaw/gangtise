#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${ROOT_DIR}"

echo "工作目录: ${ROOT_DIR}"

if [[ ! -d "gangtise-kb" ]]; then
  echo "错误: 在 ${ROOT_DIR} 下未找到 gangtise-kb 目录"
  exit 1
fi

echo "开始备份 gangtise-kb ..."

zip -r "gangtise-kb.bak" "gangtise-kb"

echo "备份完成，删除原目录 ..."

# 备份当前脚本目录下的 .authorization（如果存在），以便更新后恢复
AUTH_BACKUP=""
if [[ -f "${SCRIPT_DIR}/.authorization" ]]; then
  AUTH_BACKUP="$(mktemp /tmp/authorization.XXXXXX)"
  cp "${SCRIPT_DIR}/.authorization" "${AUTH_BACKUP}"
  echo "已备份 .authorization 到临时文件: ${AUTH_BACKUP}"
fi

rm -rf "gangtise-kb"

# 使用通用临时文件路径，避免模板名已存在导致 mktemp 失败
TMP_ZIP="$(mktemp)"

echo "从远程下载最新 gangtise-kb.zip ..."

curl -L "https://open.gangtise.com/obsproxy/windowsx64/gangtise-kb.zip" -o "${TMP_ZIP}"

echo "在 ${ROOT_DIR} 下解压 ..."

unzip -o "${TMP_ZIP}"

# 如果之前备份了 .authorization，则恢复到新的脚本目录下
if [[ -n "${AUTH_BACKUP}" && -f "${AUTH_BACKUP}" ]]; then
  cp "${AUTH_BACKUP}" "${SCRIPT_DIR}/.authorization"
  rm -f "${AUTH_BACKUP}"
  echo "已恢复 SCRIPT_DIR 下的 .authorization"
fi

rm -f "${TMP_ZIP}"

echo "更新完成。"

