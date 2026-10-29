# -*- coding: utf-8 -*-
import io, os, re, subprocess

preview = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output\preview\preview-v1.2.0.html"
tmp = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output\preview\_preview_check.js"
outp = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_preview_chk.txt"

with io.open(preview, "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
lines = ["script blocks: %d" % len(scripts)]
for i, s in enumerate(scripts):
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(s)
    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
    lines.append("block %d: returncode=%d %s" % (i, r.returncode, r.stderr.strip()[:300]))

with io.open(outp, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
