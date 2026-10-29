# -*- coding: utf-8 -*-
"""VM 上复测：rate.uc（trim 修正后）+ services.uc（名字带 s 不再被裁）。"""
import io, os, threading, time
import paramiko

BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
log = []

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


s = c.open_sftp()
src = io.open(os.path.join(BASE, "athena-rate.uc"), encoding="utf-8").read()
patched = src.replace("[ 'pppoe-wan', 'wan', 'br-lan' ]", "[ 'enp0s3', 'eth0', 'pppoe-wan' ]")
assert patched != src
s.putfo(io.BytesIO(patched.encode("utf-8")), "/tmp/rate_test.uc")
s.put(os.path.join(BASE, "athena-services.uc"), "/tmp/svc.uc")
s.close()


def call():
    return run(UC + " /tmp/rate_test.uc")


log.append("== rate 首采 ==")
log.append(call())


def pull():
    s2 = c.open_sftp()
    s2.get("/tmp/big.bin", os.devnull)
    s2.close()


th = threading.Thread(target=pull)
th.start()
time.sleep(0.3)
log.append("== 有流量采样 ==")
log.append(call())
time.sleep(2)
log.append(call())
th.join()
time.sleep(0.5)
log.append("== 静默 ==")
call()
time.sleep(2)
log.append(call())

log.append("== services.uc list（看名字带 s 的服务是否完整）==")
log.append(run(UC + " /tmp/svc.uc list 2>&1 | head -c 1200"))

c.close()
io.open(r"C:\Users\Administrator\AppData\Local\Temp\rate57b.txt", "w", encoding="utf-8").write("\n".join(log))
print("done")
