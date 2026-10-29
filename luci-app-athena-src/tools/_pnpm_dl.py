import urllib.request, hashlib, sys

urls = [
    "https://registry.npmmirror.com/pnpm/-/pnpm-11.22.0.tgz",
    "https://registry.npmjs.org/pnpm/-/pnpm-11.22.0.tgz",
]
dst = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_pnpm-11.22.0.tgz"
ok = False
for u in urls:
    print("try:", u, flush=True)
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as r, open(dst, "wb") as f:
            total = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
            print("downloaded:", total, flush=True)
        if total > 5000000:
            ok = True
            break
    except Exception as e:
        print("fail:", e, flush=True)
print("OK" if ok else "FAILED")
