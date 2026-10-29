# -*- coding: utf-8 -*-
import io, os

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
out = []

with io.open(os.path.join(base, "athena-resources.sh"), encoding="utf-8") as f:
    txt = f.read()
out.append("==== athena-resources.sh (tail) ====")
out.append(txt[1800:])
out.append("")

idx = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
with io.open(idx, encoding="utf-8") as f:
    html = f.read()

import re
# find process/res list rendering functions
for pat in ["function loadRes", "function renderRes", "resList", "procs", "进程"]:
    for m in re.finditer(re.escape(pat), html):
        s = max(0, m.start()-100); e = min(len(html), m.end()+400)
        ctx = html[s:e].replace("\n", " ")
        out.append("--- [%s] at %d ---" % (pat, m.start()))
        out.append(ctx)

with io.open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_res_dump.txt", "w", encoding="utf-8") as f:
    f.write("\n\n".join(out))
print("done")
