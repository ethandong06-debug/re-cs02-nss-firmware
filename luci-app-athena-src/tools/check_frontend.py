import re

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
h = open(p, encoding="utf-8").read()
print("html bytes:", len(h))
print("script open/close:", h.count("<script"), h.count("</script>"))

# 提取内嵌 JS 做基本语法检查（用简单括号配对）
scripts = re.findall(r"<script[^>]*>(.*?)</script>", h, re.S)
print("inline scripts:", len(scripts))
for i, s in enumerate(scripts):
    if not s.strip():
        continue
    # 括号/引号粗检
    for ch_open, ch_close, name in [("(", ")", "()"), ("{", "}", "{}"), ("[", "]", "[]")]:
        if s.count(ch_open) != s.count(ch_close):
            print(f"  script[{i}] unbalanced {name}: {s.count(ch_open)} vs {s.count(ch_close)}")
    if s.count('"') % 2 != 0:
        print(f"  script[{i}] odd double quotes")
print("basic scan done")

# 检查新增函数是否都存在
for fn in ["openNativeLuCI", "appAlias", "loadActiveApps", "renderActiveApps", "appIconFor", "svcRowHTML", "renderSvcBox"]:
    print(fn, "->", "OK" if fn in h else "MISSING")
for marker in ["svc-group-t", "appCard", "appBox", "appSub", "APP_ALIASES", "DNS 指纹", "ACTIVE_APPS"]:
    print(marker, "->", "OK" if marker in h else "MISSING")
