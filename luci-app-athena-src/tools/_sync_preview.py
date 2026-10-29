# -*- coding: utf-8 -*-
"""把最新 index.html 同步进静态预览稿（保留原有 Mock 数据块）。"""
import io, os

BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt"
IDX = BASE + r"\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
PV = BASE + r"\preview\AthenaWrt-全站v5.html"
BAK = BASE + r"\preview\AthenaWrt-全站v5-v1.2.39-同步前备份.html"
ANCHOR = "window.doLogin=doLogin;"

pv = io.open(PV, encoding="utf-8").read()
lines = pv.split("\n")
start = next(i for i, l in enumerate(lines) if l.startswith("/* ===== 静态预览 Mock"))
# 块结束标记：try{ boot(); } 那一行
end = next(i for i, l in enumerate(lines) if "try{ boot(); }catch(e)" in l)
block = "\n".join(lines[start:end + 1])
assert "var _MOCK=" in block, "mock 块解析失败"

io.open(BAK, "w", encoding="utf-8", newline="").write(pv)

idx = io.open(IDX, encoding="utf-8").read()
assert idx.count(ANCHOR) == 1, "锚点不唯一: %d" % idx.count(ANCHOR)
i = idx.index(ANCHOR) + len(ANCHOR)
out = idx[:i] + "\n" + block + idx[i:]

io.open(PV, "w", encoding="utf-8", newline="").write(out)

checks = ["var _MOCK=", "doFlashConfirm", "_localSha", "hashFile", "},10000);", "loadActiveApps(); },120000)", "athena-fw-upload.bin", "cgi-upload"]
print("preview bytes:", len(out.encode("utf-8")))
for c in checks:
    print("  %-34s %s" % (c, c in out))
print("mock block lines:", block.count("\n") + 1)
