import paramiko, traceback
out = []
try:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", port=2222, username="vboxuser", password="vboxuser", timeout=20)
    def run(cmd, name, t=30):
        stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
        o = stdout.read().decode("utf-8", "replace")
        out.append("=== %s ===\n%s" % (name, (o.strip() or "(空)")[-800:]))
    run("pkill -9 make ; pkill -9 -f 'download.pl' ; pkill -9 -f 'curl.real' ; pkill -9 -f 'time.pl' ; sleep 2 ; ps aux | grep -E 'make|download|curl' | grep -v grep | wc -l", "全杀残留进程", 30)
    c.close()
except Exception as e:
    out.append(traceback.format_exc())
open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_kill2.txt","w",encoding="utf-8").write("\n".join(out))
