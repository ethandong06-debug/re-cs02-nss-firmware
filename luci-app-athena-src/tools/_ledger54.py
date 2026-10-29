# -*- coding: utf-8 -*-
import io

p = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\AthenaWrt-待修问题记录.md"
t = io.open(p, encoding="utf-8").read()

old27 = "| 27 | 界面缩放/网速单位刷新后回默认 | uci commit athena 报 Invalid argument，配置写不进 /etc/config | v1.2.52：新增 athena-prefs.sh（/etc/athena-prefs.conf 权威存储），zoom/unit 写文件，uci 仅镜像 | 编译机通过，待真机验收 |"
new27 = "| 27 | 界面缩放/网速单位刷新后回默认 | uci commit athena 报 Invalid argument，配置写不进 /etc/config | v1.2.52：新增 athena-prefs.sh（/etc/athena-prefs.conf 权威存储），zoom/unit 写文件，uci 仅镜像 | 真机通过：zoom=115 / unit=MB/s 读回一致 |"
assert old27 in t, "27 行未匹配"
t = t.replace(old27, new27)

add = """

| 31 | 磁盘卡「已用 0 MB / 115.2 GB (0%)」永远是 0 | 整盘 overlay：`/` = overlayfs:/tmp/root，`/rom` = /dev/root(squashfs)，没有任何 mmcblk0pN 被直接挂载；旧 `athena-disk.sh list` 靠 /proc/mounts 反查分区，必然全落空，于是 size 走 /sys、used 恒为 0 | v1.2.54：`list` 改由 /sys/block/<dev>/size 取物理容量，新增 `mounted` / `parts_count` / `parts[]`（分区名·容量·挂载点·fs），`used_mb` 只累加真正挂载的分区；前端未挂载时显示「容量 115.2 GB · 分区未挂载（overlay 运行在内存）」，进度条置 0 | 编译机 `sh -n` 过、VM 实跑返回 mounted:false；前端 CDP 渲染截图核对通过 |
| 32 | 第三方服务（ddnsto 等）没有「打开」按钮 | ①详情弹窗用静态假表 SVC_DETAIL（pid 3108 / 内存 18 MB / v2.31.0 全是写死值），第三方不在表里；②列表「打开」条件只看 `s.path`，而只有 ddns/ttyd 能从 menu.d 拿到 path | v1.2.54：删掉 SVC_DETAIL 整块；`athena-services.uc` 新增 KNOWN_UI（ddnsto → 官方控制台）+ detect_port()（从 /etc/init.d/<svc> 抓 -p/--port，2–5 位端口），输出新增 `port` / `url`；前端 openable 改 (path‖url‖port)，openSvcWin 三档（LuCI 菜单内嵌 / 本机端口 iframe / 官方控制台新窗口），底部加「新窗口」；分组口径改「有网页入口（N）」/「其他第三方服务（M）· 无网页入口」 | 编译机 ucode 实跑 29 条正常；CDP 截图：filebrowser(8081)、ddnsto 都进了「有网页入口（4）」并有打开按钮 |
| 33 | 指标卡排序弹窗只弹一句说明，保存后卡片不动 | openSortModal 被后段同名覆盖定义顶掉（真实现 1400+ 行处被一句「固定顺序」说明框替换）；saveSort 也只重排 DOM 不入库 | v1.2.54：删除覆盖定义；新增 KPI_ORDER / applyKpiOrder / loadKpiOrder / saveKpiOrder（写在 KPI_ITEMS 所在作用域），localStorage + athena-prefs.sh 双存，远端写入走 window.__kpiRemoteSave 钩子；boot() 增加 loadKpiOrder + loadKpiOrderRemote | CDP 实测：下移 CPU 后保存 → 首页 grid 变为 mem,cpu,up,dev，localStorage=`mem,cpu,up,dev`，路由端收到 `athena-prefs.sh set kpi_order mem,cpu,up,dev` |
| 34 | 系统日志四列不齐（时间/级别/模块/正文挤成一坨） | `athena-log.sh` 原样输出 logread 文本；前端 `log-line` / `log-list` / `log-chip` / `log-search` / `log-toolbar` 五个类在样式表里根本没定义 | v1.2.54：后端 awk 解析 facility.level 输出 `time|level|module|msg`（时间兼容「Fri Oct 28 20:12:00 2026」与「Oct 28 21:00:00」两种 logread 格式，内核行剥 [ 88.123] 前缀，解析失败退回原始行）；前端新增 grid 四列 CSS + 级别中文化色块（错误红/警告橙/信息灰/调试灰）+ 窄屏列宽收缩 + 悬浮看全文；搜索同时匹配模块与正文 | 编译机用假 logread 喂 7 行（含两种格式、内核行、非标准行）全部正确分列；CDP 截图四列对齐 |
| 35 | 资源占用列表看不到内核线程（找不到吃 CPU 的 sugov/ksoftirqd） | `athena-resources.uc` 把 cmdline 为空的内核线程直接丢弃 | v1.2.54：后端打 `"kth":true` 随 JSON 返回（仍计入 procs_mb）；前端卡头加「显示内核线程」开关（默认关），二次兜底正则过滤 kworker/ksoftirqd/irq/sugov/migration/rcu_/napi 等，提示「已隐藏 N 个内核线程」，内核组只给灰色「内核」标签、不给重启/停止按钮；状态双存 localStorage + athena-prefs.sh | 编译机 ucode 实跑确认 kth 字段；CDP 截图：默认隐藏 3 条 + 提示，开关打开后 sugov:0 37.8% 出现且无操作按钮 |
"""
t = t.rstrip("\n") + add
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("ok")
