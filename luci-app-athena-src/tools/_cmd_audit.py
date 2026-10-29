#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态命令依赖审计：提取 athena-*.sh 调用的外部命令，在固件 rootfs 检查是否存在"""
import re, io, sys, os, paramiko
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
LIB = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"

# 收集所有脚本全文
full = {}
for f in sorted(os.listdir(LIB)):
    if f.endswith(".sh"):
        full[f] = open(os.path.join(LIB, f), encoding="utf-8").read()

# 提取候选命令：行首 / 管道后 / 分号后 / && || 后 / 赋值后 的小写标识符（排除变量 $、内建关键字）
builtin = {"if","then","else","elif","fi","case","esac","for","while","do","done","in","return","exit","local",
    "echo","true","false","shift","set","export","unset","break","continue","read","sleep","trap","cd","pwd",
    "eval","exec","wait","type","command","umask","ulimit","times","alias","printf","getopts","source","."
}
cands = {}
pat = re.compile(r'(?:^|[\|\;&\(]\s*|&&\s*|\|\|\s*|\{\s*|\bdo\s*|\bthen\s*|=\s*)([a-zA-Z][a-zA-Z0-9_]*)\b')
pat2 = re.compile(r'\b(?:uci|ubus|ip|brctl|iw|iwlist|wpa_cli|hostapd|killall|nft|tc|ethtool)\b')
for f, txt in full.items():
    got = set()
    # 方式1：控制位后
    for m in pat.finditer(txt):
        w = m.group(1)
        if w not in builtin and not w.startswith("echo"):
            got.add(w)
    # 方式2：$(...) 与 ${...} 内第一条命令（浅层）
    for m in re.finditer(r'\$\(\s*([a-zA-Z][a-zA-Z0-9_]*)', txt):
        got.add(m.group(1))
    for m in re.finditer(r'\$\{([a-zA-Z][a-zA-Z0-9_]*):-', txt):
        pass
    cands[f] = sorted(got)

allcmd = set()
for f, cs in cands.items():
    allcmd.update(cs)
    print("== %s (%d) ==" % (f, len(cs)))
    print("  " + ", ".join(cs))

# VM 检查存在性
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)
R = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax"
# 拿到 rootfs 内所有可执行文件名
i, o, e = c.exec_command("ls %s/bin %s/sbin %s/usr/bin %s/usr/sbin %s/usr/libexec 2>/dev/null | sort -u" % (R,R,R,R,R), timeout=60)
have = set(o.read().decode("utf-8","replace").split())
c.close()

missing = sorted(x for x in allcmd if x not in have)
print("\n== 疑似缺失命令（rootfs 无同名文件；busybox applet 需另判）==")
print(", ".join(missing) if missing else "无")
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_cmd_audit.txt","w",encoding="utf-8").write(
    "== 疑似缺失 ==\n" + (", ".join(missing) if missing else "无") + "\n\n== 全部候选命令 ==\n" + ", ".join(sorted(allcmd)))
