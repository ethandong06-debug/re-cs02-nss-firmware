import paramiko, io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\build_check_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ok = False
for i in range(12):
    try:
        c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=10, banner_timeout=10, auth_timeout=10)
        ok = True
        break
    except Exception:
        time.sleep(3)
if not ok:
    with open(out, "w", encoding="utf-8") as f:
        f.write("SSH NOT READY")
    print("done")
    sys.exit(0)
cmd = "date '+%H:%M:%S'; ps aux | grep -E 'make|cc1|gcc|ld ' | grep -v grep | wc -l; cat /proc/loadavg; ls -l --time-style='+%H:%M:%S' ~/jdc-build/immortalwrt_ipq-main/bin/targets/qualcommax/ipq60xx/*squashfs-*bin 2>/dev/null"
i, o, e = c.exec_command(cmd, timeout=30)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
