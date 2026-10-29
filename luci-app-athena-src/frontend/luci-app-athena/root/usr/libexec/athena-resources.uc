#!/usr/bin/env ucode
'use strict';
/*
 * athena-resources.uc - AthenaWrt 资源采集器（ucode 版，v1.2.44）
 *
 * 为什么换成 ucode：
 *   v1.2.42 的 shell 版一次采样触发 459 次 execve（146 个进程 × 3 个外部命令），
 *   真机实测 athena-resources.sh 单次 real 1.80s / user 1.69s。真正解析
 *   每个进程的 stat 只要 0.003s —— 贵在「起进程」不在「算力」。
 *   现在改成单个 ucode 程序：1 次 execve，所有文件读取与 JSON 组装都在进程内。
 *
 * 输出结构与 v1.2.43 完全一致（前端不用改）：
 *   {"cpu":{"total":0-100,"temp":c,"window":s},
 *    "memory":{"total_mb":n,"used_mb":n,"pct":0-100,"procs_mb":n,"other_mb":n},
 *    "procs":[{"pid":p,"name":"x","label":"…","desc":"…","cpu":x.x,"mem":x.x,"rss_mb":x.x,"prot":b}]}
 *
 * 缓存文件与 shell 版共用，保证与 athena-status.sh（概览页）口径一致、可随时回退：
 *   /tmp/athena-cpu-cache    "OLD_IDLE OLD_TOTAL OLD_UP OLD_PCT"（4 列整数，status.sh 也读）
 *   /tmp/athena-res-cache.ticks  首行 "UP|<uptime>"
 */

import * as fs from 'fs';

const CACHE     = '/tmp/athena-res-cache';
const CPU_CACHE = '/tmp/athena-cpu-cache';
const HZ        = 100;      /* Linux USER_HZ，本平台恒为 100 */
const PAGESIZE  = 4096;     /* 本平台恒为 4096 */

/* ---------- 小工具 ---------- */

function try_readfile(path) {
	try { return fs.readfile(path); } catch (e) { return null; }
}

