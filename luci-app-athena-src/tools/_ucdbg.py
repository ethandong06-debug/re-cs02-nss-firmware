# -*- coding: utf-8 -*-
import paramiko, io

DBG = r'''
import * as fs from 'fs';

let h = fs.popen('uci -q show athena 2>/dev/null');
let a = h.read('all');
h.close();
print("uci athena bytes=", length(a), " raw=[", a, "]\n");

let h2 = fs.popen('iwinfo phy0-ap0 info 2>/dev/null');
let b = h2.read('all');
h2.close();
print("iwinfo bytes=", length(b), " raw=[", b, "]\n");

let m = match(b, /(2\.4[0-9]* GHz|5\.[0-9]* GHz)/);
print("band match=", m, "\n");

let lines = split("a=1\nb=2", '\n');
print("split lines=", lines, " n=", length(lines), "\n");

let t = "athena.system.mode='single'";
let mm = match(t, /^([A-Za-z0-9_.@\[\]-]+)=(.*)$/);
print("parse match=", mm, "\n");

let f = fs.readfile('/tmp/hostapd/phy0-ap0');
print("hostapd raw=[", f, "]\n");
for (let line in split(f, '\n')) {
	let r = match(line, /^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}/);
	print("  line=[", line, "] match=", r, "\n");
}

let bm = {};
bm['3c:22:fb:aa:bb:cc'] = 'x';
print("mapget=", bm['3c:22:fb:aa:bb:cc'], "\n");
'''
LOCAL = r"C:\Users\Administrator\AppData\Local\Temp\uc_dbg.uc"
io.open(LOCAL, "w", encoding="utf-8", newline="\n").write(DBG)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp(); s.put(LOCAL, "/tmp/uc_dbg.uc"); s.close()
def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
out = run("PATH=/tmp/mockbin:/usr/sbin:/usr/bin:/sbin:/bin " + U + " /tmp/uc_dbg.uc 2>&1")
io.open(r"C:\Users\Administrator\AppData\Local\Temp\ucdbg.txt", "w", encoding="utf-8").write(out)
c.close()
print("done")
