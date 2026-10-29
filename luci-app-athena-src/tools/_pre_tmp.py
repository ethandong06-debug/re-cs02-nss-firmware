import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    stdin, stdout, stderr = c.exec_command("ps aux | grep -E 'make|download|curl' | grep -v grep | wc -l")
    n = stdout.read().decode("utf-8", "replace").strip()
    out.append("残留进程数: " + n)
    stdin, stdout, stderr = c.exec_command("ls -la /home/vboxuser/jdc-build/immortalwrt_ipq-main/dl/node-v22.23.2.tar.gz /home/vboxuser/jdc-build/immortalwrt_ipq-main/dl/node-v22.23.2-linux-x64.tar.gz")
    out.append(stdout.read().decode("utf-8", "replace").strip())
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_pre13.txt","w",encoding="utf-8").write("\n".join(out))
