import paramiko, io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\uci_def_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ok = False
for i in range(20):
    try:
        c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=10, banner_timeout=10, auth_timeout=10)
        ok = True
        break
    except Exception:
        time.sleep(4)
if not ok:
    with open(out, "w", encoding="utf-8") as f:
        f.write("SSH NOT READY")
    print("done")
    sys.exit(0)
# v1.2.16 固件在 VM 上？之前解包过 /tmp/fwv16。若 VM 重启后没了，先查 /tmp 或 bin 目录
cmd = "ls /tmp/xv16/etc/uci-defaults/ 2>/dev/null; echo ===; ls ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx/*squashfs-sysupgrade.bin 2>/dev/null; echo ===; ls /tmp/fwv16/etc/uci-defaults/ 2>/dev/null"
i, o, e = c.exec_command(cmd, timeout=30)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
