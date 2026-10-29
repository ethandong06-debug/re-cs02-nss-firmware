import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=30):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1500:]))
    run("ps -ef --forest | grep -A4 'package/feeds/packages/node' | head -14", "node 编译进程树")
    run("ls -la %s/build_dir/host/node-*/ 2>/dev/null | head -5; ls -la %s/build_dir/host/node-*/.built %s/build_dir/host/node-*/.configured* 2>/dev/null" % (base, base, base), "node host 构建目录状态")
    run("ls -la %s/tmp/.node*flock 2>/dev/null" % base, "node 锁")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_chk13j.txt","w",encoding="utf-8").write("\n".join(out))
