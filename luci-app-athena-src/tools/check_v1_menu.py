#!/usr/bin/env python3
"""Regression guard for the AthenaWrt V1.0 in-app menu.

Usage:
  python3 tools/check_v1_menu.py path/to/index.html

The expected menu is copied from the user-approved V1.0 prototype. Any rename,
reorder, regrouping, addition, or removal fails this check.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED = [
    ("总览", ["首页仪表盘"]),
    ("无线", ["三频 WiFi", "访客网络", "WiFi 定时"]),
    ("网络", ["工作模式与 WAN", "基础网络服务", "网络诊断"]),
    ("终端", ["终端列表", "家长控制"]),
    ("存储", ["存储与磁盘管理", "NAS 文件共享"]),
    ("系统", ["系统维护与备份", "雅典娜点阵屏", "系统日志", "软件包管理"]),
]


def extract_menu(source: str):
    match = re.search(r"window\.groups\s*=\s*\[(.*?)\n\s*\];", source, re.S)
    if not match:
        raise ValueError("未找到 window.groups 菜单定义")
    groups = []
    pattern = re.compile(
        r"\{\s*name\s*:\s*'([^']+)'\s*,\s*pages\s*:\s*\[(.*?)\]\s*\}",
        re.S,
    )
    for item in pattern.finditer(match.group(1)):
        name = item.group(1)
        pages = re.findall(r"'([^']*)'", item.group(2))
        groups.append((name, pages))
    if not groups:
        raise ValueError("找到了 window.groups，但没有解析到任何菜单分组")
    return groups


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: check_v1_menu.py path/to/index.html", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        actual = extract_menu(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"菜单检查失败：{exc}", file=sys.stderr)
        return 1

    if actual != EXPECTED:
        print("菜单与用户确认的 V1.0 基准不一致。")
        print(f"期望：{EXPECTED!r}")
        print(f"实际：{actual!r}")
        return 1

    page_count = sum(len(pages) for _, pages in actual)
    print(f"V1.0 菜单检查通过：{len(actual)} 个分组，{page_count} 个页面；名称、顺序和归属均未改变。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
