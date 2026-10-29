# -*- coding: utf-8 -*-
"""Patch filebrowser go.mod (add x/net indirect), ensure cache has x/net v0.40.0, rerun iterative build."""
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

# 1) patch go.mod: add x/net v0.40.0 // indirect after golang.org/x/image line
out = []
i, o = None, run_ssh("grep -n 'golang.org/x/image' " + GOMOD)
out.append("=== x/image 行 ===\n" + o.strip())
patched = run_ssh(
    "grep -q 'golang.org/x/net ' " + GOMOD + " && echo already || "
    "(sed -i '/golang.org\\/x\\/image/a\\\\tgolang.org/x/net v0.40.0 // indirect' " + GOMOD + " && echo patched)")
out.append("=== patch ===\n" + patched.strip())
out.append("=== patch 后 x 段 ===\n" + run_ssh("grep -nE 'golang.org/x/(net|crypto|image|text)' " + GOMOD).strip())
out.append("=== go.sum x/net v0.40.0 ===\n" + (run_ssh("grep 'golang.org/x/net v0.40.0' " + BASE + "/build_dir/target-aarch64_cortex-a53_musl/filebrowser-2.43.0/go.sum").strip() or "(go.sum 无 v0.40.0)"))

# 2) ensure x/net v0.40.0 in cache (local + upload)
m, v = "golang.org/x/net", "v0.40.0"
em = esc(m)
vdir = os.path.join(LOCAL_BASE, em, "@v")
os.makedirs(vdir, exist_ok=True)
for ext in (".info", ".mod", ".zip"):
    fp = os.path.join(vdir, v + ext)
    if not (os.path.exists(fp) and os.path.getsize(fp) > 0):
        try:
            req = urllib.request.Request("https://goproxy.cn/" + em + "/@v/" + v + ext, headers={"User-Agent": "go"})
            with urllib.request.urlopen(req, timeout=120) as r:
                with open(fp, "wb") as f:
                    f.write(r.read())
        except Exception as ex:
            out.append("fetch fail " + ext + ": " + str(ex))
# upload
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
sftp = c.open_sftp()
for part in [em, em + "/@v"]:
    try:
        sftp.stat(REMOTE_BASE + "/" + part)
    except IOError:
        try:
            sftp.mkdir(REMOTE_BASE + "/" + part)
        except IOError:
            pass
for f in os.listdir(vdir):
    sftp.put(os.path.join(vdir, f), os.path.join(REMOTE_BASE, em, "@v", f))
sftp.close()
c.close()
out.append("=== x/net v0.40.0 已上传 ===")

with open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_patch_net.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
