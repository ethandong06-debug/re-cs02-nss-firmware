import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    base = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
    def run(cmd, name, t=180):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        e = stderr.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s%s" % (name, o.strip()[-1500:], e.strip()[-500:]))
    run("cd %s/dl && curl -L -o node-v22.23.2-linux-x64.tar.gz --connect-timeout 10 --max-time 150 https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/v22.23.2/node-v22.23.2-linux-x64.tar.gz 2>&1 | tail -2; ls -la node-v22.23.2-linux-x64.tar.gz" % base, "清华镜像下载 node", 180)
    run("cd %s && echo 'b294a556e639d64338823920e5866c21c02741742d2e1529ee1a225c1ec9252a  node-v22.23.2-linux-x64.tar.gz' | sha256sum -c - ; ls -la dl/node-v22.23.2-linux-x64.tar.gz" % base, "校验 sha256", 60)
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_node13.txt","w",encoding="utf-8").write("\n".join(out))
