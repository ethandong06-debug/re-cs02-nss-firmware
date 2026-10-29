# -*- coding: utf-8 -*-
"""提取 index.html 三段 <script> 做 node --check，并打印文件大小/哈希。"""
import io, re, subprocess, os, hashlib

P = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\htdocs\luci-static\resources\view\athena\index.html"
s = io.open(P, encoding="utf-8").read()

blocks = re.findall(r"<script>(.*?)</script>", s, re.S)
print("script blocks:", len(blocks), [len(b) for b in blocks])
ok = True
for i, b in enumerate(blocks):
    tmp = os.path.join(os.environ["TEMP"], f"_chk{i}.js")
    io.open(tmp, "w", encoding="utf-8").write(b)
    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, shell=True)
    print(f"block{i}: rc={r.returncode} {r.stderr.strip()[:300]}")
    if r.returncode:
        ok = False
raw = io.open(P, "rb").read()
print("bytes", len(raw), "sha256", hashlib.sha256(raw).hexdigest())
print("NODECHECK", "OK" if ok else "FAIL")
