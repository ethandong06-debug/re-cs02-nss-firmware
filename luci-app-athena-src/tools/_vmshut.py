import paramiko, io, time, traceback

log = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=15)

    def run(cmd, t=30):
        _, o, e = c.exec_command(cmd, timeout=t)
        return (o.read().decode() + e.read().decode()).strip()

    log.append("jobs: " + run("systemctl list-jobs --no-pager 2>&1 | head -8"))
    log.append("shutdown cmd: " + run("echo vboxuser | sudo -S systemctl poweroff --no-block 2>&1; echo rc=$?", 20))
    c.close()

    # 轮询 ssh 端口是否关闭
    import socket
    closed_at = None
    for i in range(24):           # 最多 120 秒
        time.sleep(5)
        s = socket.socket()
        s.settimeout(2)
        try:
            s.connect(("127.0.0.1", 2222))
            s.close()
        except Exception:
            closed_at = (i + 1) * 5
            break
    log.append("ssh port closed after: " + (str(closed_at) + "s" if closed_at else "仍未关闭（120s）"))
except Exception:
    log.append(traceback.format_exc()[:800])

io.open(r"C:\Users\Administrator\AppData\Local\Temp\vmshut.txt", "w", encoding="utf-8").write("\n".join(log))
