import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
i, o, e = c.exec_command("curl -sI --connect-timeout 8 https://goproxy.cn | head -3; echo ---; curl -sI --connect-timeout 8 https://mirrors.aliyun.com/goproxy/ | head -3")
out.append("=== GOPROXY 可达性 ===\n" + o.read().decode("utf-8", "replace").strip())

# 检查 filebrowser Makefile 的 Go 构建方式
i, o, e = c.exec_command("cat /home/vboxuser/jdc-build/immortalwrt_ipq-main/feeds/packages/utils/filebrowser/Makefile")
out.append("=== filebrowser Makefile ===\n" + o.read().decode("utf-8", "replace").strip()[:1500])
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_goproxy_chk.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
