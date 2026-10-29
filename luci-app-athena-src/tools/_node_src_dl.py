import urllib.request, hashlib
urls = [
  "https://npmmirror.com/mirrors/node/v22.23.2/node-v22.23.2.tar.gz",
  "https://mirrors.huaweicloud.com/nodejs/v22.23.2/node-v22.23.2.tar.gz",
  "https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/v22.23.2/node-v22.23.2.tar.gz",
  "https://mirrors.tencent.com/nodejs-release/v22.23.2/node-v22.23.2.tar.gz",
]
dst = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_node-src.tar.gz"
exp = "cdaed46fcd8923a55974b7bbc7caaadeaaf7aed60cc137e59837b72f575ef641"
ok = False
for u in urls:
    print("try:", u, flush=True)
    try:
        req = urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as r, open(dst,"wb") as f:
            total = 0
            while True:
                chunk = r.read(1<<20)
                if not chunk: break
                f.write(chunk); total += len(chunk)
            print("downloaded:", total, flush=True)
        if total > 30000000:
            ok = True; break
    except Exception as e:
        print("fail:", e, flush=True)
if ok:
    h = hashlib.sha256(open(dst,"rb").read()).hexdigest()
    print("sha256:", h)
    print("MATCH" if h == exp else "MISMATCH")
else:
    print("ALL FAILED")
