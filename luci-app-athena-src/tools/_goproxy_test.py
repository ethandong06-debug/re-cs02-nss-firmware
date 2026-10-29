import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
i, o, e = c.exec_command("curl -s -o /dev/null -w '%{http_code} %{size_download}' --connect-timeout 8 https://mirrors.aliyun.com/goproxy/github.com/gin-gonic/gin/@v/v1.10.0.mod; echo; curl -s -o /dev/null -w '%{http_code} %{size_download}' --connect-timeout 8 https://goproxy.cn/github.com/gin-gonic/gin/@v/v1.10.0.mod")
out.append("=== 模块可达性 ===\n" + o.read().decode("utf-8", "replace").strip())
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_goproxy_test.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
