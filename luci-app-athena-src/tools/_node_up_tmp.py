import paramiko, traceback, os
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    sftp = c.open_sftp()
    src = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_node-v22.23.2-linux-x64.tar.gz"
    dst = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/dl/node-v22.23.2-linux-x64.tar.gz"
    sftp.put(src, dst)
    sftp.close()
    stdin, stdout, stderr = c.exec_command("ls -la " + dst)
    out.append(stdout.read().decode("utf-8", "replace").strip())
    stdin, stdout, stderr = c.exec_command("cd /home/vboxuser/jdc-build/immortalwrt_ipq-main && echo 'b294a556e639d64338823920e5866c21c02741742d2e1529ee1a225c1ec9252a  node-v22.23.2-linux-x64.tar.gz' | sha256sum -c -")
    out.append("=== 校验 ===\n" + stdout.read().decode("utf-8", "replace").strip())
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_node_up13.txt","w",encoding="utf-8").write("\n".join(out))
