# -*- coding: utf-8 -*-
"""用 VM 上的 ucode 实测 \s 的真实语义（字符类内 / 外、trim、split、MemTotal）。"""
import io, paramiko

UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
prog = r'''
print("A trim旧式_ddns=[", replace("ddns", /[\s\r\n]+$/, ""), "]\n");
print("B trim新式_=[", replace("ddns", /[ \t\r\n]+$/, ""), "]\n");
print("C 类内\\s_enp0s3=", (match("enp0s3: 5 6", /^[ \t]*([^ \t:]+):[ \t]*(.+)$/) != null), "\n");
print("D 类内\\s_老式=", (match("enp0s3: 5 6", /^\s*([^\s:]+):\s*(.+)$/) != null), "\n");
print("E split\\s+=", split("1  2", /\s+/), "\n");
print("F split类=", split("1  2", /[ \t]+/), "\n");
print("G MemTotal\\s=", match("MemTotal:     812345 kB", /MemTotal:\s+(\d+)/), "\n");
print("H btime\\s=", match("btime 12345", /^btime\s+(\d+)/), "\n");
'''
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp()
s.putfo(io.BytesIO(prog.encode("utf-8")), "/tmp/regx.uc")
s.close()
_, o, e = c.exec_command(UC + " /tmp/regx.uc 2>&1", timeout=60)
print(o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
c.close()