function esc(s) {
	return replace(s ?? '', /[\\"]/g, c => c == '\\' ? '\\\\' : '\\"');
}

/* 有符号整数写法（ucode 数字是 double） */
function i(n) {
	return sprintf('%d', int(n ?? 0));
}

function f1(n) {
	return sprintf('%.1f', n ?? 0);
}

/* ---------- 1. CPU 总量 / 核数 / uptime ---------- */

let stat = try_readfile('/proc/stat') ?? '';

let cur_total = 0, cur_idle = 0, ncpu = 0;
for (let line in split(stat, '\n')) {
	let m = match(line, /^cpu(\d*)\s+(.*)$/);
	if (!m)
		continue;
	if (length(m[1]) == 0) {
		/* 总的 cpu 行：user nice system idle iowait irq softirq ... */
		let f = split(trim(m[2]), /\s+/);
		for (let k = 0; k < 7; k++)
			cur_total += int(f[k] ?? 0);
		cur_idle += int(f[3] ?? 0) + int(f[4] ?? 0);
	}
	else {
		ncpu++;
	}
}
if (ncpu <= 0)
	ncpu = 4;

let up_raw = 0;
{
	let u = match(try_readfile('/proc/uptime') ?? '', /^(\d+)/);
	if (u)
		up_raw = int(u[1]);
}
let now_up = up_raw;

/* ---------- 2. CPU 占用：与 status.sh 共用缓存，口径不变 ---------- */

let cpu_total = 0, cpu_win = 0, old_pct = 0, have_old = false;
{
	let txt = try_readfile(CPU_CACHE);
	if (txt) {
		let f = split(trim(txt), /\s+/);
		if (length(f) >= 4) {
			let old_idle = int(+f[0]), old_total = int(+f[1]),
			    old_up = int(+f[2]), old_p = int(+f[3]);
			let dt = cur_total - old_total;
			let di = cur_idle - old_idle;
			let win = now_up - old_up;
			have_old = true;
			old_pct = old_p;
			cpu_win = win;
			if (dt >= 80 && win >= 2)
				cpu_total = int((dt - di) * 100 / dt);
			else
				cpu_total = old_p;
		}
	}
	if (!have_old) {
		/* 首次无快照：按负载估算（与 shell 版一致） */
		let l = match(try_readfile('/proc/loadavg') ?? '', /^([\d.]+)/);
		let load1 = l ? +l[1] : 0;
		cpu_total = int(load1 / ncpu * 100);
	}
}
if (cpu_total > 100) cpu_total = 100;
if (cpu_total < 0)   cpu_total = 0;

/* 写回：4 列格式 IDLE TOTAL_TICKS UPTIME PCT —— 与 athena-status.sh 完全一致。
 * 注意第 2 列必须是「总 tick」而不是百分比：status.sh 用它算 DIFF_T，
 * v1.2.42/43 的 shell 版把百分比写进了这一列，结果两处都算成「开机以来累计均值」。 */
try {
	fs.writefile(CPU_CACHE, `${cur_idle} ${cur_total} ${now_up} ${cpu_total}\n`);
} catch (e) { }

/* ---------- 3. 温度（所有 thermal zone 取最高） ---------- */

let temp = 0;
{
	let zones = null;
	try { zones = fs.lsdir('/sys/class/thermal'); } catch (e) { zones = null; }
	if (zones)
		for (let z in zones) {
			if (substr(z, 0, 12) != 'thermal_zone')
				continue;
			let t = try_readfile(`/sys/class/thermal/${z}/temp`);
			let v = t ? int(trim(t)) : 0;
			if (v > temp) temp = v;
		}
}
temp = int(temp / 1000);

/* ---------- 4. 内存 ---------- */

let mem_total_kb = 0, mem_avail_kb = 0;
{
	let mi = try_readfile('/proc/meminfo') ?? '';
	let mt = match(mi, /MemTotal:\s+(\d+)/);
	let ma = match(mi, /MemAvailable:\s+(\d+)/);
	mem_total_kb = mt ? int(mt[1]) : 1;
	mem_avail_kb = ma ? int(ma[1]) : 0;
	if (mem_total_kb <= 0) mem_total_kb = 1;
}
let mem_used_kb = mem_total_kb - mem_avail_kb;
if (mem_used_kb < 0) mem_used_kb = 0;
let mem_pct = int(mem_used_kb * 100 / mem_total_kb);

/* ---------- 5. 遍历 /proc/<pid>/stat ---------- */

let procs = [];          /* {pid, name, ticks, rss_kb} */
let procs_kb = 0;

{
	let entries = null;
	try { entries = fs.lsdir('/proc'); } catch (e) { entries = null; }

	if (entries)
		for (let e in entries) {
			if (!match(e, /^\d+$/))
				continue;

			let raw = try_readfile(`/proc/${e}/stat`);
			if (!raw)
				continue;

			/* comm 可能含空格/括号：贪婪匹配到「最后一个 ')'」 */
			let m = match(raw, /^(\d+) \((.*)\) (.*)$/);
			if (!m)
				continue;

			let rest = trim(m[3]);
			let f = split(rest, /\s+/);
			if (length(f) < 22)
				continue;

			let ticks = int(f[11] ?? 0) + int(f[12] ?? 0);   /* utime + stime */
			let rss   = int(f[21] ?? 0) * PAGESIZE / 1024;   /* 页 → KB */

			/* 内核线程判定：cmdline 为空 = 没有用户态代码。
			 * 比按名字正则可靠（kblockd/scsi_eh_0/md… 这些名字正则都漏掉了）。
			 * v1.2.54：不再直接丢弃，而是标 kth:true 返回——前端默认隐藏，
			 * 用户在「资源占用」卡片打开「显示内核线程」开关时才展示。 */
			let cmdline = try_readfile(`/proc/${e}/cmdline`);
			let kth = (cmdline == null || length(cmdline) == 0);

			push(procs, { pid: int(m[1]), name: m[2], ticks: ticks, rss_kb: rss, kth: kth });
			procs_kb += rss;
		}
}

/* ---------- 6. 进程 CPU%：Δticks / HZ / 核数 / 实际经过秒 ---------- */

let elapsed = 0;
{
	let old_ticks = {};
	let old_up = null;
	let txt = try_readfile(`${CACHE}.ticks`);

	if (txt)
		for (let line in split(trim(txt), '\n')) {
			if (line == '') continue;
			let p = split(line, '|');
			if (p[0] == 'UP') { old_up = +p[1]; continue; }
			old_ticks[p[0]] = int(p[1] ?? 0);
		}

	if (old_up != null) {
		elapsed = up_raw - old_up;
		if (elapsed < 1 || elapsed > 300)
			elapsed = 0;
	}

	for (let p in procs) {
		let d = p.ticks - (old_ticks[`${p.pid}`] ?? 0);
		let c = 0;
		if (elapsed > 0 && d > 0) {
			c = d / HZ / ncpu / elapsed * 100;
			if (c > 100) c = 100;
		}
		p.cpu = c;
		p.mem = mem_total_kb > 0 ? p.rss_kb / mem_total_kb * 100 : 0;
	}

	/* 更新快照：时间与数据同一文件，避免两份缓存不同步 */
	let buf = `UP|${up_raw}\n`;
	for (let p in procs)
		buf += `${p.pid}|${p.ticks}\n`;
	try { fs.writefile(`${CACHE}.ticks`, buf); } catch (e) { }
	/* 老版 CACHE.now 只被本脚本使用，这里清掉避免残留误导 */
	try { fs.unlink(`${CACHE}.now`); } catch (e) { }
}

let other_kb = mem_used_kb - procs_kb;
if (other_kb < 0) other_kb = 0;

/* ---------- 7. 名称/用途映射（与 v1.2.43 的 awk 版逐条对齐） ---------- */

const KTH_RE = /^(kworker|ksoftirqd|napi\/|irq\/|migration\/|cpuhp\/|kthreadd|kswapd|oom_reaper|watchdogd|pool_workqueue|rcu_|kcompactd|spi0|askfirst)/;

function is_kth(n) { return match(n, KTH_RE) != null; }

function lab(n) {
	if (match(n, /^athena-/))                              return '雅典娜后台服务';
	if (is_kth(n)) return match(n, /^(kthreadd|ksoftirqd)/) ? '内核调度线程' : '内核后台任务';
	if (n == 'netifd')                                     return '网络服务';
	if (n == 'odhcpd')                                     return '地址分配服务';
	if (n == 'dnsmasq')                                    return 'DNS 与地址分配';
	if (n == 'ubusd')                                       return '系统消息中心';
	if (match(n, /^(uhttpd|lighttpd|luci)/))                return 'Web 管理界面';
	if (n == 'rpcd')                                        return '后台管理接口';
	if (n == 'logd')                                        return '系统日志服务';
	if (n == 'dropbear')                                    return '远程登录服务';
	if (match(n, /^ppp/))                                   return '宽带拨号服务';
	if (n == 'hostapd')                                     return 'WiFi 服务';
	if (n == 'wpa_supplicant')                              return 'WiFi 客户端';
	if (match(n, /^(crond|busybox-cron)$/))                 return '定时任务服务';
	if (match(n, /^(ntpd|chronyd|systemd-timesyncd)$/))     return '时间同步服务';
	if (n == 'odhcp6c')                                     return 'IPv6 获取服务';
	if (match(n, /^(ash|sh|bash)$/))                        return '命令脚本';
	if (match(n, /^(curl|wget)$/))                          return '网络工具';
	if (n == 'busybox')                                     return '系统基础工具';
	return '后台进程';
}

function dsc(n) {
	if (match(n, /^athena-/))                              return 'AthenaWrt 管理功能';
	if (is_kth(n)) return match(n, /^(kthreadd|ksoftirqd)/) ? '内核调度（可忽略）' : '系统底层任务（可忽略）';
	if (n == 'netifd')                                     return '管理网口与上网连接';
	if (n == 'odhcpd')                                     return '给手机/电脑分配 IP';
	if (n == 'dnsmasq')                                    return '上网域名解析 + IP 分配';
	if (n == 'ubusd')                                      return '系统内部通信（可忽略）';
	if (match(n, /^(uhttpd|lighttpd|luci)/))               return '运行后台管理页面';
	if (n == 'rpcd')                                       return '向管理界面提供数据';
	if (n == 'logd')                                       return '记录系统运行日志';
	if (n == 'dropbear')                                   return '允许 SSH 远程登录';
	if (match(n, /^ppp/))                                  return '宽带账号拨号连接';
	if (n == 'hostapd')                                    return '管理无线网络（WiFi）';
	if (n == 'wpa_supplicant')                             return '连接外部无线网络';
	if (match(n, /^(crond|busybox-cron)$/))                return '按计划执行定时任务';
	if (match(n, /^(ntpd|chronyd|systemd-timesyncd)$/))    return '自动校准系统时间';
	if (n == 'odhcp6c')                                    return '自动获取 IPv6 地址';
	if (match(n, /^(ash|sh|bash)$/))                       return '执行系统脚本';
	if (match(n, /^(curl|wget)$/))                         return '下载与测速工具';
	if (n == 'busybox')                                    return '系统常用命令集合';
	return '系统或应用进程';
}

function prot(n) {
	return match(n, /^(wpad|hostapd|hostapd_cli|netifd|dnsmasq|odhcpd|odhcp6c|ubusd|rpcd|uhttpd|lighttpd|dropbear|logd|syslogd|pppd|pppoe.*)$/) != null;
}

/* ---------- 8. 排序（按内存占比降序，与 shell 版 sort -k4 -rn 一致） + 组装 ---------- */

sort(procs, (a, b) => b.mem - a.mem);

let out = sprintf('{"cpu":{"total":%s,"temp":%s,"window":%s},', i(cpu_total), i(temp), i(cpu_win));
out += sprintf('"memory":{"total_mb":%s,"used_mb":%s,"pct":%s,"procs_mb":%s,"other_mb":%s},"procs":[',
	i(mem_total_kb / 1024), i(mem_used_kb / 1024), i(mem_pct),
	i(procs_kb / 1024), i(other_kb / 1024));

let first = true;
for (let p in procs) {
	/* 空名进程（内核掉队的无名线程）直接跳过；内核线程带 kth 标记输出，由前端决定是否显示 */
	if (p.name == '')
		continue;
	if (!first)
		out += ',';
	first = false;
	out += sprintf('{"pid":%s,"name":"%s","label":"%s","desc":"%s","cpu":%s,"mem":%s,"rss_mb":%s,"prot":%s%s}',
		i(p.pid), esc(p.name), esc(lab(p.name)), esc(dsc(p.name)),
		f1(p.cpu), f1(p.mem), f1(p.rss_kb / 1024), prot(p.name) ? 'true' : 'false',
		p.kth ? ',"kth":true' : '');
}
out += ']}';

print(out, '\n');
