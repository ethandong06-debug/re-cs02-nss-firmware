# -*- coding: utf-8 -*-
"""v1.2.56 交付前校验：三段 JS 语法、ACL JSON 合法且含 prefs、三个文件大小/哈希。"""
import io, re, os, json, subprocess, hashlib

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"
P = base + r"\htdocs\luci-static\resources\view\athena\index.html"
A = base + r"\root\usr\share\rpcd\acl.d\luci-app-athena.json"
L = base + r"\root\usr\libexec\athena-logcap.sh"

s = io.open(P, encoding="utf-8").read()
blocks = re.findall(r"<script>(.*?)</script>", s, re.S)
print("blocks:", len(blocks), [len(b) for b in blocks])
for i, b in enumerate(blocks):
    t = os.path.join(os.environ["TEMP"], f"_c56_{i}.js")
    io.open(t, "w", encoding="utf-8").write(b)
    r = subprocess.run(["node", "--check", t], capture_output=True, text=True, shell=True)
    print(f"  block{i}: rc={r.returncode} {r.stderr.strip()[:200]}")

d = json.loads(io.open(A, encoding="utf-8").read())
files = d["luci-app-athena"]["write"]["file"]
print("ACL prefs:", files.get("/usr/libexec/athena-prefs.sh"))
print("ACL 条目数:", len(files))

for p in (P, A, L):
    raw = io.open(p, "rb").read()
    print(os.path.basename(p), len(raw), hashlib.sha256(raw).hexdigest())

print("exec-rc6 处理:", "OK" if "执行权限不足" in s else "缺失")
print("logcap CAP:", [l for l in io.open(L, encoding="utf-8").read().splitlines() if l.startswith("CAP=")])
print("JSON-VALID OK")
