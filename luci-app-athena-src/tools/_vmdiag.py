import paramiko, io, traceback

out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=15)
    out.append("connected")
    for cmd in ["uptime", "id", "echo vboxuser | sudo -S id 2>&1"]:
        _, o, e = c.exec_command(cmd, timeout=25)
        out.append("$ " + cmd + " -> " + (o.read().decode() + e.read().decode()).strip()[:200])
    c.close()
except Exception:
    out.append(traceback.format_exc()[:800])

io.open(r"C:\Users\Administrator\AppData\Local\Temp\vmdiag.txt", "w", encoding="utf-8").write("\n".join(out))
