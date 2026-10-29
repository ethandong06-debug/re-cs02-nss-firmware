# -*- coding: utf-8 -*-
import paramiko, io
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)
def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()
R = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/target-aarch64_cortex-a53_musl/root-qualcommax"
out = []
out.append("== 设备上 ucode 的真实路径（入口脚本硬编码了 /usr/bin/ucode）==")
out.append(run("ls -l %s/usr/bin/ucode %s/usr/bin/ucode-cli 2>/dev/null; find %s/usr -maxdepth 2 -name 'ucode*' 2>/dev/null | head" % (R, R, R)))
out.append("== staging 里 .uc 与本地是否一致（sha256）==")
out.append(run("sha256sum %s/usr/libexec/athena-resources.uc %s/usr/libexec/athena-resources.sh %s/usr/libexec/athena-resources-legacy.sh" % (R, R, R)))
io.open(r"C:\Users\Administrator\AppData\Local\Temp\ucpath.txt", "w", encoding="utf-8").write("\n".join(out))
c.close()
