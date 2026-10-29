import paramiko, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\fw_diff2_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20, banner_timeout=20, auth_timeout=20)
cmd = (
    "for V in v15 v16; do "
    "awk '/^P:/{p=$0} /^V:/{print p, $0}' /tmp/x$V/lib/apk/db/installed | sort > /tmp/pkgs_$V; "
    "done; "
    "echo '=== 包版本差异（P 行相同但 V 不同/增删）==='; "
    "diff /tmp/pkgs_v15 /tmp/pkgs_v16; "
    "echo '=== header.ut diff ==='; "
    "diff /tmp/xv15/usr/share/ucode/luci/template/header.ut /tmp/xv16/usr/share/ucode/luci/template/header.ut | head -40; "
    "echo '=== version.uc diff ==='; "
    "diff /tmp/xv15/usr/share/ucode/luci/version.uc /tmp/xv16/usr/share/ucode/luci/version.uc | head -20"
)
i, o, e = c.exec_command(cmd, timeout=120)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
