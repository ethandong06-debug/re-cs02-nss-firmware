# -*- coding: utf-8 -*-
"""Upload x/net v0.40.0 via exec cat; diagnose remote dir first."""
import paramiko, os

HOST, PORT, USER, PASS = "127.0.0.1", 2222, "vboxuser", "vboxuser"
BASE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download\golang.org\x\net\@v"
REMOTE_DIR = BASE + "/dl/go-mod-cache/cache/download/golang.org/x/net/@v"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)

i, o, e = c.exec_command("ls -la " + REMOTE_DIR + " 2>&1 | head -8")
print("=== 远程目录现状 ===")
print(o.read().decode("utf-8", "replace").strip())

print("=== 本地文件 ===")
for f in os.listdir(LOCAL):
    print(f, os.path.getsize(os.path.join(LOCAL, f)))

for f in os.listdir(LOCAL):
    lp = os.path.join(LOCAL, f)
    rp = REMOTE_DIR + "/" + f
    with open(lp, "rb") as fh:
        data = fh.read()
    stdin, stdout, stderr = c.exec_command("cat > " + rp)
    stdin.write(data)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    print("write", f, "ok" if not err.strip() else err.strip())

i, o, e = c.exec_command("ls -la " + REMOTE_DIR + " | head -8")
print("=== 上传后 ===")
print(o.read().decode("utf-8", "replace").strip())
c.close()
