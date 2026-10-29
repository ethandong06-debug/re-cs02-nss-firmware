#!/usr/bin/ucode
// AthenaWrt 状态聚合采集器（ucode 版，v1.2.45）
// 替代 athena-status.sh：把系统/CPU/内存/网速/无线/存储/端口/设备/点阵屏/WAN 一次聚合成 JSON。
//
// 为什么要重写：shell 版有 130 处命令替换（$( )）、32 处 awk、14 处 cat，单次执行要 fork
// 约 400 个进程，真机实测 real 1.41s / user 1.34s，页面 15 秒一刷就把 CPU 吃到 2~23%。
// 重写后所有 /proc、/sys、/etc 数据都在本进程内直接读，只有必须跟内核/驱动打交道的
// 少数几处（uci show、ubus call、iwinfo）才 exec，fork 数从 ~400 降到 ~10。
//
// 与 shell 版保持完全一致的外部行为：
//   1) 3 秒结果缓存 /tmp/athena-status.json + /tmp/athena-status.stamp
//   2) 并发合并锁 /var/run/athena-status.lock（另加 20 秒僵死锁清理）
//   3) CPU 采样缓存 /tmp/athena-cpu-cache（IDLE TOTAL UPTIME PCT，与资源卡共用）
//   4) 网络速率缓存 /tmp/athena-net-cache（NOW_S RX TX）
//   5) 设备在线状态 /tmp/athena-devs（mac first_seen last_down）
//   6) 输出 JSON 的字段名、类型、顺序与 shell 版逐字一致

import * as fs from 'fs';

const SCACHE = '/tmp/athena-status.json';
const SSTAMP = '/tmp/athena-status.stamp';
const SLOCK = '/var/run/athena-status.lock';
const CPU_CACHE = '/tmp/athena-cpu-cache';
const NET_CACHE = '/tmp/athena-net-cache';
const DEVSTATE = '/tmp/athena-devs';

// ---------- 通用小工具 ----------
function rd(p) {
	let s = fs.readfile(p);
	return (s == null) ? '' : s;
}

function trim(s) {
	s = (s == null) ? '' : ('' + s);
	s = replace(s, /^[ \t\r\n]+/, '');
	s = replace(s, /[ \t\r\n]+$/, '');
	return s;
}

function to_int(v, def) {
	if (v == null) return def;
	let s = trim('' + v);
	if (s == '' || !match(s, /^-?\d+/)) return def;
	return int(s);
}

