# -*- coding: utf-8 -*-
"""README 追加 7.8 节：v1.2.57 实时网速 2 秒采样 + ddnsto 改原生菜单 + ucode 正则坑。"""
import io

P = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
SEC = u"""

---

## 7.8 v1.2.57：实时网速 2 秒采样（1900M 只测到 900 多）、ddnsto 改走原生 LuCI 菜单、ucode 正则 `\\s` 坑

### 7.8.1 现象与真因

Jason 报：本地实测 1900 Mbps，首页「实时网速」卡峰值只有 945.2 Mbps，且「我这边测完了，那边还刚开始」。截图：下载 0.25 MB/s、上传 2.00 MB/s，峰值 958 Mbps，折线只有左侧一根尖峰后贴地。

两个真因（都有代码依据）：

1. `athena-status.uc` 的 `rx_rate/tx_rate` 是「两次调用之间」的平均值，而页面 15 秒才轮询一次 → delta 窗口就是 15 秒。1900M 的 20 秒测速被摊进 15 秒窗口，峰值自然只剩 900 多；屏幕显示的又是「刚刚过去 15 秒的平均」，观感就是慢一拍。
2. `pushSpark` 是 15 秒一个点、留 60 点 = 15 分钟，卡片标题却写「最近 60 秒」，语义完全对不上。

### 7.8.2 改法（5 个文件）

| 文件 | 改动 |
|---|---|
| **新增** `athena-rate.uc` | 只读 `/proc/uptime` + `/proc/net/dev`，单次约 10ms。`uptime_cs()` 取百分之一秒（整秒精度会让 2 秒采样抖 ±50%）；`pick_if()` 固定单选一个接口（`pppoe-wan` → `wan` → `br-lan`，并沿用缓存里的接口名），避免跨接口差值变负；首采/换接口/计数器回绕只重置基准并报 0（带 `"primed":true`）；`dt<0.4s` 沿用上次值，避免炸出天文数字。缓存 `/tmp/.athena-rate` = `uptime_cs rx tx ifname rx_rate tx_rate` |
| `athena-status.sh` | 加 `rate` 分支 → `exec /usr/bin/ucode /usr/libexec/athena-rate.uc`。**故意走这个入口**：rpcd ACL 只认 `athena-status.sh` 一条，不必新增放行项（v1.2.56 就是栽在漏放行上） |
| `athena-status.uc` | 实时网速正则修正（见 7.8.3），`rx/tx` 字段保留但首页不再用 |
| `index.html` | `applyStatus()` 里 `if(d.network){…}` 整行注释；`loadStatus()` 去掉 `pushSpark`；新增 `loadRate()` + `_rateTimer`，`boot()` 里 `loadRate(); setInterval(loadRate,2000)`，回前台补一次；`pushSpark` 上限 60 → 30（2 秒×30 = 60 秒）；`drawSpark()` 的 `line()` 分母改按点数 `N` 动态，两个方向的峰值文字也挪到这里实时刷新；静态初值 `862.4`/`945.2`/`41.2`/`48.7` 改 `0.0`/`峰值 —` |
| `athena-services.uc` | 删掉 `KNOWN_UI`（不再给 ddnsto 官方控制台外链），`detect_path()` 加第三轮兜底：任何 `menu.d` 文件里只要出现过含 `base` 的 admin 路径就用它（不再要求文件名带 base）。端口探测只作最后兜底 |

### 7.8.3 顺手挖出的 ucode 正则坑（影响面比网速大）

VM 上用 staging 的 ucode（`staging_dir/hostpkg/bin/ucode`，VM 里没有 `/usr/bin/ucode`，这轮先踩了一次）实测：

```
rot  A trim旧式_ddns=[ddn]        # /[\\s\\r\\n]+$/ 把结尾字母 s 也裁掉了
     B trim新式_=[ddns]           # /[ \\t\\r\\n]+$/ 正确
     C 类内\\s_enp0s3=true        # /^[ \\t]*([^ \\t:]+):[ \\t]*(.+)$/ 命中
     D 类内\\s_老式=false         # /^\\s*([^\\s:]+):\\s*(.+)$/ 对 enp0s3 不命中
     E/G/H：`\\s` 在字符类**外**（`\\s+`、`MemTotal:\\s+(\\d+)`）工作正常
```

结论：ucode 的 **字符类内 `\\s` 被当成字面字母 `s`**。后果有两个：

1. `if_bytes()` 的网卡表正则匹配不到带 `s` 的接口名（`enp0s3`、`wwan0s1`…），只有 `lo`/`br-lan` 这类能过 —— 真机恰好是 `pppoe-wan` 才没暴露。
2. 三个文件里的 `trim()` 用 `[\\s\\r\\n]`，会把值结尾的 `s` 裁掉：`ddns` → `ddn`、`dbus` → `dbu`。**这很可能就是 ddnsto/ddns 菜单路径一直对不上的原因**（VM 复测 `athena-services.uc list`，服务名 `ddns`/`dbus`/`cryptdisks-early` 现在完整保留）。

已把 `athena-rate.uc`、`athena-services.uc`、`athena-status.uc` 的 `trim()` 与网卡表正则全部改成显式的 `[ \\t\\r\\n]` / `[^ \\t:]`。

### 7.8.4 编译机实测（rate.uc，先修完 bug 再测）

第一次运行报 `Reference error: left-hand side expression is null`（`rd()` 里 `fs.readfile`）——**漏了 `import * as fs from 'fs';`**，补上后通过。VM 无 `pppoe-wan`，拷一份候选接口换成 `enp0s3` 的同源副本测：

```
首采            {"ok":true,"if":"enp0s3","rx_mbps":0,"tx_mbps":0,"dt_ms":0,"primed":true}
sftp 拉 300MB   t1 {"ok":true,"if":"enp0s3","rx_mbps":7.0,"tx_mbps":129.0,"dt_ms":3550}
                t2 {"ok":true,"if":"enp0s3","rx_mbps":24.0,"tx_mbps":612.0,"dt_ms":2010}
静默           {"ok":true,"if":"enp0s3","rx_mbps":0.0,"tx_mbps":0.0,"dt_ms":2000}
0.2s 连打两次   dt_ms=10 / 210（<400ms 沿用上次值，没出现天文数字）
```

`athena-services.uc list` 在 VM 上跑通，服务名带 `s` 的（`ddns`、`dbus`、`cryptdisks-early`）均完整。

### 7.8.5 文件与安装（v1.2.57）

| 文件 | 设备路径 | 字节 | sha256 | CDN |
|---|---|---|---|---|
| index.html | `/www/luci-static/resources/view/athena/index.html`（644） | 306,752 | `5dd1e72e7f3f22edcd87fd5ca67e199adce3867159e4b47eb0f540b17c67b8d0` | https://aka.doubaocdn.com/s/jVZZfvfUUL |
| athena-rate.uc | `/usr/libexec/athena-rate.uc`（755，**新增**） | 4,336 | `9494ee7a514c7d9dc167d90056b956bebec6d80474dd54c60f1df5b8c0919b05` | https://aka.doubaocdn.com/s/DPpy8Gtkoh |
| athena-status.sh | `/usr/libexec/athena-status.sh`（755） | 1,329 | `dc3b3c1c12508e18d8c44dcdfca7716979b09ba4d8a2ad35cbae6c71f3cf8d0e` | https://aka.doubaocdn.com/s/9Lzo2BERk0 |
| athena-status.uc | `/usr/libexec/athena-status.uc`（755） | 23,794 | `c53ac0643ec26aecd440dc3d3bd75ff622ba8f31a60a0f9ee71ed9e2898e7f97` | https://aka.doubaocdn.com/s/K0libiUZLV |
| athena-services.uc | `/usr/libexec/athena-services.uc`（755） | 11,911 | `3c0fe62a9a79dbb0eab8e28f43ce9a2816f4d635394bc942669d1f6705b1d626` | https://aka.doubaocdn.com/s/qmAWHA2RCg |

**不需要动 ACL、不需要重启 rpcd**：rate 走的是已放行的 `athena-status.sh`。

安装（一条命令，用 `;` 自连接，绝对路径，不要换行）：

```
wget -qO- -T 30 https://aka.doubaocdn.com/s/jVZZfvfUUL >/tmp/i4.html;wget -qO- -T 30 https://aka.doubaocdn.com/s/DPpy8Gtkoh >/tmp/r4.uc;wget -qO- -T 30 https://aka.doubaocdn.com/s/9Lzo2BERk0 >/tmp/s4.sh;wget -qO- -T 30 https://aka.doubaocdn.com/s/K0libiUZLV >/tmp/u4.uc;wget -qO- -T 30 https://aka.doubaocdn.com/s/qmAWHA2RCg >/tmp/v4.uc;cp /tmp/i4.html /www/luci-static/resources/view/athena/index.html;cp /tmp/r4.uc /usr/libexec/athena-rate.uc;cp /tmp/s4.sh /usr/libexec/athena-status.sh;cp /tmp/u4.uc /usr/libexec/athena-status.uc;cp /tmp/v4.uc /usr/libexec/athena-services.uc;chmod 755 /usr/libexec/athena-rate.uc /usr/libexec/athena-status.sh /usr/libexec/athena-status.uc /usr/libexec/athena-services.uc;chmod 644 /www/luci-static/resources/view/athena/index.html;sha256sum /www/luci-static/resources/view/athena/index.html /usr/libexec/athena-rate.uc /usr/libexec/athena-status.sh /usr/libexec/athena-status.uc /usr/libexec/athena-services.uc;echo OK57
```

### 7.8.6 验收

真机功能验证（测速同时看这个，两个 2 秒采样之间应该出现接近 1900 的 rx_mbps）：

```
sh /usr/libexec/athena-status.sh rate;sleep 2;sh /usr/libexec/athena-status.sh rate;sh /usr/libexec/athena-services.sh list | grep -o '"id":"ddnsto"[^}]*'
```

通过标准：

1. 五个 sha256 与上表一致，末尾打印 `OK57`。
2. `rate` 两次输出 `dt_ms` 在 2000 左右；无流量时 0.0，跑测速时 `rx_mbps` 能到 1800~1900。
3. 首页「实时网速」2 秒跳一次，峰值贴着实际（不再卡在 900 多），测速结束曲线立刻回落。
4. `athena-services.sh list` 里 ddnsto 那一项出现 `"path":"admin/..."`，点「打开」进的是原生 LuCI 页面。
"""
t = io.open(P, encoding="utf-8").read()
io.open(P, "w", encoding="utf-8").write(t.rstrip() + SEC)
print("README bytes:", len(io.open(P, encoding="utf-8").read()))
