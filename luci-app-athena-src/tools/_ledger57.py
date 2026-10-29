# -*- coding: utf-8 -*-
"""台账追加第 38、39 项。"""
import io

P = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\AthenaWrt-待修问题记录.md"
ROWS = u"""
| 38 | 「实时网速」卡显示不准：实测 1900 Mbps 只测到 945.2，且测速结束页面才刚开始动 | ①`athena-status.uc` 的 rx_rate/tx_rate 是「两次调用之间」的平均，而页面 15 秒轮询一次 → delta 窗口就是 15 秒，1900M 的 20 秒测速被摊成 900 多；②`pushSpark` 15 秒一点 × 60 点 = 15 分钟，标题却写「最近 60 秒」 | v1.2.57：新增 `athena-rate.uc`（只读 /proc/uptime + /proc/net/dev，单接口单选，百秒分之一精度，首采/回绕只重置基准，dt<0.4s 沿用上次值）；`athena-status.sh` 加 `rate` 分支走已放行的 ACL 条目；`index.html` 新增 `loadRate()` 2 秒独立采样、pushSpark 上限 30、drawSpark 按点数动态、两列峰值实时刷新、静态假初值清零 | 编译机实测（VM 无 pppoe-wan，用同源副本换 enp0s3）：首采 primed、sftp 拉 300MB 时 tx 129→612 Mbps、dt_ms≈2000、静默 0.0、0.2 秒连打沿用上次值；**待真机装机验收** |
| 39 | ddnsto 只能走官方控制台外链，没跟原生菜单对齐 | Jason 明确：ddnsto 有原生 LuCI 菜单入口，不要单独做外链，直接引用原生接口。追查发现更底层的坑：三个 .uc 的 `trim()` 用 `[\\s\\r\\n]`，而 ucode 字符类里 `\\s` 是字面字母 s → 值结尾的 s 被裁掉（`ddns`→`ddn`、`dbus`→`dbu`），菜单路径匹配也随之错位；`[^\\s:]` 同理匹配不到 enp0s3 这类带 s 的网卡名 | v1.2.57：删除 `KNOWN_UI`（不再输出 url）；`detect_path()` 加第三轮兜底（任何 menu.d 里含 base 的 admin 路径都可用）；`trim()` 与网卡表正则统一改显式 `[ \\t\\r\\n]` / `[^ \\t:]`。VM 实测：`services list` 里 ddns/dbus/cryptdisks-early 名字完整 | **待真机装机验收**（看 ddnsto 是否出现 `"path"`） |
"""
t = io.open(P, encoding="utf-8").read()
io.open(P, "w", encoding="utf-8").write(t.rstrip() + "\n" + ROWS)
print("ok", len(io.open(P, encoding="utf-8").read()))
