# -*- coding: utf-8 -*-
"""把 athena-resources.sh 拆成：入口(dispatch)+legacy(老 JSON 组装实现)，并生成 ucode 采集器入口。"""
import io, os, re

root = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
sh = os.path.join(root, "athena-resources.sh")
t = io.open(sh, encoding="utf-8").read()

MARK = "# ---- CPU 总量（/proc/stat 的 cpu 行）----"
i = t.index(MARK)
head, tail = t[:i], t[i:]

# 变量块（CACHE/HZ/NCPU/PAGESIZE/json_str）需要给 legacy 用
m = re.search(r"CACHE=/tmp/athena-res-cache\n.*?json_str\(\) \{.*?\}\n", head, re.S)
vars_block = m.group(0) if m else ""

# stop/restart 分支原样保留在入口
m2 = re.search(r"# ---- 进程操作：.*?\nfi\n", head, re.S)
stop_block = m2.group(0) if m2 else ""
# 去掉 stop_block 里对 json_str 等变量的依赖：它只用 PID/NAME，无需 vars

entry = """#!/bin/sh
# AthenaWrt 资源监控入口（v1.2.44）
#
# 采样逻辑已搬到 ucode：/usr/libexec/athena-resources.uc
#   旧实现一次采样触发 459 次 execve（146 进程 × 3 个外部命令），真机 1.80 秒；
#   ucode 版一次采样只 1 次 execve，编译器实测 0.02 秒。
# 本脚本只保留：
#   1) 进程启停（stop/restart —— 这一步要 kill，本来就要起进程，频率极低）
#   2) 入口：exec 到 ucode；ucode 不可用时回退到 legacy shell 实现
#
# rpcd ACL 仍只认这个路径，所以前端/ACL 都不用改。

""" + stop_block + """
# ---- 采样 ----
if [ -x /usr/bin/ucode ] && [ -r /usr/libexec/athena-resources.uc ]; then
\texec /usr/bin/ucode /usr/libexec/athena-resources.uc
fi

# 兜底：ucode 缺失（理论不会发生，ucode 是 LuCI 的运行时）时走旧 shell 实现
exec /usr/libexec/athena-resources-legacy.sh
"""

legacy = """#!/bin/sh
# AthenaWrt 资源监控 —— 旧 shell 实现（v1.2.43 逻辑，原样保留做兜底）
# 只在 /usr/bin/ucode 缺失时被 athena-resources.sh exec 调用；
# 正常路径走 athena-resources.uc（1 次 execve）。
#
""" + vars_block + "\n" + tail

io.open(sh, "w", encoding="utf-8", newline="").write(entry)
io.open(os.path.join(root, "athena-resources-legacy.sh"), "w", encoding="utf-8", newline="").write(legacy)
print("entry", len(entry.encode("utf-8")), "legacy", len(legacy.encode("utf-8")), "vars", len(vars_block))
