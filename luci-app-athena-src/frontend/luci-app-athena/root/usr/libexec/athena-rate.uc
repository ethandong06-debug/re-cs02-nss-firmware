#!/usr/bin/ucode
// AthenaWrt — 实时网速双口采样 v2（v1.2.59）
//
// v1.2.57：2 秒采样，单取 pppoe-wan。
// v1.2.59：Jason 要求「精准流量」。同一次采样里同时读 WAN 口（pppoe-wan/wan）
//   和 LAN 口（br-lan）的计数器，两组速率都输出并写日志：
//     - pppoe-wan.rx/tx = 互联网方向链路级计数（Ookla 对的是这个方向）
//     - br-lan.tx/rx    = PC 实际收到/发出（br-lan.tx 就是 Ookla 下行口径）
//   下次测速后把 /tmp/.athena-rate.log 拉出来，三个数同屏对比，哪个准就用哪个。
//
// 输出：{"ok":true,"if":"pppoe-wan","rx_mbps":1901.2,"tx_mbps":8.4,
//        "br_rx_mbps":1895.0,"br_tx_mbps":8.1,"dt_ms":2030}
// 日志：/tmp/.athena-rate.log，每行一条，限额 200 行
// 缓存：/tmp/.athena-rate = "cs ppp_rx ppp_tx br_rx br_tx if ppp_rr ppp_tr br_rr br_tr"

import * as fs from 'fs';

const CACHE = '/tmp/.athena-rate';
const LOG = '/tmp/.athena-rate.log';
const LOG_KEEP = 200;

function rd(p) { let s = fs.readfile(p); return (s == null) ? '' : s; }
function trim(s) {
	s = (s == null) ? '' : ('' + s);
	s = replace(s, /^[ \t\r\n]+/, '');
	s = replace(s, /[ \t\r\n]+$/, '');
	return s;
}
function fields(line) {
	line = trim(line);
	if (line == '') return [];
	return split(replace(line, /[ \t]+/g, ' '), ' ');
}

function uptime_cs() {
	let p = fields(rd('/proc/uptime'));
	if (length(p) == 0) return 0;
	let w = p[0], dot = index(w, '.');
	if (dot < 0) return int(w) * 100;
	let f = substr(w, dot + 1, 2);
	if (length(f) == 1) f = f + '0';
	else if (length(f) == 0) f = '00';
	return int(substr(w, 0, dot)) * 100 + int(f);
}

let DEV = {};
function load_dev() {
	let idx = 0;
	for (let line in split(rd('/proc/net/dev'), '\n')) {
		idx++;
		if (idx <= 2) continue;
		let m = match(line, /^[ \t]*([^ \t:]+):[ \t]*(.+)$/);
		if (!m) continue;
		let f = fields(m[2]);
		if (length(f) < 9) continue;
		DEV[m[1]] = { rx: +f[0], tx: +f[8] };
	}
}

function pick_ppp(cached) {
	if (cached != '' && DEV[cached]) return cached;
	for (let n in [ 'pppoe-wan', 'wan' ]) { if (DEV[n]) return n; }
	return '';
}

load_dev();
let now = uptime_cs();

let prev = fields(rd(CACHE));
let p_cs = 0, p_prx = 0, p_ptx = 0, p_brx = 0, p_btx = 0, p_if = '';
let p_prr = '0.0', p_ptr = '0.0', p_brr = '0.0', p_btr = '0.0';
if (length(prev) >= 9) {
	p_cs = int(prev[0]); p_prx = +prev[1]; p_ptx = +prev[2];
	p_brx = +prev[3]; p_btx = +prev[4]; p_if = prev[5];
	if (p_if == 'none') p_if = '';
	p_prr = prev[6]; p_ptr = prev[7]; p_brr = prev[8]; p_btr = prev[9];
}

let ppp = pick_ppp(p_if);
let br = DEV['br-lan'] ? 'br-lan' : '';
let C = (DEV[ppp] != null) ? DEV[ppp] : { rx: 0, tx: 0 };
let B = (DEV[br] != null) ? DEV[br] : { rx: 0, tx: 0 };

