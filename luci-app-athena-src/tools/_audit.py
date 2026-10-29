#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Athena 前端全量静态体检：
1) 函数引用 vs 定义（onclick 字符串 + 代码调用）
2) 后端脚本引用 vs libexec 实际文件
3) 假数据残留扫描
4) VIEWS 与 NAV 一致性
"""
import re, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt"
HTML = os.path.join(BASE, r"frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html")
LIBS = os.path.join(BASE, r"frontend\luci-app-athena\root\usr\libexec")
src = open(HTML, encoding="utf-8").read()
out = []

# ---- 1) 函数定义 ----
defs = set()
for m in re.finditer(r"(?:function\s+)([A-Za-z_$][\w$]*)\s*\(", src):
    defs.add(m.group(1))
# const/let x = (args) => 或 = function
for m in re.finditer(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:function\s*\(|\([^)]*\)\s*=>)", src):
    defs.add(m.group(1))
out.append("函数定义数: %d" % len(defs))

# ---- 2) 函数引用 ----
refs = set()
# onclick="fn(...)" / onchange="fn(...)" 等属性内
for m in re.finditer(r'on\w+="([A-Za-z_$][\w$]*)\s*\(', src):
    refs.add(m.group(1))
# 代码中调用 fn( （排除定义处、关键字）
for m in re.finditer(r'(?<![A-Za-z0-9_$.])([A-Za-z_$][\w$]*)\s*\(', src):
    name = m.group(1)
    if name in ('if','for','while','switch','function','return','typeof','catch','new','throw','else','case'):
        continue
    refs.add(name)
out.append("函数引用数(含DOM内置): %d" % len(refs))

missing = sorted(r for r in refs if r not in defs)
# 过滤常见 DOM/内置（白名单）
builtin = {"Math","JSON","Object","Array","String","Number","Date","RegExp","console","setTimeout",
    "setInterval","clearInterval","clearTimeout","parseInt","parseFloat","isNaN","decodeURIComponent",
    "encodeURIComponent","Promise","window","document","alert","confirm","prompt","atob","btoa",
    "athenaRPC","athenaData","fetch","top","self","parent","event","this","undefined","escape"}
suspect = [x for x in missing if x not in builtin]
out.append("\n== 疑似未定义函数引用（点击无反应隐患）==")
out.append(", ".join(suspect) if suspect else "无")

# ---- 3) 后端脚本引用 ----
scripts = set()
for m in re.finditer(r"(?:athenaRPC\.exec|athenaData\.\w+)\s*\(\s*['\"]([\w.-]+\.sh|[\w.-]+)", src):
    scripts.add(m.group(1))
out.append("\n== 前端引用的后端脚本 ==")
out.append(", ".join(sorted(scripts)))
libfiles = set(f for f in os.listdir(LIBS) if f.endswith(".sh"))
out.append("== libexec 实际脚本 ==")
out.append(", ".join(sorted(libfiles)))
missing_scripts = sorted(s for s in scripts if s not in libfiles)
out.append("== 引用但不存在于 libexec 的脚本 ==")
out.append(", ".join(missing_scripts) if missing_scripts else "无")

# ---- 4) 假数据残留 ----
out.append("\n== 假数据残留扫描 ==")
for kw in ["Math.random", "Math\.random", "假数据", "demo", "mock"]:
    hits = len(re.findall(kw, src))
    out.append("%s: %d 处" % (kw, hits))
# 硬编码时间/数值？ 抽查常见假字符串
for kw in ["iPhone 15", "信道已优化", "异常登录", "192.168.1.1"]:
    hits = len(re.findall(kw, src))
    if hits: out.append("硬编码残留 %s: %d 处" % (kw, hits))

# ---- 5) VIEWS vs NAV ----
nav_ids = set(re.findall(r"\{id:'([a-z]+)', name:'[^']+'\}", src[:620]))
view_names = re.findall(r"^\s{2}([a-z]+)\(\)\{", src, re.M)
out.append("\n== NAV 视图 ==")
out.append(", ".join(sorted(nav_ids)))
out.append("== VIEWS 渲染函数 ==")
out.append(", ".join(sorted(set(view_names))))
out.append("== NAV 有但无渲染函数 ==")
out.append(", ".join(sorted(n for n in nav_ids if n not in view_names)) if nav_ids - set(view_names) else "无")
out.append("== 渲染函数有但不在 NAV ==")
out.append(", ".join(sorted(set(view_names) - nav_ids)) if set(view_names) - nav_ids else "无")

p = os.path.join(BASE, "tools", "_audit.txt")
open(p, "w", encoding="utf-8").write("\n".join(out))
print("AUDIT DONE ->", p)
