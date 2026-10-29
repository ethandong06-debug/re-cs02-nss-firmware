# -*- coding: utf-8 -*-
"""Upload old x/net files, rerun iterative build."""
import paramiko, os, re, time

HOST, PORT, USER, PASS = "127.0.0.1", 2222, "vboxuser", "vboxuser"
BASE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download\golang.org\x\net\@v"
REMOTE_DIR = BASE + "/dl/go-mod-cache/cache/download/golang.org/x/net/@v"

def run_ssh(cmd, t=300):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    i, o, e = c.exec_command(cmd, timeout=t)
    data = o.read().decode("utf-8", "replace")
    c.close()
    return data

# upload old x/net via cat
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
c.exec_command("mkdir -p " + REMOTE_DIR)
for f in os.listdir(LOCAL):
    if f.startswith("v0.0.0-20191105084925"):
        stdin, stdout, stderr = c.exec_command("cat > " + REMOTE_DIR + "/" + f)
        with open(os.path.join(LOCAL, f), "rb") as fh:
            stdin.write(fh.read())
        stdin.channel.shutdown_write()
        stdout.read()
        print("uploaded", f)
c.close()
print(run_ssh("ls -la " + REMOTE_DIR + " | grep 2019").strip())

missing_pat = re.compile(r"([a-zA-Z0-9_.\-/!]+)@v([0-9][a-zA-Z0-9.\-+]*): module lookup disabled")

for attempt in range(1, 31):
    print("=== attempt %d ===" % attempt, flush=True)
    tail = run_ssh(
        "cd %s && export GOPROXY=off GOSUMDB=off GOFLAGS=-mod=mod && make package/feeds/packages/filebrowser/compile V=s 2>&1 | tail -50" % BASE, t=420)[-3500:]
    if "ERROR: package" not in tail and "Error 1" not in tail and ".built" in tail:
        print("BUILD OK")
        break
    if "module lookup" not in tail and "ERROR: package" not in tail:
        print("UNKNOWN:", tail[-500:])
        break
    missing = set()
    for line in tail.splitlines():
        mm = missing_pat.search(line)
        if mm:
            missing.add((mm.group(1).replace("!", ""), mm.group(2)))
    if not missing:
        print("NO MISSING:", tail[-600:])
        break
    print("missing:", missing, flush=True)
    for m, v in missing:
        em = re.sub(r'[A-Z]', lambda x: '!' + x.group(0).lower(), m)
        vd = os.path.join(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download", em, "@v")
        os.makedirs(vd, exist_ok=True)
        got = 0
        for ext in (".info", ".mod", ".zip"):
            fp = os.path.join(vd, v + ext)
            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                got += 1
                continue
            for src in ("https://goproxy.io/%s/@v/%s%s", "https://goproxy.cn/%s/@v/%s%s"):
                try:
                    req = urllib.request.Request(src % (em, v, ext), headers={"User-Agent": "go"})
                    with urllib.request.urlopen(req, timeout=90) as r:
                        data = r.read()
                    if data and len(data) > 10:
                        with open(fp, "wb") as f:
                            f.write(data)
                        got += 1
                    break
                except Exception:
                    continue
        if got:
            cc = paramiko.SSHClient()
            cc.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cc.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
            cc.exec_command("mkdir -p " + REMOTE_DIR.replace("/golang.org/x/net/@v", "/" + em + "/@v"))
            for ext in (".info", ".mod", ".zip"):
                fp = os.path.join(vd, v + ext)
                if not os.path.exists(fp):
                    continue
                stdin, stdout, stderr = cc.exec_command("cat > " + REMOTE_DIR.replace("/golang.org/x/net/@v", "/" + em + "/@v") + "/" + v + ext)
                with open(fp, "rb") as fh:
                    stdin.write(fh.read())
                stdin.channel.shutdown_write()
                stdout.read()
            cc.close()
            print("  uploaded", m, v, flush=True)
        else:
            print("  !! cannot obtain", m, v, flush=True)
    time.sleep(1)
print("=== done ===")
