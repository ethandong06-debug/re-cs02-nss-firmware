# -*- coding: utf-8 -*-
"""Step 1: fetch go.sum from VM, download all modules from goproxy.cn to local cache"""
import paramiko, urllib.request, os, re, sys, time

VM_SUM = None
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)
    i, o, e = c.exec_command(
        "cat /home/vboxuser/jdc-build/immortalwrt_ipq-main/build_dir/target-aarch64_cortex-a53_musl/filebrowser-2.43.0/go.sum")
    VM_SUM = o.read().decode("utf-8", "replace")
    c.close()
except Exception as ex:
    print("SSH fetch failed:", ex)
    sys.exit(1)

# parse module@version pairs
pairs = {}
for line in VM_SUM.splitlines():
    parts = line.split()
    if len(parts) >= 2:
        m, v = parts[0], parts[1]
        pairs[m + "@" + v] = (m, v)
print("total pairs:", len(pairs))

def esc(mod):
    return re.sub(r'[A-Z]', lambda x: '!' + x.group(0).lower(), mod)

BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download"
ok = 0
fail = []
for key, (m, v) in sorted(pairs.items()):
    em = esc(m)
    vdir = os.path.join(BASE, em, "@v")
    os.makedirs(vdir, exist_ok=True)
    for ext in (".info", ".mod", ".zip"):
        fp = os.path.join(vdir, v + ext)
        if os.path.exists(fp) and os.path.getsize(fp) > 0:
            ok += 1
            continue
        url = "https://goproxy.cn/" + em + "/@v/" + v + ext
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "go"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            with open(fp, "wb") as f:
                f.write(data)
            ok += 1
        except Exception as ex:
            fail.append((key, ext, str(ex)))
    time.sleep(0.05)

print("files ok:", ok, "fail:", len(fail))
for f_ in fail[:20]:
    print("FAIL", f_)
with open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomod_dl_result.txt", "w", encoding="utf-8") as f:
    f.write("ok=%d fail=%d\n" % (ok, len(fail)))
    for x in fail:
        f.write("%s %s %s\n" % x)
