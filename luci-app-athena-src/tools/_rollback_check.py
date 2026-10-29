# -*- coding: utf-8 -*-
"""回退后校验：athena-resources.sh（v1.2.40 形态）在 VM 内能否正常出数。"""
import paramiko, json

base = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena\root\usr\libexec"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=25)
sftp = c.open_sftp()
sftp.put(base + r"\athena-resources.sh", "/tmp/rs/athena-resources.sh")
sftp.put(base + r"\athena-status.sh", "/tmp/rs/athena-status.sh")
sftp.close()

def run(cmd, t=120):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

print(run("sh -n /tmp/rs/athena-resources.sh && sh -n /tmp/rs/athena-status.sh && echo SYNTAX_OK")[0].strip())
run("rm -f /tmp/athena-res-cache /tmp/athena-res-cache.ticks /tmp/athena-res-now")
o, e = run("cd /tmp/rs && time sh athena-resources.sh")
print("elapsed:", [x for x in e.strip().splitlines() if x.startswith("real")])
try:
    d = json.loads(o[o.index("{"):o.rindex("}") + 1])
    print("keys:", list(d.keys()))
    print("cpu:", d["cpu"], "| memory:", d["memory"])
    print("procs:", len(d["procs"]), "sample:", d["procs"][0] if d["procs"] else None)
    print("新版字段是否消失:", [k for k in ("window",) if k in d["cpu"]], [k for k in ("procs_mb","other_mb") if k in d["memory"]])
except Exception as ex:
    print("解析失败:", ex, o[:300])
c.close()
