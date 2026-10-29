import paramiko, traceback, os
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=30):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1000:]))
    run("ps aux | grep -E 'make|node|filebrowser|go' | grep -v grep | head -8", "编译任务")
    run("ls -la %s/staging_dir/host/bin/node 2>/dev/null | head -2" % base, "host node")
    run("ls -lt %s/bin/targets/qualcommax/ipq60xx/*.bin 2>/dev/null | head -2" % base, "固件")
    c.close()
except Exception as e:
    out.append("ERR: " + traceback.format_exc())
p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_chk13m.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
    f.flush()
    os.fsync(f.fileno())
