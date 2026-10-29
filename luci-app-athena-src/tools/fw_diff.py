import paramiko, io, sys, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\fw_diff_out.txt"
c = None
for i in range(40):
    try:
        c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=10, banner_timeout=10, auth_timeout=10)
        i2, o2, e2 = c.exec_command("echo READY", timeout=10)
        o2.read()
        break
    except Exception:
        time.sleep(3)
if c is None:
    with open(out, "w", encoding="utf-8") as f:
        f.write("VM NOT READY")
    print("done")
    sys.exit(0)
# 解包两个版本固件：v1.2.15 需先从本地传上去？不，用 VM 上历史产物不可靠——直接把本地两个 bin 上传
sftp = c.open_sftp()
local = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\output"
v15 = os.path.join(local, "AthenaWrt-v1.2.15-jdcloud_re-cs-02-sysupgrade.bin")
v16 = os.path.join(local, "AthenaWrt-v1.2.16-jdcloud_re-cs-02-sysupgrade.bin")
if os.path.exists(v15) and os.path.exists(v16):
    sftp.put(v15, "/tmp/v15.bin")
    sftp.put(v16, "/tmp/v16.bin")
    print("uploaded both")
sftp.close()
cmd = (
    "for V in v15 v16; do "
    "F=/tmp/$V.bin; OFF=$(grep -abo 'hsqs' $F | head -1 | cut -d: -f1); "
    "dd if=$F of=/tmp/$V.sq bs=1 skip=$OFF 2>/dev/null; "
    "rm -rf /tmp/x$V; unsquashfs -d /tmp/x$V /tmp/$V.sq >/dev/null 2>&1; "
    "done; "
    "diff -rq /tmp/xv15 /tmp/xv16 2>/dev/null | sort | head -60"
)
i, o, e = c.exec_command(cmd, timeout=300)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
