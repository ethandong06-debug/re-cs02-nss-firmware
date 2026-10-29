import paramiko, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\fw_diff3_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)
cmd = (
    "echo '=== scripts.tar.gz 包脚本清单差异 ==='; "
    "cd /tmp; rm -rf s15 s16; mkdir s15 s16; "
    "tar -tzf /tmp/xv15/lib/apk/db/scripts.tar.gz > /tmp/s15.list 2>/dev/null; "
    "tar -tzf /tmp/xv16/lib/apk/db/scripts.tar.gz > /tmp/s16.list 2>/dev/null; "
    "diff /tmp/s15.list /tmp/s16.list; "
    "echo '=== installed 完整包版本 diff（所有行）==='; "
    "diff /tmp/xv15/lib/apk/db/installed /tmp/xv16/lib/apk/db/installed | head -80"
)
i, o, e = c.exec_command(cmd, timeout=120)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
