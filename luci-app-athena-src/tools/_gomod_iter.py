# -*- coding: utf-8 -*-
"""Iterative: build filebrowser pkg -> parse missing module -> download from goproxy.cn -> upload -> retry."""
import paramiko, urllib.request, os, re, sys, time

HOST, PORT, USER, PASS = "127.0.0.1", 2222, "vboxuser", "vboxuser"
BASE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
LOCAL_BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download"
REMOTE_BASE = BASE + "/dl/go-mod-cache/cache/download"

def esc(mod):
    return re.sub(r'[A-Z]', lambda x: '!' + x.group(0).lower(), mod)

def run_ssh(cmd, t=300):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    i, o, e = c.exec_command(cmd, timeout=t)
    data = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    c.close()
    return data, err

def fetch_one(m, v):
    """download .info/.mod/.zip to local cache, return True on any success"""
    em = esc(m)
    vdir = os.path.join(LOCAL_BASE, em, "@v")
    os.makedirs(vdir, exist_ok=True)
    got = 0
    for ext in (".info", ".mod", ".zip"):
        fp = os.path.join(vdir, v + ext)
        if os.path.exists(fp) and os.path.getsize(fp) > 0:
            got += 1
            continue
        url = "https://goproxy.cn/" + em + "/@v/" + v + ext
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "go"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if b"404 page not found" not in data and len(data) > 0:
                with open(fp, "wb") as f:
                    f.write(data)
                got += 1
            else:
                print("  goproxy 404 for %s@%s%s" % (m, v, ext))
        except Exception as ex:
            print("  fetch fail %s@%s%s: %s" % (m, v, ext, ex))
    return got

def upload_dirs(m, v):
    em = esc(m)
    lp = os.path.join(LOCAL_BASE, em, "@v")
    rp = REMOTE_BASE + "/" + em + "/@v"
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    sftp = c.open_sftp()
    # mkdir -p
    for part in [em, em + "/@v"]:
        try:
            sftp.stat(REMOTE_BASE + "/" + part)
        except IOError:
            try:
                sftp.mkdir(REMOTE_BASE + "/" + part)
            except IOError:
                pass
    for f in os.listdir(lp):
        sftp.put(os.path.join(lp, f), os.path.join(rp, f))
    sftp.close()
    c.close()

missing_pat = re.compile(r"([a-zA-Z0-9_.\-/!]+)@v([0-9][a-zA-Z0-9.\-+]*): module lookup disabled")

for attempt in range(1, 41):
    print("=== attempt %d ===" % attempt, flush=True)
    data, err = run_ssh(
        "cd %s && export GOPROXY=off GOSUMDB=off GOFLAGS=-mod=mod && make package/feeds/packages/filebrowser/compile V=s 2>&1 | tail -60" % BASE, t=420)
    tail = (data or "")[-4000:]
    # success?
    if ".built" in tail and "ERROR: package" not in tail and "Error 1" not in tail:
        print("BUILD OK")
        break
    if "ERROR: package" not in tail and "Error 1" not in tail and "failed" not in tail:
        print("UNKNOWN STATE, tail:", tail[-800:])
        break
    # parse missing
    missing = set()
    for m_line in tail.splitlines():
        mm = missing_pat.search(m_line)
        if mm:
            missing.add((mm.group(1).replace("!", "").lower().replace("!", ""), mm.group(2)))
    # also generic "cannot find module providing package"
    for m_line in tail.splitlines():
        if "cannot find module providing package" in m_line:
            parts = m_line.strip().split()
            if len(parts) >= 4:
                # e.g. module lookup disabled by GOPROXY=off for X@vY  (other format)
                pass
    if not missing:
        print("NO MISSING PARSED, tail:", tail[-1000:])
        break
    print("missing:", missing, flush=True)
    for m, v in missing:
        got = fetch_one(m, v)
        if got:
            upload_dirs(m, v)
            print("  uploaded %s@%s (%d files)" % (m, v, got), flush=True)
        else:
            print("  !! cannot obtain %s@%s" % (m, v), flush=True)
    time.sleep(1)

print("=== done ===")
