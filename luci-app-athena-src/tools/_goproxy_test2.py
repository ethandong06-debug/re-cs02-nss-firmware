import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

urls = [
    "https://mirrors.aliyun.com/goproxy/github.com/gin-gonic/gin/@latest",
    "https://goproxy.cn/github.com/gin-gonic/gin/@latest",
    "https://goproxy.io/github.com/gin-gonic/gin/@latest",
    "https://proxy.golang.com.cn/github.com/gin-gonic/gin/@latest",
]
out = ["=== 各镜像 /@latest 测试 ==="]
for u in urls:
    i, o, e = c.exec_command("curl -s -o /dev/null -w '%{http_code} %{size_download}' --connect-timeout 6 '" + u + "'")
    out.append(u + " -> " + o.read().decode("utf-8", "replace").strip())
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_goproxy_test2.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
