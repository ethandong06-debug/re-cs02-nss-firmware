import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
i, o, e = c.exec_command("curl -s -o /dev/null -w '%{http_code}' --connect-timeout 6 http://10.0.2.2:8899/github.com/gin-gonic/gin/@latest; echo; ip route | head -2")
out.append("=== VM 到宿主代理 ===\n" + o.read().decode("utf-8", "replace").strip())
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_vm_proxy_test.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
