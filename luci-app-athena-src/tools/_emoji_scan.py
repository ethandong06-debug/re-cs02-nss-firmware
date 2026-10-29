# -*- coding: utf-8 -*-
"""Scan all emoji icons in index.html with surrounding text context."""
import io, re

src = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
with io.open(src, "r", encoding="utf-8") as f:
    html = f.read()

# strip <style> blocks to avoid CSS noise
html_no_style = re.sub(r"<style>.*?</style>", "", html, flags=re.S)

emoji_pat = re.compile(
    u"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]"
)

seen = []
for m in emoji_pat.finditer(html_no_style):
    em = m.group(0)
    start = max(0, m.start() - 80)
    end = min(len(html_no_style), m.end() + 120)
    ctx = html_no_style[start:end].replace("\n", " ").replace("\r", "")
    seen.append((em, ctx))

lines = []
for i, (em, ctx) in enumerate(seen):
    lines.append("%02d [%s] ...%s..." % (i, em, ctx))

outp = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_emoji_scan.txt"
with io.open(outp, "w", encoding="utf-8") as f:
    f.write("total emoji occurrences: %d\n\n" % len(seen))
    f.write("\n".join(lines))
print("total:", len(seen))
