# -*- coding: utf-8 -*-
import io, os

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
out = []
for fn in ["athena-wireless.sh", "athena-speedtest.sh", "athena-resources.sh"]:
    p = os.path.join(base, fn)
    with io.open(p, encoding="utf-8") as f:
        txt = f.read()
    out.append("==== %s (%d bytes) ====" % (fn, len(txt)))
    out.append(txt[:2000])
    out.append("")

with io.open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_srcdump.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done")
