import paramiko, time, sys

HOST = "127.0.0.1"
PORT = 2222
USER = "vboxuser"
PASS = "vboxuser"
BASE = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)

cmd = "cd %s && export GOPROXY=direct GOSUMDB=off GOFLAGS=-mod=mod && make -j6 V=s 2>&1 | tail -120" % BASE
stdin, stdout, stderr = c.exec_command(cmd, timeout=3600)

buf = b""
while True:
    chunk = stdout.channel.recv(65536)
    if not chunk:
        break
    buf += chunk

text = buf.decode("utf-8", "replace")
# 保存完整尾部
with open(r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_rebuild_log13.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("=== 日志尾部 ===")
print(text[-3000:])
sys.exit(0 if "make: *** [" not in text.splitlines()[-1] else 1)
