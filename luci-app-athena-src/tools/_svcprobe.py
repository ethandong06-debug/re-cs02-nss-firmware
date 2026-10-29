# -*- coding: utf-8 -*-
import paramiko, io

PROBE = r'''
import * as fs from 'fs';
let st = fs.stat('/tmp/svc/etc/init.d/ddns');
print("stat=", st, "\n");
print("perm=", st.perm, " mode=", st.mode, " perm&73=", st.perm & 73, "\n");
let ls = fs.lsdir('/tmp/svc/etc/init.d');
print("lsdir=", ls, "\n");
print("sorted=", sort(ls), "\n");
let rc = fs.lsdir('/tmp/svc/etc/rc.d');
print("rc=", rc, "\n");
for (let e in rc) print("  entry=[", e, "] matchS=", match(e, /^S[0-9]/), "\n");
'''
LOCAL = r"C:\Users\Administrator\AppData\Local\Temp\svcprobe.uc"
io.open(LOCAL, "w", encoding="utf-8", newline="\n").write(PROBE)
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp(); s.put(LOCAL, "/tmp/svcprobe.uc"); s.close()
def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
out = run(U + " /tmp/svcprobe.uc 2>&1")
io.open(r"C:\Users\Administrator\AppData\Local\Temp\svcprobe.txt", "w", encoding="utf-8").write(out)
c.close()
print("done")
