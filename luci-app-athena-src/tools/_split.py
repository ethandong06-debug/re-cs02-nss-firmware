# -*- coding: utf-8 -*-
import os, json, sys

ROOT = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt"

def emit(rel_paths, outpath):
    files = []
    for rel in rel_paths:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        with open(p, "rb") as f:
            raw = f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        files.append({"path": rel, "content": content})
    # write pretty-printed, one file per line-ish: keep compact but parseable
    with open(outpath, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i, it in enumerate(files):
            f.write(json.dumps(it, ensure_ascii=False))
            f.write(",\n" if i < len(files)-1 else "\n")
        f.write("]\n")
    print(outpath, len(files), "files")

import glob
# collect all libexec files in root
libexec_dir = os.path.join(ROOT, "frontend/luci-app-athena/root/usr/libexec")
scripts = sorted(os.listdir(libexec_dir))
# exclude legacy/bak
scripts = [s for s in scripts if "legacy" not in s and ".bak" not in s]
rels = ["frontend/luci-app-athena/root/usr/libexec/" + s for s in scripts]
print("total libexec:", len(scripts), scripts)

# split into batches of 6
for i in range(0, len(rels), 6):
    batch = rels[i:i+6]
    emit(batch, os.path.join(os.environ["TEMP"], f"g1_{i//6}.json"))
