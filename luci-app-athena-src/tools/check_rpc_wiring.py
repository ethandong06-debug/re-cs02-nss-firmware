#!/usr/bin/env python3
"""Check literal Athena RPC targets against rpcd ACL and APK install rules.

Usage:
  python3 tools/check_rpc_wiring.py index.html luci-app-athena.json Makefile
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print("用法: check_rpc_wiring.py index.html luci-app-athena.json Makefile", file=sys.stderr)
        return 2

    html_path, acl_path, makefile_path = map(Path, sys.argv[1:])
    try:
        html = html_path.read_text(encoding="utf-8")
        acl = json.loads(acl_path.read_text(encoding="utf-8"))
        makefile = makefile_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"读取输入失败：{exc}", file=sys.stderr)
        return 1

    rpc_targets = set(re.findall(
        r"""athenaRPC\.exec\(\s*['"]([^'"]+\.sh)['"]""", html
    ))

    acl_root = acl.get("luci-app-athena", {}).get("write", {}).get("file", {})
    acl_targets = {
        key.rsplit("/", 1)[-1]
        for key, permissions in acl_root.items()
        if key.startswith("/usr/libexec/") and "exec" in permissions
    }

    install_targets = set(re.findall(
        r"""INSTALL_BIN\s+\./root/usr/libexec/([A-Za-z0-9_.-]+)""",
        makefile,
    ))

    missing_acl = sorted(rpc_targets - acl_targets)
    missing_package = sorted(rpc_targets - install_targets)
    if missing_acl or missing_package:
        if missing_acl:
            print("RPC 已调用但 ACL 未授权：", ", ".join(missing_acl))
        if missing_package:
            print("RPC 已调用但 APK 未安装：", ", ".join(missing_package))
        return 1

    print(
        f"RPC 接线检查通过：{len(rpc_targets)} 个静态脚本目标均已列入 ACL 和 Makefile。"
    )
    print("注意：此检查不验证脚本内部参数、命令分支或运行时真实效果。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