function log_line(s) {
	let old = split(rd(LOG), '\n');
	let kept = [];
	for (let i = length(old) - LOG_KEEP; i < length(old); i++) {
		if (i >= 0) push(kept, old[i]);
	}
	push(kept, s);
	fs.writefile(LOG, join('\n', kept) + '\n');
}

function flush_cache(rr, tr, brr, btr) {
	let tag = (ppp == '') ? 'none' : ppp;  // 空接口名会被 split 吃掉，用占位符
	fs.writefile(CACHE, now + ' ' + C.rx + ' ' + C.tx + ' ' + B.rx + ' ' + B.tx + ' ' + tag +
		' ' + rr + ' ' + tr + ' ' + brr + ' ' + btr);
}

// 首次 / 接口变化 / 任一计数器回退 → 只重置基准，报 0，不产生尖峰
if (p_cs == 0 || ppp != p_if || C.rx < p_prx || C.tx < p_ptx || B.rx < p_brx || B.tx < p_btx) {
	flush_cache('0.0', '0.0', '0.0', '0.0');
	log_line(sprintf('up=%d primed if=%s', now, ppp));
	printf('%s', '{"ok":true,"if":"' + ppp + '","rx_mbps":0,"tx_mbps":0,"br_rx_mbps":0,"br_tx_mbps":0,"dt_ms":0,"primed":true}\n');
	exit(0);
}

let dt_cs = now - p_cs;
if (dt_cs < 0) dt_cs = 0;
// <0.4s 的重复调用沿用上次数值（GWRT 也是 dt<0.5 跳过）
if (dt_cs < 40) {
	log_line(sprintf('up=%d dt=%d skip if=%s', now, dt_cs, ppp));
	printf('%s', '{"ok":true,"if":"' + ppp + '","rx_mbps":' + p_prr + ',"tx_mbps":' + p_ptr +
		',"br_rx_mbps":' + p_brr + ',"br_tx_mbps":' + p_btr + ',"dt_ms":' + (dt_cs * 10) + '}\n');
	exit(0);
}

let dt_s = dt_cs / 100;
let prr = sprintf('%.1f', (C.rx - p_prx) * 8 / 1000000 / dt_s);
let ptr = sprintf('%.1f', (C.tx - p_ptx) * 8 / 1000000 / dt_s);
let brr = sprintf('%.1f', (B.rx - p_brx) * 8 / 1000000 / dt_s);
let btr = sprintf('%.1f', (B.tx - p_btx) * 8 / 1000000 / dt_s);
if (match(prr, /^-/)) prr = '0.0';
if (match(ptr, /^-/)) ptr = '0.0';
if (match(brr, /^-/)) brr = '0.0';
if (match(btr, /^-/)) btr = '0.0';
// dt 抖动产生的 inf/nan 直接丢 0（真机实测 dt=97 时出现过 ppp_rx=inf）
if (index(prr, 'inf') >= 0 || index(prr, 'nan') >= 0) prr = '0.0';
if (index(ptr, 'inf') >= 0 || index(ptr, 'nan') >= 0) ptr = '0.0';
if (index(brr, 'inf') >= 0 || index(brr, 'nan') >= 0) brr = '0.0';
if (index(btr, 'inf') >= 0 || index(btr, 'nan') >= 0) btr = '0.0';

flush_cache(prr, ptr, brr, btr);
log_line(sprintf('up=%d dt=%d if=%s ppp_rx=%s ppp_tx=%s br_rx=%s br_tx=%s',
	now, dt_cs, ppp, prr, ptr, brr, btr));
printf('%s', '{"ok":true,"if":"' + ppp + '","rx_mbps":' + prr + ',"tx_mbps":' + ptr +
	',"br_rx_mbps":' + brr + ',"br_tx_mbps":' + btr + ',"dt_ms":' + (dt_cs * 10) + '}\n');
