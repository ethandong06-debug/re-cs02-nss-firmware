# -*- coding: utf-8 -*-
import io

p = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
t = io.open(p, encoding="utf-8").read().rstrip("\n")

add = r"""

---

# v1.2.54 · 清单第 1~5 项收尾（存储 0 MB / 服务打开 / 卡片排序 / 日志四列 / 内核线程开关）

一句话：把 Jason 列的缺陷清单里剩下的 5 条一起改完，连同 v1.2.53 的「日志限额 2MB」一起热替换。**本条所有文件都已编译进 1.2.54 的 apk，也都能单独热替换。**

apk：`luci-app-athena-1.2.54-r1.apk`（14,673,942 B，`PKG_VERSION:=1.2.54`，`athena-version`=1.2.54）

## 1. 逐条根因（真机 + 代码双向取证）

| # | 现象 | 根因 | 取证 |
|---|---|---|---|
| ① | 磁盘「已用 0 MB / 115.2 GB (0%)」永远是 0 | 整盘 overlay：`/` = `overlayfs:/tmp/root`，`/rom` = `/dev/root`（squashfs），**没有任何 `mmcblk0pN` 被直接挂载**；旧 `athena-disk.sh list` 靠 `/proc/mounts` 反查分区，必然全落空 → size 走 `/sys`、used 恒 0 | 真机 `/proc/mounts`、`df -h`；`/sys/block` 有 `mmcblk0 + p0..p11` |
| ② | 第三方服务（ddnsto 等）没有「打开」按钮 | ①详情弹窗用静态假表 `SVC_DETAIL`（`pid:"3108"` / `mem:"18 MB"` / `ver:"v2.31.0"` 全写死），第三方不在表里；②列表「打开」条件只看 `s.path`，只有 ddns / ttyd 能从 `menu.d` 拿到 path | 真机 `menu.d` 只有 11 个 JSON；`athena-services.sh list` 里第三方全部 `desc:"第三方服务"` 且无 path |
| ③ | 排序弹窗只弹一句「固定顺序」，保存后卡片不动 | `openSortModal` 被**同名覆盖定义**顶掉——1400 行处的真实现（上移/下移 + 保存）被后段一句说明框替换；`saveSort` 也只重排 DOM 不入库 | `grep -n openSortModal` 两处定义；CDP 实测点保存后 `#kpiGrid` 子节点顺序不变 |
| ④ | 日志四列不齐、像一坨裸文本 | `athena-log.sh` 原样 `logread` 输出；前端 `log-line` / `log-list` / `log-chip` / `log-search` / `log-toolbar` 五个类**在样式表里根本没定义** | 样式表全量 grep 五个类名 0 命中 |
| ⑤ | 资源列表看不到内核线程（吃 CPU 的 sugov / ksoftirqd 找不到） | `athena-resources.uc` 把 `cmdline` 为空的内核线程**直接丢弃** | 真机 `top` 里 `sugov:0` 137.8%、页面列表里没有 |

内存那条独立结论（沿用 v1.2.53）：SUnreclaim 155,836 kB 是 NSS/ECM/ath11k 的内核对象，进程侧全机只占 19 MB——所以「资源列表里找不到吃 40% 的进程」不是 bug。

## 2. 改法（6 个文件）

| 文件 | 改了什么 |
|---|---|
| `athena-disk.sh` | `list` 重写：物理容量取 `/sys/block/<dev>/size`；新增 `mounted`（布尔）、`parts_count`、`parts[]`（分区名/容量/挂载点/fs，未挂载给空串）；`used_mb` 只累加真正挂载的分区 |
| `athena-services.uc` | 新增 `KNOWN_UI`（`ddnsto` → `https://www.ddnsto.com/`，确定值不猜）+ `detect_port()`（从 `/etc/init.d/<base>` 匹配 `-p` / `--port` / `-port`，取 2–5 位端口）；输出新增 `"port"` / `"url"` |
| `athena-resources.uc` | 内核线程打 `"kth":true` 后随 JSON 返回（不再丢弃，仍计入 `procs_mb`） |
| `athena-log.sh` | 整体重写：awk 找 `facility.level` → 输出 `time|level|module|msg`；时间兼容「Fri Oct 28 20:12:00 2026」与「Oct 28 21:00:00」两种 logread 格式（月名表换算成 `10-28`）；内核行剥 `[ 88.123]` 前缀；解析失败退回原始整行；`head -300` |
| `athena-apps.sh` | 每次调用顺手跑一次 `athena-logcap.sh`（v1.2.53 已有，本轮同批复用） |
| `index.html` | ①`renderDisksRows` 未挂载时显示「容量 115.2 GB · 分区未挂载（overlay 运行在内存）」，进度条置 0；②删掉 `SVC_DETAIL` 整块；`svcRowHTML` 的 openable 改 `path‖url‖port`，`renderSvcBox` 分组口径改「有网页入口（N）」/「其他第三方服务（M）· 无网页入口」，`openSvcWin` 三档（LuCI 菜单内嵌 / 本机端口 iframe / 官方控制台新窗口）+ 底部「新窗口」，`openSvcPage` 对官方控制台走 `window.open`；③删掉覆盖版 `openSortModal`，新增 `KPI_ORDER` / `applyKpiOrder` / `loadKpiOrder` / `saveKpiOrder`（写在 `KPI_ITEMS` 所在作用域，远端写入走 `window.__kpiRemoteSave` 钩子），`boot()` 加 `loadKpiOrder + loadKpiOrderRemote`；④日志四列 grid CSS（`104px 44px 96px minmax(0,1fr)`）+ 级别中文化色块（错误红/警告橙/信息灰/调试灰）+ 窄屏收缩 + 悬浮看全文，`logRender` 改四列、搜索同时匹配模块与正文；⑤资源卡头加「显示内核线程」开关，默认按 `kth` + 兜底正则过滤，提示「已隐藏 N 个内核线程」，内核组只给灰色「内核」标签、不给重启/停止，状态双存 localStorage + `athena-prefs.sh` |

## 3. 验证记录

| 层 | 做法 | 结果 |
|---|---|---|
| 前端语法 | 三个 `<script>` 块分别抽出跑 `node --check` | 3/3 通过（50,862 / 130,557 / 1,468 字符） |
| 后端语法 | sftp 上传到编译机 `sh -n` | `athena-disk.sh` / `athena-log.sh` 均通过 |
| 后端实跑 | compilestage 的 `staging_dir/hostpkg/bin/ucode` 直接跑 | `athena-resources.uc` 输出含 `"kth":true`；`athena-services.uc` 正常出 29 条 |
| 日志解析 | 假 `logread` 喂 7 行：两种时间格式 + 内核 `[12345.678]` / `[  88.123]` + 一条非标准行 | 全部正确分列；非标准行退回原始整行且级别仍判 err；`list err` 与 `list all dnsmasq` 过滤正确 |
| 磁盘 | VM 上 `athena-disk.sh list` | 返回 `sda 307200 MB mounted:false`（新字段生效） |
| 前端渲染 | Chrome `--headless=new` + CDP + mock `fetch('/ubus/')`，真走登录 → 高级页 → 点弹窗；6 张截图逐一核对 | 存储卡文案正确；服务卡「有网页入口（4）」含 filebrowser / ddnsto 且都有打开按钮；日志四列对齐；排序弹窗是真弹窗（4 行 + 上移下移 + 保存）；内核线程默认隐藏 3 条 + 提示，开关打开后 `sugov:0 37.8%` 出现且无操作按钮 |
| 排序持久化 | CDP 点「下移 CPU」→「保存」 | `#kpiGrid` 变 `kpi-mem,kpi-cpu,kpi-up,kpi-dev`；`localStorage.athena_kpi_order = "mem,cpu,up,dev"`；路由端收到 `athena-prefs.sh set kpi_order mem,cpu,up,dev` |
| 包内一致 | `make package/luci-app-athena/clean` 后全量重编 | staging 里 7 个文件 sha256 与本地逐字节一致（见下表完整 hash） |

> 踩坑记录：页面脚本整体包在 IIFE 里，`_RES` / `renderResBox` 在全局 `typeof` 都是 undefined；只改全局变量做「打桩」全是假象。必须 mock `fetch('/ubus/')` 让页面真走登录与 `boot()`，截图才可信。

## 4. 热替换（7 个文件，1.2.54）

| 文件 | 设备路径 | 字节 | sha256 | 下载 |
|---|---|---|---|---|
| `index.html` | `/www/luci-static/resources/view/athena/` | 303,186 | `ddfa45103f7b8bd9…` | https://aka.doubaocdn.com/s/VFf1Q7tzoK |
| `athena-disk.sh` | `/usr/libexec/` | 4,403 | `bccac26a0714eca7…` | https://aka.doubaocdn.com/s/gMu6ExomU0 |
| `athena-log.sh` | `/usr/libexec/` | 4,240 | `021aea8720deaf1f…` | https://aka.doubaocdn.com/s/Q0gjIaXfi4 |
| `athena-resources.uc` | `/usr/libexec/` | 12,182 | `e11f6e098457c048…` | https://aka.doubaocdn.com/s/nRHsimfLKD |
| `athena-services.uc` | `/usr/libexec/` | 10,456 | `46be24ddff69e7ec…` | https://aka.doubaocdn.com/s/qQS9UuaCLY |
| `athena-logcap.sh`（v1.2.53 延用） | `/usr/libexec/` | 1,811 | `b31ecbb4902dc4a9…` | https://aka.doubaocdn.com/s/Jn8hZdB9rn |
| `athena-apps.sh`（v1.2.53 延用） | `/usr/libexec/` | 9,286 | `6f287600e7e99f9d…` | https://aka.doubaocdn.com/s/ZZCw9hpwWU |

完整 sha256：

```
ddfa45103f7b8bd9776045c319da5043af8b3dbae4351881e967fee4599b7538  index.html
bccac26a0714eca7a3a72eb9b54d056e8a826d4c4e5d02ea8e340272b2ff1511  athena-disk.sh
021aea8720deaf1fafc27cfeba9c79c47efa231ff8a9e3b8c72e773db1229b5a  athena-log.sh
e11f6e098457c04811ddc8c598c9c6e470ec7636aa305a2394ce4f3dca0704dc  athena-resources.uc
46be24ddff69e7ecd1c0e47b63d602c47523a2a06675bb157a9db3b49c22b126  athena-services.uc
b31ecbb4902dc4a993b6c82097be4fa28466fdf230310943da8005fd5a67e864  athena-logcap.sh
6f287600e7e99f9d71fe2c53804c31c8c30b712118b115a0e7090a5963cfe6c0  athena-apps.sh
```

装机命令（**一行一条，全部短行**；串口折行不会再把参数吃掉）：

```sh
cd /tmp
echo "[1/3] 下载 7 个文件"
wget -O i.html "https://aka.doubaocdn.com/s/VFf1Q7tzoK"
wget -O d.sh "https://aka.doubaocdn.com/s/gMu6ExomU0"
wget -O l.sh "https://aka.doubaocdn.com/s/Q0gjIaXfi4"
wget -O r.uc "https://aka.doubaocdn.com/s/nRHsimfLKD"
wget -O s.uc "https://aka.doubaocdn.com/s/qQS9UuaCLY"
wget -O c.sh "https://aka.doubaocdn.com/s/Jn8hZdB9rn"
wget -O a.sh "https://aka.doubaocdn.com/s/ZZCw9hpwWU"
ls -l i.html d.sh l.sh r.uc s.uc c.sh a.sh
echo "[2/3] 校验"
sha256sum i.html d.sh l.sh r.uc s.uc c.sh a.sh
echo "[3/3] 替换"
cp i.html /www/luci-static/resources/view/athena/index.html
cp d.sh /usr/libexec/athena-disk.sh
cp l.sh /usr/libexec/athena-log.sh
cp r.uc /usr/libexec/athena-resources.uc
cp s.uc /usr/libexec/athena-services.uc
cp c.sh /usr/libexec/athena-logcap.sh
cp a.sh /usr/libexec/athena-apps.sh
chmod 755 /usr/libexec/athena-*
chmod 644 /www/luci-static/resources/view/athena/index.html
rm -f /tmp/athena-status.json /tmp/athena-apps.cache
```

cron 那条（v1.2.53 起需要，幂等，重复执行安全）：

```sh
grep -q athena-logcap /etc/crontabs/root 2>/dev/null || echo '* * * * * /usr/libexec/athena-logcap.sh >/dev/null 2>&1' >> /etc/crontabs/root; /etc/init.d/cron restart
```

> `athena-log.sh` 有两条必须核对 hash 的：`021aea87…`（4,240 B）。早期 3,762 B 版是旧的时间解析（只认一种 logread 格式），已作废。

## 5. 验收判据（真机）

| 命令 | 期望 |
|---|---|
| `ls -l /tmp/dnsmasq.log`（装完等 1 分钟） | 从 31MB 降到约 1.5–1.6MB |
| `grep -E '^(Shmem|MemAvailable)' /proc/meminfo` | Shmem 从 94,508 kB 降到约 6.6 万 kB |
| `sh /usr/libexec/athena-log.sh list` | 返回 `{"ok":true,"logs":[{"time":"10-28 20:12:00","level":"info","module":"dnsmasq","msg":"…"}]}`，四字段齐全 |
| `sh /usr/libexec/athena-disk.sh list` | 返回含 `"mounted":false` / `"parts_count":11` / `"parts":[…]` |
| `sh /usr/libexec/athena-services.sh list` | ddnsto 带 `"url":…`，filebrowser 带 `"port":8081` |
| 页面：存储卡 | 「容量 115.2 GB · 分区未挂载（overlay 运行在内存）」，不再 0 MB |
| 页面：服务卡 | 「有网页入口（4）」，ddnsto / filebrowser 都有「打开」 |
| 页面：指标卡排序 | 下移后点保存，首页立刻重排；刷新后保持 |
| 页面：系统日志 | 四列对齐，级别带色块，长文本单行省略 + 悬浮看全文 |
| 页面：资源占用 | 默认不显示 kworker/sugov；右上角开关打开后出现，且这类行只有灰色「内核」标签、没有重启/停止 |
"""

io.open(p, "w", encoding="utf-8", newline="\n").write(t + add)
print("ok")
