import paramiko, os

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=15)

out = []
i, o, e = c.exec_command("curl -s -o /dev/null -w '%{http_code} %{time_total}s' --connect-timeout 8 https://github.com; echo; curl -s -o /dev/null -w '%{http_code} %{time_total}s' --connect-timeout 8 https://codeload.github.com/filebrowser/filebrowser/tar.gz/v2.43.0")
out.append("=== github 可达性 ===\n" + o.read().decode("utf-8", "replace").strip())
i, o, e = c.exec_command("which go git; go version 2>/dev/null | head -1")
out.append("=== VM go/git ===\n" + o.read().decode("utf-8", "replace").strip())
c.close()

p = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gh_chk.txt"
with open(p, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
