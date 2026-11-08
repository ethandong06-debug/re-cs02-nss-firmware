#!/usr/bin/env python3
"""Regression check for the V1.0 RPC gateway, rpcd ACL and APK installation."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) != 5:
        print("usage: check_rpc_wiring.py index.html gateway.sh acl.json Makefile", file=sys.stderr)
        return 2
    index_path, gateway_path, acl_path, makefile_path = map(Path, sys.argv[1:])
    try:
        html=index_path.read_text(encoding="utf-8")
        gateway=gateway_path.read_text(encoding="utf-8")
        acl=json.loads(acl_path.read_text(encoding="utf-8"))
        makefile=makefile_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"input error: {exc}", file=sys.stderr); return 1

    errors=[]
    if "/usr/libexec/athena-v1.sh" not in html:
        errors.append("前端未通过 V1 RPC 网关执行命令")
    if "command:'/usr/libexec/athena-v1.sh'" not in html and 'command:"/usr/libexec/athena-v1.sh"' not in html:
        errors.append("前端 RPC 目标路径与网关不一致")
    if "athena-v1.sh" not in makefile or "PKG_RELEASE:=8" not in makefile:
        errors.append("APK Makefile 未安装网关或未递增版本")
    acl_root=acl.get("luci-app-athena",{}).get("write",{})
    file_acl=acl_root.get("file",{})
    if set(file_acl)!={"/usr/libexec/athena-v1.sh"} or file_acl.get("/usr/libexec/athena-v1.sh")!=["exec"]:
        errors.append("rpcd ACL 必须只授权 athena-v1.sh 的 exec")
    if acl_root.get("ubus",{}).get("file")!=["exec"]:
        errors.append("rpcd ACL 的 ubus.file 权限必须仅为 exec")
    for forbidden in ("athena-mode.sh","athena-upgrade.sh","athena-reset.sh"):
        if forbidden in file_acl:
            errors.append(f"高风险脚本不应直接暴露给前端 ACL：{forbidden}")
    for dangerous in ("eval ", "sh -c", "system("):
        if dangerous in gateway:
            errors.append(f"网关疑似包含动态命令执行：{dangerous}")
    for required in ("status)","wifi-set)","disk-format)","nas-remove)","backup-create)"):
        if required not in gateway:
            errors.append(f"网关缺少预期命令分支：{required}")
    if errors:
        print("\n".join("FAIL: "+x for x in errors)); return 1
    print("RPC 安全接线检查通过：前端只调用 V1 网关；ACL 只开放网关；APK 已安装网关；模式切换/升级/重置脚本未直接授权。")
    print("注意：该静态检查不替代真机上的参数边界、接口返回和回滚测试。")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
