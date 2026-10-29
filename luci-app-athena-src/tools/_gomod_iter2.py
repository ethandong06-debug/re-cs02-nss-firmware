# -*- coding: utf-8 -*-
"""Ensure go.mod has x/net v0.42.0 indirect, rerun iterative filebrowser build."""
import paramiko, urllib.request, os, re, sys, time

HOST, PORT, USER, PASS = "127.0.0.1", 2222, "vboxuser", "vboxuser"
BASE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
GOMOD = BASE + "/build_dir/target-aarch64_cortex-a53_musl/filebrowser-2.43.0/go.mod"
LOCAL_BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download"
REMOTE_BASE = BASE + "/dl/go-mod-cache/cache/download"

def run_ssh(cmd, t=300):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    i, o, e = c.exec_command(cmd, timeout=t)
    data = o.read().decode("utf-8", "replace")
    c.close()
    return data

def esc(mod):
    return re.sub(r'[A-Z]', lambda x: '!' + x.group(0).lower(), mod)

# 1) set x/net to v0.42.0 in go.mod
r = run_ssh("grep -n 'golang.org/x/net ' " + GOMOD)
print("=== 当前 go.mod x/net ===")
print(r.strip() or "(无)")

if "x/net v0.42.0" in r:
    print("already v0.42.0")
elif "golang.org/x/net" in r:
    run_ssh("sed -i 's|golang.org/x/net v0.40.0 // indirect|golang.org/x/net v0.42.0 // indirect|' " + GOMOD)
    print("updated 0.40->0.42")
else:
    run_ssh("sed -i '/golang.org\\/x\\/image/a\\\\tgolang.org/x/net v0.42.0 // indirect' " + GOMOD)
    print("added v0.42.0")
print(run_ssh("grep -nE 'golang.org/x/(net|crypto|image|text)' " + GOMOD).strip())

# 2) ensure x/net v0.42.0 in local+remote (already on remote per prior listing; ensure local)
em = esc("golang.org/x/net")
vdir = os.path.join(LOCAL_BASE, em, "@v")
os.makedirs(vdir, exist_ok=True)
for ext in (".info", ".mod", ".zip"):
    fp = os.path.join(vdir, "v0.42.0" + ext)
    if not (os.path.exists(fp) and os.path.getsize(fp) > 0):
        try:
            req = urllib.request.Request("https://goproxy.cn/" + em + "/@v/v0.42.0" + ext, headers={"User-Agent": "go"})
            with urllib.request.urlopen(req, timeout=120) as r:
                with open(fp, "wb") as f:
                    f.write(r.read())
        except Exception as ex:
            print("fetch fail", ext, ex)

# 3) iterative build (same loop as _gomod_iter.py but starting fresh)
missing_pat = re.compile(r"([a-zA-Z0-9_.\-/!]+)@v([0-9][a-zA-Z0-9.\-+]*): module lookup disabled")

for attempt in range(1, 41):
    print("=== attempt %d ===" % attempt, flush=True)
    tail = run_ssh(
        "cd %s && export GOPROXY=off GOSUMDB=off GOFLAGS=-mod=mod && make package/feeds/packages/filebrowser/compile V=s 2>&1 | tail -50" % BASE, t=420)[-3500:]
    if "ERROR: package" not in tail and "Error 1" not in tail and ".built" in tail:
        print("BUILD OK")
        break
    if "ERROR: package" not in tail and "failed" not in tail and "module lookup" not in tail:
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
        em2 = esc(m)
        vd = os.path.join(LOCAL_BASE, em2, "@v")
        os.makedirs(vd, exist_ok=True)
        got = 0
        for ext in (".info", ".mod", ".zip"):
            fp = os.path.join(vd, v + ext)
            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                got += 1
                continue
            try:
                req = urllib.request.Request("https://goproxy.cn/" + em2 + "/@v/" + v + ext, headers={"User-Agent": "go"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                if data and len(data) > 10:
                    with open(fp, "wb") as f:
                        f.write(data)
                    got += 1
                else:
                    print("  empty", m, v, ext)
            except Exception as ex:
                print("  fail", m, v, ext, ex)
        if got:
            # upload via cat
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
            c.exec_command("mkdir -p " + REMOTE_BASE + "/" + em2 + "/@v")
            for ext in (".info", ".mod", ".zip"):
                fp = os.path.join(vd, v + ext)
                if not os.path.exists(fp):
                    continue
                stdin, stdout, stderr = c.exec_command("cat > " + REMOTE_BASE + "/" + em2 + "/@v/" + v + ext)
                with open(fp, "rb") as fh:
                    stdin.write(fh.read())
                stdin.channel.shutdown_write()
                stdout.read()
            c.close()
            print("  uploaded", m, v, flush=True)
        else:
            print("  !! cannot obtain", m, v, flush=True)
    time.sleep(1)

print("=== done ===")
