import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
i, o, e = c.exec_command("env | grep -i proxy; echo ---; cat /etc/hosts | grep -v '^#' | head -20; echo ---; curl -s -o /dev/null -w '%{http_code}' --connect-timeout 6 https://goproxy.cn/github.com/gin-gonic/gin/@v/list")
out.append("=== 代理环境与 hosts ===\n" + o.read().decode("utf-8", "replace").strip())
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_proxy_chk.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
