# -*- coding: utf-8 -*-
import io

p = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\AthenaWrt-待修问题记录.md"
t = io.open(p, encoding="utf-8").read()

old30 = "| 编译机通过（3.1MB→1.56MB 保留尾部），待真机 |"
new30 = "| 真机通过：44,818,699 B → 2,270,892 B，Shmem 102,060 → 60,820 kB；上限随后调至 4MB（见第 36 项） |"
assert old30 in t
t = t.replace(old30, new30)

add = """
| 36 | 日志限额上机后不降反涨（44.8MB）、锁与记录文件都不存在 | 真机 `sh -x`：`+ stat -c '%s' /tmp/dnsmasq.log` → `+ sz=` → `exit 0`。这台 BusyBox v1.38.0 的 `stat -c '%s'` 返回空串，尺寸读空直接退出，脚本从没走通过 | v1.2.55：新增 `fsize()`，优先 `wc -c < 文件 | tr -d ' \\t'`，失败再退回 `stat -c %s`；v1.2.56 把 CAP 由 2MB 调到 4MB（真机 20000 行实测 2.27MB ＞ 2MB，会每分钟空转裁一次） | 真机通过：44,818,699 → 2,270,892 B；记录显示 cron 每分钟确实在跑（22:37–22:43 各一条 trim），换 4MB 后不再空转 |
| 37 | 后台输入密码后永远显示「登录中…」，进不去 | ①v1.2.54 在 boot() 新增 loadKpiOrderRemote()，首个调用 athena-prefs.sh；②rpcd ACL（/usr/share/rpcd/acl.d/luci-app-athena.json）逐条列了所有 athena-*.sh，**唯独漏 athena-prefs.sh**；③rpcd 返回码 6，旧 exec() 把 6 当「会话过期」调 _authFail()；④_authFail() 把登录遮罩顶回来但不复位按钮文字 → 永久「登录中」。取证：真机 wget POST /ubus/ session.login 成功返回 ubus_rpc_session，其 ACL 列表里确认无 prefs | v1.2.56：ACL 补 `/usr/libexec/athena-prefs.sh:["exec"]`（31→32 条，必须 /etc/init.d/rpcd restart 生效）；exec() 返回码 6 只抛「执行权限不足」不再 _authFail、5 抛「命令未返回数据」，j.error 仅在 session 存在且匹配 access denied/invalid session/expired 时才踢回登录页；_authFail() 复位按钮；doLogin()、boot() 全包 try/catch，异常原文显示为红字；boot() 内 18 个 loadXxx 与 8 个 renderXxx 用 _safe(fn,tag) 逐个隔离 | 三个文件已真机装机（f419fd74… / e08ea89c… / 543defb0…，rpcd 已重启），**待 Jason 用无痕窗口登录验收** |
"""
io.open(p, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + add)
print("ok")
