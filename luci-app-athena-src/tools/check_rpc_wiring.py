#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def main():
    if len(sys.argv)!=6:
        print("usage: check_rpc_wiring.py index.html runtime.js gateway.sh acl.json Makefile",file=sys.stderr); return 2
    index,runtime,gateway,acl_path,makefile_path=map(Path,sys.argv[1:])
    try:
        html=index.read_text(encoding="utf-8"); js=runtime.read_text(encoding="utf-8")
        sh=gateway.read_text(encoding="utf-8"); acl=json.loads(acl_path.read_text()); mk=makefile_path.read_text()
    except Exception as e:
        print("input error:",e); return 1
    errors=[]
    if "athena-v1-runtime.js" not in html: errors.append("index.html 未加载 V1 runtime")
    if "/usr/libexec/athena-v1.sh" not in js: errors.append("runtime 未调用唯一 RPC 网关")
    if "athena-v1.sh" not in mk or "athena-wifi-schedule.sh" not in mk or "PKG_RELEASE:=9" not in mk:
        errors.append("Makefile 未安装 V1 网关/无线定时脚本或版本号错误")
    root=acl.get("luci-app-athena",{}).get("write",{})
    file_acl=root.get("file",{})
    if set(file_acl)!={"/usr/libexec/athena-v1.sh"} or file_acl.get("/usr/libexec/athena-v1.sh")!=["exec"]:
        errors.append("ACL 必须只允许执行 athena-v1.sh")
    if root.get("ubus",{}).get("file")!=["exec"]: errors.append("ubus.file 权限必须仅为 exec")
    if any(x in file_acl for x in ("athena-mode.sh","athena-upgrade.sh","athena-reset.sh")):
        errors.append("高风险脚本被直接暴露")
    if any(x in sh for x in ("eval ", "sh -c", "system(")): errors.append("网关包含动态命令执行")
    if "backup-restore)" in sh or "V.call('backup-restore'" in js:
        errors.append("V1.0 不应开放整份系统配置恢复")
    if "wifi-set) need 7" not in sh:
        errors.append("无线设置网关必须校验隐藏 SSID 参数数量")
    if "protected_pkg()" not in (gateway.parent / "athena-packages-legacy.sh").read_text(encoding="utf-8"):
        errors.append("软件包后端缺少关键组件保护逻辑")
    labels=__import__("re").findall(r"^\\s*([A-Za-z0-9_-]+)\\)", sh, __import__("re").M)
    dup=sorted({x for x in labels if labels.count(x)>1})
    if dup: errors.append("网关存在重复 case 分支："+", ".join(dup))
    for marker in ("status)","wifi-set)","disk-format)","nas-remove)","backup-create)","wifi-schedule-set)","reboot-now)"):
        if marker not in sh: errors.append("网关缺少分支 "+marker)
    if errors:
        print("\\n".join("FAIL: "+x for x in errors)); return 1
    print("RPC 接线通过：V1 runtime -> 单一网关 -> 最小 ACL -> APK 安装清单。")
    print("网络模式切换、整机刷写、恢复出厂未授予前端直接执行权限。")
    return 0
if __name__=="__main__": raise SystemExit(main())
