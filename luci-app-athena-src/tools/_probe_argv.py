# -*- coding: utf-8 -*-
"""探查 ucode argv 支持、tar -xzO 取成员、6MB APKINDEX 解析速度。"""
import paramiko, os, io, random, string

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
TMP = os.environ.get("TEMP", ".")
TOOLS = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=300):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


run("rm -rf /tmp/idx; mkdir -p /tmp/idx")
s = c.open_sftp()
s.put(os.path.join(TOOLS, "probe_argv.uc"), "/tmp/probe_argv.uc")
s.close()

random.seed(7)
lines = []
for i in range(60000):
    name = "pkg%d-%s" % (i, "".join(random.choice(string.ascii_lowercase) for _ in range(6)))
    lines += ["C:Q1%s=" % ("".join(random.choice("ABCdef0123") for _ in range(20))),
              "P:" + name,
              "V:1.%d.%d-r%d" % (i % 50, i % 97, i % 9),
              "A:aarch64_cortex-a53", "S:12345", "I:23456",
              "T:test package %d" % i, "D:dep1 dep2", ""]
APK = "\n".join(lines) + "\n"
pp = os.path.join(TMP, "fake_APKINDEX")
io.open(pp, "w", encoding="utf-8", newline="\n").write(APK)

PARSER = """import * as fs from 'fs';
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
printf('rows=%d bytes=%d\\n', length(rows), length(txt));
"""
pi = os.path.join(TMP, "idxparse.uc")
io.open(pi, "w", encoding="utf-8", newline="\n").write(PARSER)

s = c.open_sftp()
s.put(pp, "/tmp/idx/APKINDEX")
s.put(pi, "/tmp/idxparse.uc")
s.close()

out = []
out.append("== ucode argv 支持 ==")
out.append(run(U + " /tmp/probe_argv.uc foo bar 2>&1"))
out.append("== tar -xzO 取单成员 ==")
out.append(run("tar -czf /tmp/idx/APKINDEX.test.tar.gz -C /tmp/idx APKINDEX && ls -l /tmp/idx/ | head -4 && tar -xzOf /tmp/idx/APKINDEX.test.tar.gz APKINDEX | wc -c"))
out.append("== 6MB / 6 万条解析 ==")
out.append(run(U + " /tmp/idxparse.uc 2>&1"))
out.append(run("for i in 1 2; do /usr/bin/time -f 'REAL %e %U %S' " + U + " /tmp/idxparse.uc >/dev/null; done 2>&1"))
out.append("== tar+gzip 解压耗时 ==")
out.append(run("for i in 1 2; do /usr/bin/time -f 'TAR %e %U %S' sh -c 'tar -xzOf /tmp/idx/APKINDEX.test.tar.gz APKINDEX > /dev/null'; done 2>&1"))

io.open(os.path.join(TMP, "probe_argv.txt"), "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