// JSON 字符串转义：与 shell 版 json_str() 完全等价（反斜杠、双引号、制表符，去掉回车）
function jstr(v) {
	let s = (v == null) ? '' : ('' + v);
	s = replace(s, /\\/g, '\\\\');
	s = replace(s, /"/g, '\\"');
	s = replace(s, /\t/g, '\\t');
	s = replace(s, /\r/g, '');
	return s;
}

function lower_hex(s) {
	return replace(s, /[A-F]/g, function (c) { return substr('abcdef', index('ABCDEF', c), 1); });
}

function upper_hex(s) {
	return replace(s, /[a-f]/g, function (c) { return substr('ABCDEF', index('abcdef', c), 1); });
}

// 按空白切分并压缩连续空白（等价 awk 默认的字段切分）
function fields(line) {
	line = trim(line);
	if (line == '') return [];
	return split(replace(line, /[ \t]+/g, ' '), ' ');
}

function uptime_f() {
	let p = fields(rd('/proc/uptime'));
	return (length(p) > 0) ? int(p[0]) : 0;
}

function now_epoch() {
	let btime = 0;
	for (let line in split(rd('/proc/stat'), '\n')) {
		let m = match(line, /^btime\s+(\d+)/);
		if (m) { btime = int(m[1]); break; }
	}
	return btime + uptime_f();
}

// ---------- 1) 3 秒缓存 + 并发锁 ----------
let cached = rd(SCACHE);
if (length(cached) > 0) {
	let st = trim(rd(SSTAMP));
	if (st != '' && (uptime_f() - int(st)) < 3) {
		printf('%s', cached);
		exit(0);
	}
}

// 僵死锁清理：shell 版靠 trap EXIT 删锁，进程被 SIGKILL 时锁会残留；这里超过 20 秒直接摘掉
let lstat = fs.stat(SLOCK);
if (lstat && (time() - lstat.mtime) > 20) fs.rmdir(SLOCK);

let lock_own = false;
if (fs.mkdir(SLOCK)) {
	lock_own = true;
}
else {
	// 已有实例在算：等 1 秒读它的结果，避免重叠执行
	let h = fs.popen('sleep 1');
	h.read('all');
	h.close();
	cached = rd(SCACHE);
	if (length(cached) > 0) {
		printf('%s', cached);
		exit(0);
	}
}

// ---------- 2) 系统信息 ----------
let hostname = trim(rd('/proc/sys/kernel/hostname'));

// 设备名：device-tree 里的 model 带结尾 NUL，先剔掉不可打印字符；缺失时退回 /tmp/sysinfo/model
let model = replace(rd('/proc/device-tree/model'), /[^ -~\n]/g, '');
model = trim(model);
if (model == '') model = trim(rd('/tmp/sysinfo/model'));
if (model == '') model = 'JDCloud RE-CS-02';

let up_i = uptime_f();
let la = fields(rd('/proc/loadavg'));
let load1 = (length(la) > 0) ? la[0] : '0';
let load2 = (length(la) > 1) ? la[1] : '0';
let load3 = (length(la) > 2) ? la[2] : '0';

let kernel = trim(rd('/proc/sys/kernel/osrelease'));

let firmware = '';
for (let line in split(rd('/etc/openwrt_release'), '\n')) {
	let m = match(line, /^DISTRIB_DESCRIPTION=(.*)$/);
	if (m) { firmware = replace(trim(m[1]), /"/g, ''); break; }
}
if (firmware == '') firmware = 'ImmortalWRT SNAPSHOT';
let aver = trim(rd('/usr/libexec/athena-version'));
if (aver != '') firmware = 'AthenaWrt v' + aver + ' · ' + firmware;

// ---------- 3) CPU 温度（所有 thermal zone 取最高） ----------
let temp = 0;
for (let f in fs.glob('/sys/class/thermal/thermal_zone*/temp')) {
	let t = to_int(rd(f), -1);
	if (t > temp) temp = t;
}
temp = int(temp / 1000);

// ---------- 4) 内存 ----------
let mem_total_kb = 0, mem_avail_kb = 0;
for (let line in split(rd('/proc/meminfo'), '\n')) {
	let m = match(line, /^(MemTotal|MemAvailable):\s*(\d+)/);
	if (!m) continue;
	if (m[1] == 'MemTotal') mem_total_kb = int(m[2]); else mem_avail_kb = int(m[2]);
}
let mem_total = int(mem_total_kb / 1024);
let mem_avail = int(mem_avail_kb / 1024);
let mem_used = mem_total - mem_avail;
let mem_pct = (mem_total > 0) ? int(mem_used * 100 / mem_total) : 0;

// ---------- 5) CPU 占用（/proc/stat 双采样，缓存跨进程） ----------
let ncpu = 0;
for (let line in split(rd('/proc/cpuinfo'), '\n')) {
	if (match(line, /^processor/)) ncpu++;
}
if (ncpu <= 0) ncpu = 4;

let cpu_idle = 0, cpu_total_ticks = 0;
for (let line in split(rd('/proc/stat'), '\n')) {
	let m = match(line, /^cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/);
	if (!m) continue;
	let u = int(m[1]), n = int(m[2]), s = int(m[3]), i = int(m[4]);
	let w = int(m[5]), q = int(m[6]), sq = int(m[7]);
	cpu_idle = i + w;
	cpu_total_ticks = u + n + s + i + w + q + sq;
	break;
}

let cpu_pct = 0;
let now_up = uptime_f();
let old = fields(rd(CPU_CACHE));
if (length(old) >= 2 && fs.stat(CPU_CACHE)) {
	let old_idle = to_int(old[0], 0);
	let old_total = to_int(old[1], 0);
	let old_up = to_int(old[2], 0);
	let old_pct = to_int(old[3], -1);
	let diff_t = cpu_total_ticks - old_total;
	let diff_i = cpu_idle - old_idle;
	let win = int(sprintf('%.0f', now_up - old_up));
	// 采样窗口必须 >=2s、tick 差 >=80：窗口过短时整数除法会把噪声放大成几十个百分点
	if (diff_t >= 80 && win >= 2) {
		cpu_pct = int((diff_t - diff_i) * 100 / diff_t);
	}
	else if (old_pct >= 0) {
		cpu_pct = old_pct;
	}
	if (cpu_pct > 100) cpu_pct = 100;
	if (cpu_pct < 0) cpu_pct = 0;
}
else {
	// 首次无缓存：用 loadavg 兜底（等价 awk 'printf "%.0f", l/n*100'）
	cpu_pct = int(sprintf('%.0f', (load1 + 0) / ncpu * 100));
	if (cpu_pct > 100) cpu_pct = 100;
}
fs.writefile(CPU_CACHE, cpu_idle + ' ' + cpu_total_ticks + ' ' + now_up + ' ' + cpu_pct);

// ---------- 6) uci 配置（一次性 show，替代十几次 uci get） ----------
function uci_show(pkg) {
	let map = {};
	let h = fs.popen('uci -q show ' + pkg + ' 2>/dev/null');
	let txt = h.read('all');
	h.close();
	for (let line in split(txt, '\n')) {
		// 键名里不会出现 '='，直接按第一个 '=' 切，避免字符类里写 \[ \] 被提前闭合
		let m = match(line, /^([^=]+)=(.*)$/);
		if (!m) continue;
		let k = m[1], v = m[2];
		if (match(v, /^'/)) {
			v = substr(v, 1, length(v) - 2);
			v = replace(v, /'\\''/g, "'");
		}
		map[k] = v;
	}
	return map;
}

let U_ATHENA = uci_show('athena');
let U_LED = uci_show('athena_led');
let U_NET = uci_show('network');

function ug(map, key, def) {
	let v = map[key];
	return (v == null) ? def : v;
}

let mode_x = ug(U_ATHENA, 'athena.system.mode', '');
if (mode_x == '') mode_x = 'router';

// ---------- 7) 实时网速 ----------
let net_if = ug(U_NET, 'network.wan.device', '');
if (mode_x == 'ap' || mode_x == 'bypass') net_if = 'br-lan';
if (net_if == '') net_if = 'wan';

function if_bytes(ifc) {
	let idx = 0;
	for (let line in split(rd('/proc/net/dev'), '\n')) {
		idx++;
		if (idx <= 2) continue;                       // 跳过两行表头
		// v1.2.57：字符类里不能写 \s（ucode 按字面字母 s 处理），否则 enp0s3 这类带 s 的网卡名匹配不到
		let m = match(line, /^[ \t]*([^ \t:]+):[ \t]*(.+)$/);
		if (!m) continue;
		if (m[1] != ifc) continue;
		let f = fields(m[2]);
		return { rx: to_int(f[0], 0), tx: to_int(f[8], 0) };
	}
	return null;
}

let ni = if_bytes(net_if);
let rx = ni ? ni.rx : 0;
let tx = ni ? ni.tx : 0;

// 单臂/拨号模式流量也可能记在 pppoe-wan（PPP 统计 > 二层承载），回退取较大值
if (fs.stat('/sys/class/net/pppoe-wan')) {
	let pi = if_bytes('pppoe-wan');
	if (pi) {
		if (pi.rx > rx) rx = pi.rx;
		if (pi.tx > tx) tx = pi.tx;
	}
}

let now_s = uptime_f();
let rx_rate = '0.0', tx_rate = '0.0';
if (fs.stat(NET_CACHE)) {
	let c = fields(rd(NET_CACHE));
	if (length(c) >= 3) {
		let o_s = to_int(c[0], 0), o_rx = to_int(c[1], 0), o_tx = to_int(c[2], 0);
		let dt = now_s - o_s;
		if (dt > 0) {
			rx_rate = sprintf('%.1f', (rx - o_rx) * 8 / 1000000 / dt);
			tx_rate = sprintf('%.1f', (tx - o_tx) * 8 / 1000000 / dt);
		}
	}
}
fs.writefile(NET_CACHE, now_s + ' ' + rx + ' ' + tx);
// 接口重置/重启/首次采样会出现负值
if (match(rx_rate, /^-/)) rx_rate = '0.0';
if (match(tx_rate, /^-/)) tx_rate = '0.0';

// ---------- 8) 无线（ubus 原始 JSON 透传，前端自己解析） ----------
let wireless = '{}';
let uh = fs.popen('ubus call network.wireless status 2>/dev/null');
let wtxt = uh.read('all');
uh.close();
wtxt = trim(wtxt);
if (wtxt != '') {
	try { json(wtxt); wireless = wtxt; } catch (e) { wireless = '{}'; }
}

// ---------- 9) 存储（块设备 + 挂载点） ----------
let mounts = [];
for (let line in split(rd('/proc/mounts'), '\n')) {
	let f = fields(line);
	if (length(f) < 3) continue;
	push(mounts, { dev: f[0], mp: f[1], fs: f[2] });
}

function mount_of(pname) {
	let dev = '/dev/' + pname;
	for (let m in mounts) if (m.dev == dev) return m;
	return null;
}

let storage = [];
for (let name in fs.lsdir('/sys/block')) {
	if (!match(name, /^(mmcblk|sd|nvme)/)) continue;
	let size_mb = int(to_int(rd('/sys/block/' + name + '/size'), 0) / 2048);
	if (size_mb <= 0) continue;
	// 分区优先（mmcblk0p1 / nvme0n1p1），再退整盘
	let parts = [], whole = [];
	for (let e in fs.lsdir('/sys/block/' + name)) {
		if (index(e, name) != 0) continue;
		if (index(e, name + 'p') == 0) push(parts, e); else push(whole, e);
	}
	parts = sort(parts);
	whole = sort(whole);
	let mp = '', mfs = '';
	for (let cand in parts) {
		let m = mount_of(cand);
		if (m) { mp = m.mp; mfs = m.fs; break; }
	}
	if (mp == '') {
		for (let cand in whole) {
			let m = mount_of(cand);
			if (m) { mp = m.mp; mfs = m.fs; break; }
		}
	}
	let used_mb = 0;
	if (mp != '') {
		let sv = fs.statvfs(mp);
		if (sv) {
			let used_bytes = sv.totalsize - sv.freesize;
			used_mb = int(used_bytes / 1048576);
		}
	}
	push(storage, { name: name, size_mb: size_mb, used_mb: used_mb, mount: mp, fs: mfs });
}

// ---------- 10) 端口速率（只报物理口） ----------
let ports = [];
for (let n in [ 'wan', 'lan1', 'lan2', 'lan3', 'lan4' ]) {
	let base = '/sys/class/net/' + n;
	if (!fs.stat(base)) continue;
	let speed = to_int(rd(base + '/speed'), 0);
	let state = trim(rd(base + '/operstate'));
	push(ports, { name: n, speed: speed, state: state });
}

// ---------- 11) 客户端清单 ----------
// 11.1 hostapd 关联表 → 无线在线 MAC + 频段
let band_map = {}, wifi_online = {};
for (let phy in fs.lsdir('/var/run/hostapd')) {
	let path = '/var/run/hostapd/' + phy;
	if (!fs.stat(path)) continue;
	let band = '';
	let h = fs.popen('iwinfo ' + phy + ' info 2>/dev/null');
	let info = h.read('all');
	h.close();
	let bm = match(info, /(2\.4[0-9]* GHz|5\.[0-9]* GHz)/);
	if (bm) band = bm[1];
	for (let line in split(rd(path), '\n')) {
		let mm = match(line, /^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}/);
		if (!mm) continue;
		let mac = lower_hex(mm[0]);
		band_map[mac] = band;
		wifi_online[mac] = true;
	}
}

// 11.2 ARP 表 → 活跃 MAC（排除全 0 与 incomplete）
function arp_list() {
	let out = [];
	let lines = split(rd('/proc/net/arp'), '\n');
	for (let i = 1; i < length(lines); i++) {
		let f = fields(lines[i]);
		if (length(f) < 4) continue;
		let ip = f[0], flags = f[2], mac = f[3];
		if (mac == '' || mac == '00:00:00:00:00:00') continue;
		if (flags == '0x0') continue;
		push(out, { ip: ip, mac: lower_hex(mac) });
	}
	return out;
}
let arp = arp_list();
let arp_online = {};
for (let a in arp) arp_online[a.mac] = true;

// 11.3 在线时长状态文件（tmpfs，重启清空）
let dev_old = {};
for (let line in split(rd(DEVSTATE), '\n')) {
	let f = fields(line);
	if (length(f) < 3) continue;
	dev_old[f[0]] = { first: to_int(f[1], 0), down: to_int(f[2], 0) };
}
let now_ts = now_epoch();
let dev_new = [];
function devstate(mac, on) {
	let prev = dev_old[mac];
	let first = prev ? prev.first : 0;
	let down = prev ? prev.down : 0;
	let upt = 0;
	if (on == 1) {
		if (first <= 0 || down > 0) first = now_ts;
		down = 0;
		upt = now_ts - first;
	}
	else {
		if (first > 0) down = now_ts;
		upt = 0;
	}
	push(dev_new, mac + ' ' + first + ' ' + down);
	return { upt: upt, down: down };
}

// 11.4 厂商 OUI（前缀匹配）
let OUI = [
	[ '3C:22:FB', 'Apple' ], [ '38:CA:DA', 'Apple' ], [ 'F0:18:98', 'Apple' ],
	[ '8C:85:90', 'Apple' ], [ 'A4:83:E7', 'Apple' ],
	[ 'C0:EE:FB', '小米' ], [ 'D0:57:7B', '小米' ], [ 'E4:5F:01', '小米' ],
	[ '70:B3:D5', '小米' ], [ 'AC:37:43', '小米' ], [ 'F0:1F:AF', '小米' ],
	[ '24:69:68', '华为' ], [ '68:3E:34', '华为' ], [ '28:6C:07', '华为' ],
	[ 'E0:19:1D', '华为' ], [ '84:2B:2B', '华为' ], [ 'A0:91:A2', '华为' ],
	[ '00:1A:2B', 'TP-Link' ], [ 'E4:F4:C6', 'TP-Link' ], [ 'C8:3A:35', 'TP-Link' ],
	[ '6C:70:9F', 'TP-Link' ], [ 'FC:D7:33', 'TP-Link' ], [ '7C:76:35', 'TP-Link' ],
	[ '14:DA:E9', '华硕' ], [ 'E8:48:B8', '华硕' ], [ 'DC:72:9B', '华硕' ], [ 'F0:2F:74', '华硕' ],
	[ '04:D9:F5', '三星' ], [ '48:4D:7E', '三星' ], [ 'A8:87:92', '三星' ],
	[ '64:09:80', '三星' ], [ 'C0:25:2F', '三星' ],
	[ '00:25:9C', '索尼' ], [ '04:CF:8C', '索尼' ], [ '54:48:E6', '索尼' ],
	[ 'B0:C5:54', '索尼' ], [ 'F8:FF:C2', '索尼' ]
];
function vendor_of(mac) {
	let u = upper_hex(mac);
	let pre = substr(u, 0, 8);
	for (let e in OUI) if (e[0] == pre) return e[1];
	return '未知设备';
}

// 11.5 DHCP 租约 → 主清单
let clients = [];
let seen = {};
let lease_txt = rd('/tmp/dhcp.leases');
for (let line in split(lease_txt, '\n')) {
	let f = fields(line);
	if (length(f) < 4) continue;                 // 剩余秒数 mac ip hostname clientid
	let mac = lower_hex(f[1]);
	let ip = f[2];
	let host = (f[3] == '*') ? '' : f[3];
	if (mac == '') continue;
	let online = wifi_online[mac] || arp_online[mac] ? true : false;
	let ds = devstate(mac, online ? 1 : 0);
	let band = band_map[mac];
	if (band == null || band == '') band = '有线';
	push(clients, {
		ip: ip, mac: mac, hostname: host, band: band, online: online,
		uptime_s: ds.upt, last_down: ds.down, vendor: vendor_of(mac)
	});
	seen[mac] = true;
}

// 11.6 补充：ARP 在线但不在租约里（静态 IP / 光猫回传口设备）
for (let a in arp) {
	if (seen[a.mac]) continue;
	let ds = devstate(a.mac, 1);
	push(clients, {
		ip: a.ip, mac: a.mac, hostname: '', band: '有线', online: true,
		uptime_s: ds.upt, last_down: ds.down, vendor: vendor_of(a.mac)
	});
	seen[a.mac] = true;
}

// 状态文件原子替换（空结果不覆盖，防止 dnsmasq/ARP 瞬时为空丢全部时长）
if (length(dev_new) > 0) {
	let body = join('\n', dev_new) + '\n';
	fs.writefile(DEVSTATE + '.new', body);
	fs.rename(DEVSTATE + '.new', DEVSTATE);
}

// ---------- 12) 点阵屏 / 模式 ----------
function led_bool(key, invert) {
	let v = ug(U_LED, 'athena_led.general.' + key, '');
	let on = (v == '1');
	if (invert) on = !on;
	return on;
}

let mt_enabled = (ug(U_LED, 'athena_led.general.enabled', '') == '1');
let mt_level = to_int(ug(U_LED, 'athena_led.general.light_level', ''), 0);
if (mt_level == 0) mt_level = 5;
let mt_night = (ug(U_LED, 'athena_led.general.night_light_enable', '') == '1');
let mt_profile = ug(U_LED, 'athena_led.general.profile_mode', '');
if (mt_profile == '') mt_profile = 'multi';
let mt_ns = ug(U_LED, 'athena_led.general.night_start', '');
if (mt_ns == '') mt_ns = '22:00';
let mt_ne = ug(U_LED, 'athena_led.general.night_end', '');
if (mt_ne == '') mt_ne = '07:00';
let mt_nl = to_int(ug(U_LED, 'athena_led.general.night_light_level', ''), 0);
if (mt_nl == 0) mt_nl = 1;
let mt_ck = !(ug(U_LED, 'athena_led.general.disable_led_clock', '') == '1');
let mt_md = !(ug(U_LED, 'athena_led.general.disable_led_medal', '') == '1');
let mt_up = !(ug(U_LED, 'athena_led.general.disable_led_up', '') == '1');
let mt_dn = !(ug(U_LED, 'athena_led.general.disable_led_down', '') == '1');

let mode = ug(U_ATHENA, 'athena.system.mode', '');
if (mode == '') mode = 'router';

// ---------- 13) WAN 配置回读 ----------
let wan_user = ug(U_NET, 'network.wan.username', '');
let wan_pwd = ug(U_NET, 'network.wan.password', '');
let wan_proto = '';
if (wan_user != '') {
	wan_proto = 'pppoe';
}
else {
	let np = ug(U_NET, 'network.wan.proto', '');
	if (np != '') {
		wan_proto = np;
	}
	else {
		wan_proto = ug(U_ATHENA, 'athena.single.wan_proto', '');
		if (wan_proto == '') wan_proto = 'pppoe';
	}
}

let wan_device = ug(U_NET, 'network.wan.device', '');
if (wan_device == '') wan_device = 'wan';

// WAN 设备与地址（v1.2.52 修正）
// 单臂 PPPoE 下 network.wan.device 往往指向并不存在的 "wan"，真实承载是 pppoe-wan；
// 真机实测：pppoe-wan 上的 27.10.61.56 就是公网出口地址（与 http://ip.3322.net 一致）。
// 这里只 fork 一次 `ip -4 addr show`，按 pppoe-* > 配置值 > wan* 的优先级取地址。
let wan_ip = '';
let wan_peer = '';
let wan_up = false;
let _has = {};
let _up = {};
let _cur = '';
let ih = fs.popen('ip -4 addr show 2>/dev/null');
let itxt = ih.read('all');
ih.close();
// 不用正则（ucode 正则对 [ \t] 与冒号类边界不稳），全部走 index/substr 的纯字符串判断。
for (let line in split(itxt, '\n')) {
	let c0 = substr(line, 0, 1);
	if (c0 != '' && index('0123456789', c0) >= 0 && index(line, ': ') >= 0 && index(line, '<') >= 0) {
		let rest = substr(line, index(line, ': ') + 2);
		let nm = (index(rest, ':') >= 0) ? substr(rest, 0, index(rest, ':')) : split(rest, ' ')[0];
		if (nm != '' && index(nm, ' ') < 0) {
			_cur = nm;
			_up[_cur] = (index(line, ',UP,') >= 0 || index(line, '<UP,') >= 0 || index(line, ',UP>') >= 0);
		}
		continue;
	}
	let p = index(line, 'inet ');
	if (p >= 0 && _cur != '') {
		// pppoe 行形如 "inet 27.10.61.56 peer 27.10.56.1/32"：先按 "/" 切掉掩码，再按空格取第一个 token
		let ip = split(split(substr(line, p + 5), '/')[0], ' ')[0];
		if (index(ip, '.') >= 0) _has[_cur] = ip;
		let pp = index(line, 'peer ');
		if (pp >= 0) {
			let pr = split(split(substr(line, pp + 5), '/')[0], ' ')[0];
			if (index(pr, '.') >= 0) wan_peer = pr;
		}
	}
}
let _pick = '';
for (let d in _has) { if (substr(d, 0, 6) == 'pppoe-') { _pick = d; break; } }
if (_pick == '' && _has[wan_device] != null) _pick = wan_device;
if (_pick == '') { for (let d in _has) { if (substr(d, 0, 3) == 'wan') { _pick = d; break; } } }
if (_pick != '') { wan_device = _pick; wan_ip = _has[_pick]; }
// 兜底：直接从内核路由表拿出口地址（223.5.5.5 走默认路由 → "dev pppoe-wan src 27.10.61.56"）
if (wan_ip == '') {
	let rh = fs.popen('ip route get 223.5.5.5 2>/dev/null');
	let rt = rh.read('all');
	rh.close();
	let dp = index(rt, ' dev ');
	let sp = index(rt, ' src ');
	if (dp >= 0) {
		let dv = split(substr(rt, dp + 5), ' ')[0];
		if (dv != '') { wan_device = dv; wan_up = true; }
	}
	if (sp >= 0) {
		let sv = split(substr(rt, sp + 5), '\n')[0];
		sv = split(sv, ' ')[0];
		if (index(sv, '.') >= 0) wan_ip = sv;
	}
}
wan_up = (_up[wan_device] == true) || wan_up;
let wan_vlan = ug(U_ATHENA, 'athena.single.wan_vlan', '');
if (wan_vlan == '') wan_vlan = '2044';

let ret_vlan = (U_ATHENA['athena.single.inner_vlan'] != null) ? U_ATHENA['athena.single.inner_vlan'] : '1';

let iptv_vlan = ug(U_ATHENA, 'athena.single.iptv_vlan', '');
if (iptv_vlan == '') {
	// 无字段但实际存在 IPTV：从 @device[N].ports 里的 'wan.X' 探测 VID
	for (let k in U_NET) {
		if (!match(k, /^network\.@device\[\d+\]\.ports$/)) continue;
		let m = match(U_NET[k], /lan4' 'wan\.(\d+)/);
		if (m) { iptv_vlan = m[1]; break; }
	}
}

let iptv_port = ug(U_ATHENA, 'athena.single.iptv_port', '');
if (iptv_port == '') iptv_port = 'lan4';

let wan_sip = ug(U_NET, 'network.wan.ipaddr', '');
let wan_smask = ug(U_NET, 'network.wan.netmask', '');
let wan_sgw = ug(U_NET, 'network.wan.gateway', '');
let wan_sdns = ug(U_NET, 'network.wan.dns', '');

// ---------- 14) 组装 JSON（字段名/顺序与 shell 版一致） ----------
let store_js = [];
for (let s in storage) {
	push(store_js, '{"name":"' + jstr(s.name) + '","size_mb":' + s.size_mb +
		',"used_mb":' + s.used_mb + ',"mount":"' + jstr(s.mount) + '","fs":"' + jstr(s.fs) + '"}');
}

let port_js = [];
for (let p in ports) {
	push(port_js, '{"name":"' + jstr(p.name) + '","speed":' + p.speed + ',"state":"' + jstr(p.state) + '"}');
}

let client_js = [];
for (let c in clients) {
	push(client_js, '{"ip":"' + jstr(c.ip) + '","mac":"' + jstr(c.mac) + '","hostname":"' + jstr(c.hostname) +
		'","band":"' + jstr(c.band) + '","online":' + (c.online ? 'true' : 'false') +
		',"uptime_s":' + c.uptime_s + ',"last_down":' + c.last_down + ',"vendor":"' + jstr(c.vendor) + '"}');
}

let out = '{"system":{"hostname":"' + jstr(hostname) + '"' +
	',"model":"' + jstr(model) + '"' +
	',"uptime":' + up_i +
	',"firmware":"' + jstr(firmware) + '"' +
	',"kernel":"' + jstr(kernel) + '"' +
	',"load":[' + load1 + ',' + load2 + ',' + load3 + ']}' +
	',"cpu":{"temp":' + temp + ',"total":' + cpu_pct + '}' +
	',"memory":{"total_mb":' + mem_total + ',"avail_mb":' + mem_avail + ',"used_mb":' + mem_used + ',"pct":' + mem_pct + '}' +
	',"network":{"rx_rate_mbps":' + rx_rate + ',"tx_rate_mbps":' + tx_rate + '}' +
	',"wireless":' + wireless +
	',"storage":[' + join(',', store_js) + ']' +
	',"ports":[' + join(',', port_js) + ']' +
	',"clients":[' + join(',', client_js) + ']' +
	',"matrix":{"enabled":' + (mt_enabled ? 'true' : 'false') +
	',"light_level":' + mt_level +
	',"night":' + (mt_night ? 'true' : 'false') +
	',"night_start":"' + jstr(mt_ns) + '"' +
	',"night_end":"' + jstr(mt_ne) + '"' +
	',"night_level":' + mt_nl +
	',"profile":"' + jstr(mt_profile) + '"' +
	',"clock":' + (mt_ck ? 'true' : 'false') +
	',"medal":' + (mt_md ? 'true' : 'false') +
	',"up":' + (mt_up ? 'true' : 'false') +
	',"down":' + (mt_dn ? 'true' : 'false') + '}' +
	',"mode":"' + jstr(mode) + '"' +
	',"wan":{"proto":"' + jstr(wan_proto) + '"' +
	',"username":"' + jstr(wan_user) + '"' +
	',"password":"' + jstr(wan_pwd) + '"' +
	',"device":"' + jstr(wan_device) + '"' +
	',"ip":"' + jstr(wan_ip) + '"' +
	',"peer":"' + jstr(wan_peer) + '"' +
	',"up":' + (wan_up ? 'true' : 'false') +
	',"wan_vlan":"' + jstr(wan_vlan) + '"' +
	',"ret_vlan":"' + jstr(ret_vlan) + '"' +
	',"iptv_vlan":"' + jstr(iptv_vlan) + '"' +
	',"iptv_port":"' + jstr(iptv_port) + '"' +
	',"static_ip":"' + jstr(wan_sip) + '"' +
	',"static_mask":"' + jstr(wan_smask) + '"' +
	',"static_gw":"' + jstr(wan_sgw) + '"' +
	',"static_dns":"' + jstr(wan_sdns) + '"' + '}}';

out = out + '\n';

fs.writefile(SCACHE + '.tmp', out);
fs.rename(SCACHE + '.tmp', SCACHE);
fs.writefile(SSTAMP, '' + up_i);

if (lock_own) fs.rmdir(SLOCK);

printf('%s', out);
