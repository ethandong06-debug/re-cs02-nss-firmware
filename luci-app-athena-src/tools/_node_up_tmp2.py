import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=60):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-1200:]))
    run("echo 'b294a556e639d64338823920e5866c21c02741742d2e1529ee1a225c1ec9252a  /home/vboxuser/jdc-build/immortalwrt_ipq-main/dl/node-v22.23.2-linux-x64.tar.gz' | sha256sum -c -", "VM 内校验 node 包", 30)
    run("rm -f %s/dl/node-v22.23.2-linux-x64.tar.gz.dl %s/dl/node-v22.23.2-linux-x64.tar.gz.hash; ps aux | grep -E 'make|download' | grep -v grep | wc -l" % (base, base), "清理半成品+确认无残留进程", 30)
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_node_up13.txt","w",encoding="utf-8").write("\n".join(out))
