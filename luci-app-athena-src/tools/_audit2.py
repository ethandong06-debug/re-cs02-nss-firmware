#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Athena 前端彻底假数据审计：
1) 所有顶层变量声明的初始值（可疑硬编码数值）
2) !athenaRPC.live 演示分支内容清单
3) 硬编码时间/温度/速度/百分比/版本/IP 文本
4) 视图渲染中的字面量数字
"""
import re, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HTML = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
src = open(HTML, encoding="utf-8").read()
out = []

# ---- 1) 顶层变量声明 ----
out.append("== 顶层 let/const 声明及初始值 ==")
for m in re.finditer(r'^(?:let|const|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([^\n]+)$', src, re.M):
    name, val = m.group(1), m.group(2).strip()
    if len(val) > 90: val = val[:87] + "..."
    out.append("%-22s = %s" % (name, val))

# ---- 2) 演示分支 ----
out.append("\n== !athenaRPC.live 演示分支（真机不执行，但列出确认）==")
for m in re.finditer(r'if\(!athenaRPC\.live\)\{([\s\S]{0,220}?)\}', src):
    out.append("--- " + m.group(1).strip()[:200].replace("\n", " ") + " ---")

# ---- 3) 硬编码文本模式 ----
out.append("\n== 硬编码时间/状态文本 ==")
for kw in [r'\d+\s*分钟前', r'\d+\s*小时前', r'\d+\s*天\s*\d+\s*小时', r'3 天', r'v1\.0\.0', r'AthenaWrt v']:
    hits = re.findall(kw, src)
    if hits: out.append("%s: %d 处 -> %s" % (kw, len(hits), hits[:5]))

out.append("\n== 视图模板中可疑字面量（温度/速度/百分比数字）==")
for kw in [r'℃', r'°C', r'Mbps', r'GB', r'MB', r'在线设备', r'台设备']:
    hits = [(m.start(), src[max(0,m.start()-40):m.start()+20].replace("\n"," ")) for m in re.finditer(kw, src)]
    if hits: out.append("%s: %d 处" % (kw, len(hits)))
    for pos, ctx in hits[:8]:
        out.append("    @%d: ...%s..." % (pos, ctx))

open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_audit2.txt", "w", encoding="utf-8").write("\n".join(out))
print("AUDIT2 DONE")
