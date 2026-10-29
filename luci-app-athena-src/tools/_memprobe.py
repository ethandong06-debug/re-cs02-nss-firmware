# -*- coding: utf-8 -*-
"""量化 ucode 解析 6MB/7.6MB APKINDEX 的峰值内存：原始 split vs grep 预过滤。"""
import paramiko, os, io

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
TMP = os.environ.get("TEMP", ".")

RAW = """import * as fs from 'fs';
let txt = fs.readfile('/tmp/idx/APKINDEX');
let rows = [], name = '';
for (let line in split(txt, '\\n')) {
	if (length(line) < 2) continue;
	let t = substr(line, 0, 2);
	if (t == 'P:') { if (name != '') push(rows, name); name = substr(line, 2, length(line) - 2); }
	else if (t == 'V:') { name = name + '|' + substr(line, 2, length(line) - 2); }
}
if (name != '') push(rows, name);
sort(rows);
printf('rows=%d\\n', length(rows));
"""

FILT = """import * as fs from 'fs';
let h = fs.popen("grep -a -E '^(P|V):' /tmp/idx/APKINDEX");
let txt = h.read('all');
h.close();
let rows = [], name = '';
for (let line in split(txt, '\\n')) {
	if (length(line) < 2) continue;
	let t = substr(line, 0, 2);
	if (t == 'P:') { if (name != '') push(rows, name); name = substr(line, 2, length(line) - 2); }
	else if (t == 'V:') { name = name + '|' + substr(line, 2, length(line) - 2); }
}
if (name != '') push(rows, name);
sort(rows);
printf('rows=%d bytes=%d\\n', length(rows), length(txt));
"""

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=300):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


s = c.open_sftp()
for tag, src in (("raw", RAW), ("filt", FILT)):
    p = os.path.join(TMP, "mem_%s.uc" % tag)
    io.open(p, "w", encoding="utf-8", newline="\n").write(src)
    s.put(p, "/tmp/mem_%s.uc" % tag)
s.close()

out = []
out.append("索引大小：")
out.append(run("ls -l /tmp/idx/APKINDEX; grep -a -c -E '^(P|V):' /tmp/idx/APKINDEX"))
out.append("== 原始 split ==")
out.append(run("/usr/bin/time -v " + U + " /tmp/mem_raw.uc 2>&1 | grep -E 'rows=|Maximum resident|Elapsed'"))
out.append("== grep 预过滤 ==")
out.append(run("/usr/bin/time -v " + U + " /tmp/mem_filt.uc 2>&1 | grep -E 'rows=|Maximum resident|Elapsed'"))
out.append("== busybox 风格 grep 是否支持 -a -E ==")
out.append(run("grep -a -c -E '^(P|V):' /tmp/idx/APKINDEX"))

io.open(os.path.join(TMP, "mem.txt"), "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
