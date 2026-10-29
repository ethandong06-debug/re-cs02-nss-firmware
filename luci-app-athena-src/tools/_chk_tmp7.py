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
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1800:]))
    run("ls -la %s/staging_dir/host/bin/node* 2>/dev/null | head -3" % base, "host node 是否已编译")
    run("ps --ppid 1302017 -o pid,etime,cmd 2>/dev/null | head -6", "新 make 的子进程")
    run("ls -la %s/dl/node-v22* 2>/dev/null; ls %s/build_dir/host/node*/.built %s/build_dir/host/node*/.hostbuilt 2>/dev/null" % (base, base, base), "node 下载与 stamp")
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_chk13f.txt","w",encoding="utf-8").write("\n".join(out))
