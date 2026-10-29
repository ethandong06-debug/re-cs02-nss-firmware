# -*- coding: utf-8 -*-
"""修正 OAF 映射表里的 id 重号：同一 id 被多个不同应用占用时，只保留首个占用者，
其余置空（前端按 id 取图标，重号会让 Amazon 显示淘宝图标之类）。"""
import io, json, shutil, os

P = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\share\athena\oaf-app-map.json"
BAK = P + ".pre-dedup.bak"

raw = io.open(P, encoding="utf-8").read()
d = json.loads(raw)
shutil.copyfile(P, BAK)

owner = {}
fixed = []
for key, val in d.items():
    i = val.get("id", "")
    if not i:
        fixed.append((key, val.get("name", ""), "空 id 保持不变"))
        continue
    if i not in owner:
        owner[i] = (key, val.get("name", ""))
    else:
        okey, oname = owner[i]
        if oname != val.get("name", ""):
            val["id"] = ""
            fixed.append((key, val.get("name", ""), "id=%s 已被 %s(%s) 占用 → 置空" % (i, oname, okey)))
        else:
            fixed.append((key, val.get("name", ""), "id=%s 同名(%s) 保留" % (i, oname)))

out = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
io.open(P, "w", encoding="utf-8", newline="").write(out)

print("entries:", len(d), "bytes:", len(out.encode("utf-8")))
for k, n, why in fixed:
    print("  %-32s %-16s %s" % (k, n, why))
