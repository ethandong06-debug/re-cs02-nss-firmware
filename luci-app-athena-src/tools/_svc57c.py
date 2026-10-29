# -*- coding: utf-8 -*-
"""用 timeout 跑新版 services.uc，看是哪一行卡住。"""
import paramiko

UC = "/home/vboxuser/jdc-build/immortalwrt_ipq-main/staging_dir/hostpkg/bin/ucode"
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("127.0.0.1", 2222, "vboxuser", "vboxuser", timeout=20)


def run(cmd, t=60):
    _, o, e = c.exec_command(cmd, timeout=t)
    return (o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")).strip()


print("== 15 秒超时跑全量 list ==")
print(run("timeout 15 " + UC + " /tmp/svc.uc list > /tmp/svc.out 2>/tmp/svc.err; echo rc=$?; echo --- out:; head -c 400 /tmp/svc.out; echo; echo --- err:; cat /tmp/svc.err"))

print("== 单独测控制器解析 ==")
test = '''import * as fs from 'fs';
function rd(p){ let s = fs.readfile(p); return (s == null) ? '' : s; }
let txt = rd('/usr/lib/lua/luci/controller/ddnsto.lua');
print('txtlen=', length(txt), '\\n');
for (let line in split(txt, '\\n')) {
  if (index(line, 'entry(') < 0) continue;
  let rest0 = substr(line, index(line, 'entry('));
  let close = index(rest0, '}');
  let rest = (close > 0) ? substr(rest0, 0, close) : rest0;
  print('rest=[', rest, ']\\n');
  let toks = [];
  let at = 0;
  while (at < length(rest)) {
    let q1 = index(rest, '"', at);
    if (q1 < 0) break;
    let q2 = index(rest, '"', q1 + 1);
    if (q2 < 0) break;
    push(toks, substr(rest, q1 + 1, q2 - q1 - 1));
    at = q2 + 1;
  }
  print('toks=', toks, '\\n');
}
'''
s = c.open_sftp()
import io
s.putfo(io.BytesIO(test.encode("utf-8")), "/tmp/dbgctrl.uc")
s.close()
print(run("timeout 15 " + UC + " /tmp/dbgctrl.uc; echo rc=$?"))
c.close()
