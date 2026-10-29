# -*- coding: utf-8 -*-
import os, json, sys

ROOT = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt"
EXCLUDE = [r"\output\\", r"\preview\\", r"\.workbuddy\\", "__pycache__", r"_gomodcache",
           r"_shots", r"\_backup\\", "_shots_single", r"_pkg54", "node_modules"]
out = []
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, ROOT)
        if any(x in rel for x in EXCLUDE):
            continue
        sz = os.path.getsize(p)
        if sz > 2 * 1024 * 1024:
            continue
        out.append((rel.replace("\\", "/"), sz))
out.sort()
print(len(out), "files,", sum(s for _, s in out) // 1024, "KB")
for r, s in out:
    print(f"{s:8d}  {r}")
