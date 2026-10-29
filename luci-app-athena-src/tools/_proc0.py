import paramiko, os
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)
i, o, e = c.exec_command("ps aux | grep -E 'make|pnpm|filebrowser|node ' | grep -v grep | wc -l")
out = "残留进程数: " + o.read().decode("utf-8", "replace").strip()
with open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_proc0.txt", "w", encoding="utf-8") as f:
    f.write(out)
c.close()
