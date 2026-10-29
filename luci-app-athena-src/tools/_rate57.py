# -*- coding: utf-8 -*-
"""在编译机上验证 athena-rate.uc：语法 + 真实流量下的速率数值与 dt 精度。

VM 里没有 pppoe-wan，所以拷一份把候选接口换成 enp0s3 的副本（只改候选列表，逻辑完全同源），
然后一边 sftp 拉大文件制造 eth 流量，一边 2 秒采样两次，看速率是否落在合理区间。
"""
import io, os, threading, time
import paramiko

LOCAL = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-rate.uc"
OUT = r"C:\Users\Administrator\AppData\Local\Temp\rate57.txt"
UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"

log = []

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


s = c.open_sftp()
s.put(LOCAL, "/tmp/rate.uc")
src = io.open(LOCAL, encoding="utf-8").read()
patched = src.replace("[ 'pppoe-wan', 'wan', 'br-lan' ]", "[ 'enp0s3', 'eth0', 'pppoe-wan' ]")
assert patched != src, "候选列表替换失败"
s.putfo(io.BytesIO(patched.encode("utf-8")), "/tmp/rate_test.uc")
s.close()

log.append("== ucode 路径 ==")
log.append(run("ls -l " + UC + "; " + UC + " -e 'print(1+1)'"))


def call():
    return run(UC + " /tmp/rate_test.uc")


log.append("== 首次采样（建立基准，应为 0 并带 primed）==")
log.append(call())

log.append("== 造 300MB 文件 ==")
log.append(run("dd if=/dev/zero of=/tmp/big.bin bs=1M count=300 2>&1 | tail -1"))

log.append("== 制造 eth0 流量 + 两次采样（间隔 2s）==")


def pull():
    s2 = c.open_sftp()
    s2.get("/tmp/big.bin", os.devnull)
    s2.close()


th = threading.Thread(target=pull)
th.start()
time.sleep(0.8)
log.append("t1: " + call())
time.sleep(2)
log.append("t2: " + call())
th.join()

log.append("== 静止状态（无流量，应接近 0）==")
time.sleep(1)
call()
time.sleep(2)
log.append("t3: " + call())

log.append("== 并发保护：0.2 秒内连打两次（应沿用上次值，dt_ms<400）==")
log.append(run(UC + " /tmp/rate_test.uc; sleep 0.2; " + UC + " /tmp/rate_test.uc"))

log.append("== 缓存文件 ==")
log.append(run("cat /tmp/.athena-rate"))

c.close()
io.open(OUT, "w", encoding="utf-8").write("\n".join(log))
print("done")
