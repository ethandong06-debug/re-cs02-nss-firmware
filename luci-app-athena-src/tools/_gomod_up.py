# -*- coding: utf-8 -*-
"""Upload local gomodcache to VM dl/go-mod-cache via SFTP."""
import paramiko, os, stat

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache"
REMOTE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/dl/go-mod-cache"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=30)
sftp = c.open_sftp()

def mkdir_p(remote_dir):
    parts = remote_dir.strip("/").split("/")
    cur = ""
    for p_ in parts:
        cur += "/" + p_
        try:
            sftp.stat(cur)
        except IOError:
            sftp.mkdir(cur)

n = 0
for root, dirs, files in os.walk(LOCAL):
    rel = os.path.relpath(root, LOCAL)
    if rel == ".":
        rel = ""
    rdir = REMOTE + ("/" + rel.replace("\\", "/") if rel else "")
    mkdir_p(rdir)
    for f in files:
        lp = os.path.join(root, f)
        rp = rdir + "/" + f
        sftp.put(lp, rp)
        n += 1

# 校验统计
i, o, e = c.exec_command("find %s -type f | wc -l; du -sh %s" % (REMOTE, REMOTE))
print("uploaded:", n)
print(o.read().decode("utf-8", "replace").strip())

# 查 golang.mk 默认 GOPROXY
i, o, e = c.exec_command("grep -nE 'GOPROXY|GONOSUM|GOSUM' /home/vboxuser/jdc-build/immortalwrt_ipq-main/feeds/packages/lang/golang/golang-values.mk /home/vboxuser/jdc-build/immortalwrt_ipq-main/feeds/packages/lang/golang/golang-package.mk | head -10")
print("=== GOPROXY 默认设置 ===")
print(o.read().decode("utf-8", "replace").strip() or "(无)")
sftp.close()
c.close()
