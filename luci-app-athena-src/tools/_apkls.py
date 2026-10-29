# -*- coding: utf-8 -*-
import paramiko, io
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
apk = B + "/bin/packages/aarch64_cortex-a53/base/luci-app-athena-1.2.44-r1.apk"
py = r'''
import gzip, io, sys, tarfile
p = sys.argv[1]
raw = open(p,'rb').read()
# apk = 多个 gzip 流拼接：signature / control / data
off = 0; idx = 0; names = []
while off < len(raw):
    try:
        g = gzip.GzipFile(fileobj=io.BytesIO(raw[off:]))
        data = g.read()
    except Exception as e:
        print("stream %d error: %s" % (idx, e)); break
    consumed = g.fileobj.tell()
    try:
        tf = tarfile.open(fileobj=io.BytesIO(data))
        mem = tf.getnames()
        print("stream %d: %d entries" % (idx, len(mem)))
        if idx >= 1:
            names += mem
    except Exception as e:
        print("stream %d not tar: %s" % (idx, e))
    off += consumed; idx += 1
print("---- 数据段文件（前 40 + 关键文件）----")
for n in names[:40]: print(n)
key = [n for n in names if 'athena-resources' in n or 'index.html' in n or 'filebrowser' in n]
print("---- 关键文件 ----")
for n in key: print(n)
print("总条目:", len(names))
'''
open("/tmp/apkls.py","w").write(py)
out = run("python3 /tmp/apkls.py %s" % apk)
io.open(r"C:\Users\Administrator\AppData\Local\Temp\apkls.txt", "w", encoding="utf-8").write(out)
c.close()
