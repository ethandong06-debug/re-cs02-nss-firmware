# -*- coding: utf-8 -*-
import paramiko, io
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace"))
B = "/home/vboxuser/jdc-build/immortalwrt_ipq-main"
U = B + "/staging_dir/hostpkg/bin/ucode"
out = []
out.append("== ucode 版本 ==")
out.append(run("%s -v" % U).strip())
out.append("== fs 导出 ==")
out.append(run("%s -e \"import * as fs from 'fs'; print(join('\\n', sort(keys(fs))), '\\n')\"" % U).strip())
out.append("== 顶层模块 ==")
out.append(run("%s -e \"print(join(' ', sort(keys(require('fs')))), '\\n')\"" % U).strip())
io.open(r"C:\Users\Administrator\AppData\Local\Temp\ucexports.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
