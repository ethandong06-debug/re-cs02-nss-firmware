# -*- coding: utf-8 -*-
"""入口包装功能测试：正常透传 / ucode 输出变坏时回退 legacy。"""
import paramiko, io

LOCAL_WRAP = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec\athena-status.sh"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
s = c.open_sftp(); s.put(LOCAL_WRAP, "/tmp/wrap_src.sh"); s.close()

def run(cmd, t=180):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()

B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
ENV = "PATH=/tmp/mockbin:/usr/sbin:/usr/bin:/sbin:/bin"
CLEAN = "rm -f /tmp/athena-status.json /tmp/athena-status.stamp /tmp/athena-cpu-cache /tmp/athena-net-cache /tmp/athena-devs; rm -rf /tmp/athena-status.lock"

out = []
out.append("== 造两个包装：正常 / 指向坏 uc ==")
out.append(run("chmod 755 /tmp/st_old.sh /tmp/st_new.uc; sed 's#/usr/bin/ucode#%s#; s#/usr/libexec/athena-status.uc#/tmp/st_new.uc#; s#/usr/libexec/athena-status-legacy.sh#/tmp/st_old.sh#' /tmp/wrap_src.sh > /tmp/wrap_ok.sh; "
               "printf '{\"x\":1}\\n' > /tmp/bad.uc; "
               "chmod 755 /tmp/st_old.sh /tmp/st_new.uc; sed 's#/usr/bin/ucode#%s#; s#/usr/libexec/athena-status.uc#/tmp/bad.uc#; s#/usr/libexec/athena-status-legacy.sh#/tmp/st_old.sh#' /tmp/wrap_src.sh > /tmp/wrap_bad.sh; "
               "chmod 755 /tmp/wrap_ok.sh /tmp/wrap_bad.sh; grep -n 'ucode\\|legacy\\|athena-status.uc' /tmp/wrap_ok.sh" % (U, U)))
out.append("== A) 正常：包装输出应等于 ucode 直接输出 ==")
out.append(run(ENV + " sh -c '" + CLEAN + "; /tmp/wrap_ok.sh > /tmp/w_ok.json; md5sum /tmp/w_ok.json'"))
out.append(run(ENV + " sh -c '" + CLEAN + "; " + U + " /tmp/st_new.uc > /tmp/u_direct.json; md5sum /tmp/u_direct.json'"))
out.append("[前 160 字节] " + run("head -c 160 /tmp/w_ok.json"))
out.append("== B) uc 输出不是我们要的 JSON：包装应回退到 legacy ==")
out.append(run(ENV + " sh -c '" + CLEAN + "; /tmp/wrap_bad.sh > /tmp/w_bad.json; md5sum /tmp/w_bad.json'"))
out.append(run(ENV + " sh -c '" + CLEAN + "; sh /tmp/st_old.sh > /tmp/legacy_direct.json; md5sum /tmp/legacy_direct.json'"))
out.append("[前 160 字节] " + run("head -c 160 /tmp/w_bad.json"))
out.append("== C) 三层 JSON 都合法、顶层字段一致 ==")
out.append(run("python3 -c \"import json;a=json.load(open('/tmp/w_ok.json'));b=json.load(open('/tmp/w_bad.json'));c=json.load(open('/tmp/legacy_direct.json'));print('ok keys',sorted(a));print('bad==legacy',sorted(b)==sorted(c));print('two files same keys',sorted(a)==sorted(c))\""))
out.append("== D) 耗时：包装（含 1 次子 shell）==")
out.append(run(ENV + " sh -c 'for i in 1 2 3; do " + CLEAN + "; /usr/bin/time -f \"WRAP %e real %U user %S sys\" /tmp/wrap_ok.sh >/dev/null; done' 2>&1"))

io.open(r"C:\Users\Administrator\AppData\Local\Temp\wrap45.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
print("done")
