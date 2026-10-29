# -*- coding: utf-8 -*-
import io, os, re, subprocess, sys

preview = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output\preview\preview-v1.2.0.html"
with io.open(preview, "r", encoding="utf-8") as f:
    html = f.read()

# extract the injected preview script (last <script> block)
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
inj = scripts[-1]
tmp = os.path.join(os.path.dirname(preview), "_preview_check.js")
with io.open(tmp, "w", encoding="utf-8") as f:
    f.write(inj)

r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
print("node --check:", r.returncode)
print(r.stderr.strip()[:500] if r.returncode else "OK - injected script syntax valid")
os.remove(tmp)

# also check the whole file's own script blocks for basic balance (informational)
total_scripts = len(scripts)
print("script blocks:", total_scripts)
