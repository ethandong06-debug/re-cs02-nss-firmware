# -*- coding: utf-8 -*-
"""v1.2.48：packages.uc 解析 /lib/apk/db/installed 的等价性 + 入口路由四态。"""
import paramiko, io, os

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
TMP = os.environ.get("TEMP", ".")

DB = "\n".join([
    "C:Q1QAMEFchtzTMQ9naKKyrfyFIDwEs=", "P:6rd", "V:13", "A:noarch", "S:3786", "I:10905", "T:IPv6 support", "",
    "C:Q1zzz", "P:base-files", "V:1655~r1", "A:aarch64_cortex-a53", "S:1000", "",
    "C:Q1aaa", "P:libc", "V:1.2.5-r4", "A:aarch64_cortex-a53", "S:20000", "",
    "C:Q1bbb", "P:luci-app-athena", "V:1.2.48-r1", "A:all", "S:30000", "",
    "C:Q1ccc", "P:kmod-nss-drv", "V:12.0.0~2024-01-01", "A:aarch64_cortex-a53", "S:4000", "",
    "C:Q1ddd", "P:busybox", "V:1.38.0-r1", "A:aarch64_cortex-a53", "S:5000", "",
    "C:Q1eee", "P:busybox", "V:1.38.0-r1", "A:aarch64_cortex-a53", "S:5000", "",
    "C:Q1fff", "P:zoneinfo-core", "V:2024b-r1", "A:all", "S:600", "",
    "",
])

STUB = '#!/bin/sh\nprintf \'{"ok":true,"packages":[],"note":"LEGACY"}\'\n'


def reference(db_text):
    rows, seen = [], set()
    state = {"name": None, "ver": ""}

    def flush():
        n = state["name"]
        if n and n not in seen:
            seen.add(n)
            rows.append((n, state["ver"] or ""))

    for line in db_text.split("\n"):
        if len(line) < 2:
            continue
        if line[:2] == "P:":
            flush()
            state["name"], state["ver"] = line[2:], ""
        elif line[:2] == "V:" and state["name"] is not None:
            state["ver"] = line[2:]
    flush()
    rows.sort(key=lambda r: (r[0] + "|" + r[1]).encode())
    return rows


c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()


def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


run("rm -rf /tmp/pk /tmp/pkw; mkdir -p /tmp/pk/db /tmp/pkw")
p = os.path.join(TMP, "pk48_db")
io.open(p, "w", encoding="utf-8", newline="\n").write(DB)
s.put(p, "/tmp/pk/db/installed")
p2 = os.path.join(TMP, "pk48_stub.sh")
io.open(p2, "w", encoding="utf-8", newline="\n").write(STUB)
s.put(p2, "/tmp/pkw/stub.sh")
s.put(os.path.join(LOCAL, "athena-packages.uc"), "/tmp/pkw/uc_raw.uc")
s.put(os.path.join(LOCAL, "athena-packages.sh"), "/tmp/pkw/wrap_raw.sh")
s.close()
run("chmod 755 /tmp/pkw/stub.sh")

out = []
out.append("== 编译测试副本 ==")
out.append(run(
    "sed \"s#/lib/apk/db/installed#/tmp/pk/db/installed#\" /tmp/pkw/uc_raw.uc > /tmp/pkw/uc.uc; "
    "sed \"s#/usr/libexec/athena-packages.uc#/tmp/pkw/uc.uc#; s#/usr/libexec/athena-packages-legacy.sh#/tmp/pkw/stub.sh#; s#/usr/bin/ucode#%s#\" /tmp/pkw/wrap_raw.sh > /tmp/pkw/wrap.sh; "
    "chmod 755 /tmp/pkw/wrap.sh /tmp/pkw/uc.uc; ls -l /tmp/pkw" % U))

out.append("== uc 输出 ==")
out.append(run(U + " /tmp/pkw/uc.uc > /tmp/pkw/o.json 2>/tmp/pkw/e.txt; echo exit=$?; head -c 300 /tmp/pkw/e.txt; cat /tmp/pkw/o.json"))
out.append("== 耗时（3 次）+ execve ==")
out.append(run("for i in 1 2 3; do /usr/bin/time -f 'REAL %e %U %S' " + U + " /tmp/pkw/uc.uc >/dev/null; done 2>&1"))
out.append(run("strace -f -c -e trace=execve " + U + " /tmp/pkw/uc.uc >/dev/null 2>/tmp/pkw/tr.txt; grep -E 'execve|total' /tmp/pkw/tr.txt | head -2"))

out.append("== 入口路由 ==")
out.append(run("echo '-- list installed:'; sh /tmp/pkw/wrap.sh list installed | head -c 150; echo"))
out.append(run("echo '-- list available:'; sh /tmp/pkw/wrap.sh list available | head -c 150; echo"))
out.append(run("echo '-- list installed kw:'; sh /tmp/pkw/wrap.sh list installed busy | head -c 150; echo"))
out.append(run("echo '-- install foo:'; sh /tmp/pkw/wrap.sh install foo | head -c 150; echo"))
out.append(run("echo '-- uc broken:'; printf 'broken(\\n' > /tmp/pkw/bad.uc; sed 's#/tmp/pkw/uc.uc#/tmp/pkw/bad.uc#' /tmp/pkw/wrap.sh > /tmp/pkw/wrap_bad.sh; chmod 755 /tmp/pkw/wrap_bad.sh; sh /tmp/pkw/wrap_bad.sh list installed | head -c 150; echo"))
out.append(run("echo '-- uc missing:'; sed 's#/tmp/pkw/uc.uc#/tmp/pkw/none.uc#' /tmp/pkw/wrap.sh > /tmp/pkw/wrap_miss.sh; chmod 755 /tmp/pkw/wrap_miss.sh; sh /tmp/pkw/wrap_miss.sh list installed | head -c 150; echo"))

io.open(os.path.join(TMP, "pkg48.txt"), "w", encoding="utf-8").write("\n".join(out))
ref = reference(DB)
io.open(os.path.join(TMP, "pk48_ref.txt"), "w", encoding="utf-8").write(
    "\n".join("%s | %s" % (n, v) for n, v in ref))
c.close()
print("done")
