# -*- coding: utf-8 -*-
import paramiko, io

PY = r'''
import gzip, io, sys, tarfile
p = sys.argv[1]
raw = open(p, 'rb').read()
off = 0; idx = 0; names = []
while off < len(raw):
    try:
        bio = io.BytesIO(raw[off:])
        g = gzip.GzipFile(fileobj=bio)
        data = g.read()
        consumed = bio.tell() - len(g.unused) if hasattr(g, 'unused') else bio.tell()
    except Exception as e:
        print("stream %d error: %s" % (idx, e)); break
    try:
        tf = tarfile.open(fileobj=io.BytesIO(data))
        mem = tf.getnames()
        print("stream %d: %d entries" % (idx, len(mem)))
        if idx >= 1:
            names += mem
    except Exception as e:
        print("stream %d not tar: %s" % (idx, e))
    if consumed <= 0: break
    off += consumed; idx += 1
print("---- 数据段前 25 ----")
for n in names[:25]: print(n)
key = [n for n in names if 'athena-resources' in n or 'index.html' in n or 'filebrowser' in n]
print("---- 关键文件 ----")
for n in key: print(n)
print("总条目:", len(names))
'''

LOCAL_TMP = r"C:\Users\Administrator\AppData\Local\Temp\apkls_remote.py"
io.open(LOCAL_TMP, "w", encoding="utf-8").write(PY)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
s.put(LOCAL_TMP, "/tmp/apkls_remote.py")
s.close()
def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
apk = B + "/bin/packages/aarch64_cortex-a53/base/luci-app-athena-1.2.44-r1.apk"
out = run("python3 /tmp/apkls_remote.py %s" % apk)
io.open(r"C:\Users\Administrator\AppData\Local\Temp\apkls.txt", "w", encoding="utf-8").write(out)
c.close()
print("done")
