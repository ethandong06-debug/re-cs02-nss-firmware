# -*- coding: utf-8 -*-
import paramiko, io

PROBE = r'''
import * as fs from 'fs';

// popen 用法探测
let h = fs.popen('echo hello-popen');
let txt = h.read('all');
h.close();
print("popen out=", txt, "\n");

// statvfs 字段
let sv = fs.statvfs('/');
print("statvfs keys=", join(' ', sort(keys(sv))), "\n");
print("sv=", sv, "\n");

// stat 字段
let st = fs.stat('/proc/stat');
print("stat keys=", join(' ', sort(keys(st))), "\n");

// glob / lsdir
print("glob=", fs.glob('/sys/block/*'), "\n");
print("lsdir=", fs.lsdir('/sys/block'), "\n");

// mkdir / rmdir / rename 返回值
print("mkdir=", fs.mkdir('/tmp/probe.lock'), "\n");
print("mkdir2=", fs.mkdir('/tmp/probe.lock'), "\n");
print("rmdir=", fs.rmdir('/tmp/probe.lock'), "\n");

// match 无 /s 时能否跨行
let s = "a\nb";
print("match=", match(s, /^a.*b$/), "\n");

// readfile 缺失返回
print("readfile missing=", fs.readfile('/tmp/nonexistent-xyz'), "\n");

// sprintf / 取整
print("sprintf=", sprintf("%.1f", 1.23456), " int=", int(3.9), "\n");
'''
LOCAL_TMP = r"C:\Users\Administrator\AppData\Local\Temp\probe_uc.py"
io.open(LOCAL_TMP, "w", encoding="utf-8").write(PROBE)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp(); s.put(LOCAL_TMP, "/tmp/probe_uc.py"); s.close()
def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
out = run("%s /tmp/probe_uc.py" % U)
io.open(r"C:\Users\Administrator\AppData\Local\Temp\probeuc.txt", "w", encoding="utf-8").write(out)
c.close()
