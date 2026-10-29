import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
i, o, e = c.exec_command("cat ~/.curlrc 2>/dev/null || echo 无curlrc; echo ---; env | grep -i -E 'proxy|curl' || echo 无环境代理")
out.append("=== curlrc/env ===\n" + o.read().decode("utf-8", "replace").strip())
i, o, e = c.exec_command("curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --connect-timeout 6 http://10.0.2.2:8899/github.com/gin-gonic/gin/@latest")
out.append("=== 绕过 curlrc 测宿主代理 ===\n" + o.read().decode("utf-8", "replace").strip())
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_curlrc_chk.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
