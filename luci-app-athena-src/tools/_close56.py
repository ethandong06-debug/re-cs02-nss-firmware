# -*- coding: utf-8 -*-
"""把 #33 / #37 状态改成真机通过，并在 README 7.6 补上验收结果。"""
import io

led = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\AthenaWrt-待修问题记录.md"
t = io.open(led, encoding="utf-8").read()

old33 = "CDP 实测：下移 CPU 后保存 → 首页 grid 变为 mem,cpu,up,dev，localStorage=`mem,cpu,up,dev`，路由端收到 `athena-prefs.sh set kpi_order mem,cpu,up,dev` |"
new33 = "CDP 实测：下移 CPU 后保存 → 首页 grid 变为 mem,cpu,up,dev，localStorage=`mem,cpu,up,dev`，路由端收到 `athena-prefs.sh set kpi_order mem,cpu,up,dev`；**真机通过（v1.2.56：ACL 放行 athena-prefs.sh 后，登录进主界面排序保存并刷新仍保持）** |"
assert old33 in t
t = t.replace(old33, new33)

old37 = "三个文件已真机装机（f419fd74… / e08ea89c… / 543defb0…，rpcd 已重启），**待 Jason 用无痕窗口登录验收** |"
new37 = "三个文件已真机装机（f419fd74… / e08ea89c… / 543defb0…，rpcd 已重启）；**真机通过：无痕窗口登录一次成功，指标卡排序保存并刷新后保持** |"
assert old37 in t
t = t.replace(old37, new37)
io.open(led, "w", encoding="utf-8", newline="\n").write(t)

rd = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
s = io.open(rd, encoding="utf-8").read()
old = "| `sh /usr/libexec/athena-logcap.sh;ls -l /tmp/dnsmasq.log` | 当前 2.27MB < 4MB，应当**不动**（正确跳过）；再涨过 4MB 才裁一次 |"
new = (old + "\n\n### 7.7 真机验收结果（2026-10-28 22:50）\n\n"
       "| 项 | 结果 |\n|---|---|\n"
       "| 登录卡在「登录中」 | **已解决**：无痕窗口一次登录成功，ACL 补 `athena-prefs.sh` 生效 |\n"
       "| 指标卡排序 | **已解决**：真机上改序保存、刷新后顺序保持（远端持久化真的写进路由器了） |\n"
       "| 日志每分钟空转裁剪 | **已解决**：裁剪记录最后一条停在 22:43:00（换 4MB 上限那一刻），之后不再新增 |\n"
       "| 磁盘 / 服务「打开」/ 日志四列 / 内核线程开关 | 真机后端输出与前端渲染均已核对通过 |\n")
assert old in s
s = s.replace(old, new)
io.open(rd, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
