# -*- coding: utf-8 -*-
import io

p = r"C:\Users\Administrator\Doubao\chats\2026-10-27\new-chat-11\hotfix2\README.md"
t = io.open(p, encoding="utf-8").read()

t = t.replace("| `sh /usr/libexec/athena-disk.sh list` | 返回含 `\"mounted\":false` / `\"parts_count\":11` / `\"parts\":[…]` |",
              "| `sh /usr/libexec/athena-disk.sh list` | 返回含 `\"mounted\":false` / `\"parts_count\":13`（真机实测 13 个分区）/ `\"parts\":[…]` |")

add = r"""

## 6. 首次真机上机结果（2026-10-28 22:05）

**七个文件全部落地，hash 逐条对上**（`sha256sum /tmp/i.html /tmp/d.sh /tmp/l.sh /tmp/r.uc /tmp/s.uc /tmp/c.sh /tmp/a.sh`）：

```
ddfa4510…  i.html      bccac26a…  d.sh       021aea87…  l.sh       e11f6e09…  r.uc
8cde41b5…  s.uc        b31ecbb4…  c.sh       6f287600…  a.sh
```

`INSTALL-DONE` 已打印，`/usr/libexec/athena-*` 已 chmod 755。

| 项 | 真机结果 | 结论 |
|---|---|---|
| `athena-disk.sh list` | `mounted:false`、`parts_count:13`、`parts[]` 列出 p4/p5/p16…p27（p27 = 114,219 MB 是那块大用户分区，未挂载） | ✅ 新字段生效；**这台机器是 13 个分区，不是早前记录的 11 个** |
| `athena-log.sh list` | 真实 logread 直接出四段：`10-15 21:41:31 | warn | odhcpd | A default route is present…`、`… | info | netifd | wan (2946): udhcpc…` | ✅ 时间解析修正有效（旧版会把这种行算成 `10-15` 之外的怪值） |
| `athena-services.uc` | 用 `sh` 跑报 `//: Permission denied` + `syntax error: unexpected "("` | ⚠️ **`.uc` 是 ucode 脚本，不能用 sh 执行**；正确入口是 `sh /usr/libexec/athena-services.sh list`（内部 `/usr/bin/ucode`） |
| cron | `grep: /etc/crontabs/root: No such file or directory` | ⚠️ 上机前这台机器**根本没有 crontab 文件**；`||` 分支已把它创建，但需确认 crond 是否在跑 |

### 6.1 上机后要补的两件事

1. **cron 自愈**（若 `ps | grep -c crond` 为 0）：

```sh
/etc/init.d/cron enable;/etc/init.d/cron start
```

`/etc/crontabs/root` 应为：

```
* * * * * /usr/libexec/athena-logcap.sh >/dev/null 2>&1
```

2. **`.uc` 一律别用 sh 跑**：`athena-services.uc` / `athena-resources.uc` / `athena-status.uc` 都是 ucode；手工验证走各自的 `.sh` 入口。

### 6.2 正确的真机自检命令

```sh
sh /usr/libexec/athena-disk.sh list
sh /usr/libexec/athena-log.sh list | head -c 300
sh /usr/libexec/athena-services.sh list | grep -o '"id":"ddnsto"[^}]*'
sh /usr/libexec/athena-logcap.sh;ls -l /tmp/dnsmasq.log;grep -E '^(Shmem|MemFree)' /proc/meminfo
```
"""

io.open(p, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + add)
print("ok")
