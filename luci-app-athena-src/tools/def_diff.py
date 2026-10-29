import paramiko, io, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
out = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\def_diff_out.txt"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for i in range(12):
    try:
        c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=10, banner_timeout=10, auth_timeout=10)
        break
    except Exception:
        time.sleep(3)
cmd = ("echo '===V15 FULL LIST==='; ls /tmp/fwv15/etc/uci-defaults/ 2>/dev/null; "
       "echo; echo '===V17 FULL LIST==='; ls /tmp/fwv17u/etc/uci-defaults/ 2>/dev/null; "
       "echo; echo '===ONLY IN V17 (new at v1.2.16)==='; "
       "comm -13 <(ls /tmp/fwv15/etc/uci-defaults/ 2>/dev/null | sort) <(ls /tmp/fwv17u/etc/uci-defaults/ 2>/dev/null | sort); "
       "echo; echo '===ONLY IN V15==='; "
       "comm -23 <(ls /tmp/fwv15/etc/uci-defaults/ 2>/dev/null | sort) <(ls /tmp/fwv17u/etc/uci-defaults/ 2>/dev/null | sort); "
       "echo; echo '===SAME-NAME DIFF==='; "
       "for f in $(comm -12 <(ls /tmp/fwv15/etc/uci-defaults/ 2>/dev/null | sort) <(ls /tmp/fwv17u/etc/uci-defaults/ 2>/dev/null | sort)); do "
       "  if ! diff -q /tmp/fwv15/etc/uci-defaults/$f /tmp/fwv17u/etc/uci-defaults/$f >/dev/null 2>&1; then echo \"CHANGED: $f\"; fi; "
       "done")
i, o, e = c.exec_command(cmd, timeout=60)
data = o.read().decode("utf-8", "replace")
c.close()
with open(out, "w", encoding="utf-8") as f:
    f.write(data)
print("done")
