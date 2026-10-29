# -*- coding: utf-8 -*-
"""把预览稿里 athena-resources.sh 的 mock 换成指定形态：
   b = 旧后端（无 window/procs_mb/other_mb/rss_mb，但有 total_mb/used_mb/pct）
   a = 新后端（含全部追加字段）
"""
import io, sys, json

P = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\preview\AthenaWrt-全站v5.html"
mode = sys.argv[1] if len(sys.argv) > 1 else "a"

t = io.open(P, encoding="utf-8").read()
key = '"athena-resources.sh":'
i = t.find(key)
assert i > 0, "mock key not found"
start = i + len(key)
# 从 key 后的第一个 { 开始做括号匹配
j = t.find("{", start)
depth = 0
k = j
while k < len(t):
    if t[k] == "{":
        depth += 1
    elif t[k] == "}":
        depth -= 1
        if depth == 0:
            break
    k += 1
old = t[j:k + 1]

procs_old = [
    {"pid": 715, "name": "hostapd", "label": "WiFi 服务", "desc": "管理无线网络（WiFi）", "cpu": 4.2, "mem": 2.5, "prot": True},
    {"pid": 812, "name": "uhttpd", "label": "Web 管理界面", "desc": "运行后台管理页面", "cpu": 3.1, "mem": 2.2, "prot": True},
    {"pid": 903, "name": "netifd", "label": "网络服务", "desc": "管理网口与上网连接", "cpu": 2.4, "mem": 1.1, "prot": True},
    {"pid": 640, "name": "dnsmasq", "label": "DNS 与地址分配", "desc": "上网域名解析 + IP 分配", "cpu": 1.6, "mem": 3.0, "prot": True},
    {"pid": 1102, "name": "athena-status.sh", "label": "雅典娜后台服务", "desc": "AthenaWrt 管理功能", "cpu": 1.2, "mem": 0.8, "prot": False},
    {"pid": 588, "name": "odhcpd", "label": "地址分配服务", "desc": "给手机/电脑分配 IP", "cpu": 0.9, "mem": 0.6, "prot": True},
    {"pid": 301, "name": "ubusd", "label": "系统消息中心", "desc": "系统内部通信（可忽略）", "cpu": 0.5, "mem": 0.6, "prot": True},
    {"pid": 455, "name": "dropbear", "label": "远程登录服务", "desc": "允许 SSH 远程登录", "cpu": 0.4, "mem": 1.0, "prot": True},
]
rss = {"hostapd": 22.4, "uhttpd": 19.7, "netifd": 9.9, "dnsmasq": 26.9,
       "athena-status.sh": 7.2, "odhcpd": 5.4, "ubusd": 5.4, "dropbear": 9.0}

if mode == "b":
    procs = [dict(p) for p in procs_old]
    data = {"cpu": {"total": 23, "temp": 47},
            "memory": {"total_mb": 897, "used_mb": 484, "pct": 54},
            "procs": procs}
else:
    procs = []
    for p in procs_old:
        q = dict(p)
        q["rss_mb"] = rss.get(p["name"], 0)
        procs.append(q)
    data = {"cpu": {"total": 23, "temp": 47, "window": 10},
            "memory": {"total_mb": 897, "used_mb": 484, "pct": 54, "procs_mb": 302, "other_mb": 182},
            "procs": procs}

new = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
t = t[:j] + new + t[k + 1:]
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("mode", mode, "old_len", len(old), "new_len", len(new), "file_bytes", len(t.encode("utf-8")))
