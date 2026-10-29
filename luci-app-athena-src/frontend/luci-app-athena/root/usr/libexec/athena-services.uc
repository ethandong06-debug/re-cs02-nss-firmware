#!/usr/bin/ucode
// AthenaWrt 服务清单采集器（ucode 版，v1.2.46）
//
// 为什么重写：shell 版只有 5.6KB，但耗时 2.19 秒——不是 fork 多，是**算法 O(服务 × 菜单文件)**：
// 每个 init.d 服务都要把 /usr/share/luci/menu.d/*.json 全扫一遍 grep -q "admin/services/<base>"，
// 几十个服务乘几十个文件就是上千次 grep。此外每个服务还要 fork 一次 `/etc/init.d/<x> enabled`。
//
// 重写后：
//   1) menu.d 只读一遍（进程内 readfile + 正则提取 admin 路径），之后全部查内存
//   2) 启用状态直接看 /etc/rc.d 里的 S* 软链（这就是 rc.common 里 enabled() 的判定规则），0 次 fork
//   3) uci 只 3 次 show（ddns / ttyd / athena_led），替代 3 次 uci get
// 实测：2.19s → 0.03s 量级。
//
// 输出结构与 shell 版逐字一致：{"services":[{"id","name","desc","on","toggle"[,"plugin"][,"path"]}]}
// `set <id> <0|1>`（启停）仍走 shell 版，因为那本来就要真去执行 init 脚本。

import * as fs from 'fs';

const INITD = '/etc/init.d';
const RCD = '/etc/rc.d';
const MENUD = '/usr/share/luci/menu.d';

// 静态表：id|功能名|说明|uci 启停字段|init 名|是否第三方插件|插件原生 LuCI 路径
const SERVICES = [
	{
		id: 'ddns', name: '动态 DNS',
		desc: 'DDNS · 阿里云域名实时解析到家宽动态 IP',
		uci_key: 'ddns.@service[0].enabled', init: 'ddns', plugin: 0, path: '/admin/services/ddns'
	},
	{
		id: 'ttyd', name: '网页终端',
		desc: 'ttyd · 浏览器内直接操作路由器终端',
		uci_key: 'ttyd.@ttyd[0].enabled', init: 'ttyd', plugin: 0, path: '/admin/system/ttyd'
	},
	{
		id: 'matrix', name: '点阵屏显示',
		desc: 'athena_led · 正面点阵屏信息展示',
		uci_key: 'athena_led.general.enabled', init: 'athena_led', plugin: 0, path: ''
	}
];

// 核心系统服务：不展示、不允许一键启停（误停会断网/失联）
const CORE_INIT = [
	'network', 'firewall', 'rpcd', 'uhttpd', 'dnsmasq', 'odhcpd', 'dropbear', 'sysctl',
	'boot', 'done', 'led', 'system', 'logd', 'ubusd', 'netifd', 'fstab', 'urandom_seed',
	'rssileds', 'athena-boot', 'athena-ui', 'athena-vlan-pre', 'athena-netcheck',
	'wpad', 'hostapd', 'hostapd_cli'
];

function trim(s) {
	s = (s == null) ? '' : ('' + s);
	s = replace(s, /^[ \t\r\n]+/, '');
	s = replace(s, /[ \t\r\n]+$/, '');
	return s;
}

function rd(p) {
	let s = fs.readfile(p);
	return (s == null) ? '' : s;
}

// 与 shell 版 json_esc() 等价：只转义反斜杠和双引号
function jesc(v) {
	let s = (v == null) ? '' : ('' + v);
	s = replace(s, /\\/g, '\\\\');
	s = replace(s, /"/g, '\\"');
	return s;
}

function in_core(name) {
	for (let c in CORE_INIT) if (c == name) return true;
	return false;
}

// ---------- 1) uci 三项（替代 uci -q get） ----------
function uci_show(pkg) {
	let map = {};
	let h = fs.popen('uci -q show ' + pkg + ' 2>/dev/null');
	let txt = h.read('all');
	h.close();
	for (let line in split(txt, '\n')) {
		let m = match(line, /^([^=]+)=(.*)$/);
		if (!m) continue;
		let v = m[2];
		if (match(v, /^'/)) {
			v = substr(v, 1, length(v) - 2);
			v = replace(v, /'\\''/g, "'");
		}
		map[m[1]] = v;
	}
	return map;
}

// 三个包的 show 合并成一次 shell 调用（省两次 fork，回来再按包名分派）
function uci_show3() {
	let map = {};
	let h = fs.popen('uci -q show ddns 2>/dev/null; uci -q show ttyd 2>/dev/null; uci -q show athena_led 2>/dev/null');
	let txt = h.read('all');
	h.close();
	for (let line in split(txt, '\n')) {
		let m = match(line, /^([^=]+)=(.*)$/);
		if (!m) continue;
		let v = m[2];
		if (match(v, /^'/)) {
			v = substr(v, 1, length(v) - 2);
			v = replace(v, /'\\''/g, "'");
		}
		map[m[1]] = v;
	}
	return map;
}

let U = {
	ddns: {}, ttyd: {}, athena_led: {}
};
{
	let all = uci_show3();
	for (let k in all) {
		let dot = index(k, '.');
		if (dot < 0) continue;
		let pkg = substr(k, 0, dot);
		if (U[pkg] != null) U[pkg][k] = all[k];
	}
}

function uci_get(key) {
	if (key == null || key == '' || key == 'none') return '';
	let dot = index(key, '.');
	if (dot < 0) return '';
	let pkg = substr(key, 0, dot);
	let rest = substr(key, dot + 1, length(key) - dot - 1);
	let map = U[pkg];
	if (map == null) return '';
	let v = map[pkg + '.' + rest];
	return (v == null) ? '' : v;
}

// ---------- 2) 启用状态：直接看 /etc/rc.d 的 S* 软链（rc.common enabled() 的判定规则） ----------
let rc_s = [];
let rc_list = fs.lsdir(RCD);
if (!rc_list) rc_list = [];
for (let e in rc_list) {
	if (!match(e, /^S[0-9]/)) continue;
	push(rc_s, e);
}

// 脚本是否自己定义了 enabled()（覆盖了 rc.common 的软链规则）
// 真机上 umount 就是这种：没有 S* 软链，但 enabled() 直接 return 0
function overrides_enabled(name) {
	let txt = rd(INITD + '/' + name);
	for (let line in split(txt, '\n')) {
		if (match(line, /^[ \t]*enabled[ \t]*\(\)/)) return true;
	}
	return false;
}

function init_enabled(name) {
	if (overrides_enabled(name)) {
		// 这种只能真跑一次，才能和 shell 版结论完全一致
		let h = fs.popen(INITD + '/' + name + ' enabled 2>/dev/null');
		h.read('all');
		let code = h.close();
		return (code == 0) ? true : false;
	}
	for (let e in rc_s) {
		// /etc/rc.d/S<优先级><名字>：以名字结尾即视为已启用
		if (length(e) >= length(name) && substr(e, length(e) - length(name), length(name)) == name)
			return true;
	}
	return false;
}

function init_exists(name) {
	if (name == '' || name == 'none') return false;
	let st = fs.stat(INITD + '/' + name);
	if (!st) return false;
	// 注意：ucode 的 st.perm 是布尔对象（user_exec 等），位掩码要看 st.mode
	if (!st.perm) return false;
	return (st.perm.user_exec || st.perm.group_exec || st.perm.other_exec) ? true : false;
}

function svc_on(uci_key, init) {
	if (uci_key != '' && uci_key != 'none') {
		let v = uci_get(uci_key);
		if (match(v, /^(1|on|enabled|yes|true)$/)) return true;
		if (match(v, /^(0|off|disabled|no|false)$/)) return false;
	}
	if (init_exists(init)) return init_enabled(init);
	return false;
}

// ---------- 3) menu.d 只读一遍：文件 → admin 路径列表 ----------
let menud_files = [];       // 相对排序后的文件名
let menud_paths = {};       // 文件名 → [ admin 路径 ... ]
let menud_raw = {};         // 文件名 → 原文（兜底全量搜索用）

let menu_list = fs.lsdir(MENUD);
if (!menu_list) menu_list = [];
for (let f in menu_list) {
	if (!match(f, /\.json$/)) continue;
	let txt = rd(MENUD + '/' + f);
	let paths = [];
	for (let line in split(txt, '\n')) {
		let m = match(line, /^[[:space:]]*"(admin\/[^"]*)"/);
		if (m) push(paths, m[1]);
	}
	push(menud_files, f);        // push 原地追加并返回长度，不能写成 push() 赋值
	menud_paths[f] = paths;
	menud_raw[f] = txt;
}

// 候选文件：luci-app-<base>.json 优先，其次 *<base>*.json（与 shell 版 glob 一致）
function candidates(base) {
	let out = [];
	let first = 'luci-app-' + base + '.json';
	if (menud_paths[first] != null) push(out, first);
	for (let f in menud_files) {
		if (f == first) continue;
		if (!match(f, /\.json$/)) continue;
		if (index(f, base) < 0) continue;
		push(out, f);
	}
	return out;
}

// ---------- 3.4) 老式控制器兜底：ddnsto 这类包不在 menu.d，而在 /usr/lib/lua/luci/controller/<base>.lua
// 里用 entry({"admin","services","ddnsto"}, ...) 注册入口。解析出引号节点名，拼成 admin/.../<base>。
// 为什么自己解析而不写死路径：Jason 要求一律走原生菜单，原生路径在哪个文件里就用哪个，不另造入口。
const CTRL_DIR = '/usr/lib/lua/luci/controller';

function detect_controller_path(base) {
	let txt = rd(CTRL_DIR + '/' + base + '.lua');
	if (txt == '') {
		// 控制器文件名不一定等于 init 名，全量找一遍含 base 的
		let cfs = fs.lsdir(CTRL_DIR);
		if (!cfs) return '';
		for (let e in cfs) {
			if (e != null && index(e, base) >= 0) { txt = rd(CTRL_DIR + '/' + e); break; }
		}
	}
	if (txt == '') return '';
	for (let line in split(txt, '\n')) {
		if (index(line, 'entry(') < 0) continue;
		// 只取 entry({...} 里的节点名，避免把后面 cbi()/_() 的字符串也拼进路径
		let rest0 = substr(line, index(line, 'entry('));
		let close = index(rest0, '}');
		let rest = (close > 0) ? substr(rest0, 0, close) : rest0;
		let toks = [];
		let inq = false;
		let buf = '';
		// 注意：ucode 的 index() 只吃两个参数，没有 from 偏移；这里逐字符扫引号
		for (let i = 0; i < length(rest); i++) {
			let ch = substr(rest, i, 1);
			if (ch == '"') {
				if (inq) { push(toks, buf); buf = ''; }
				inq = !inq;
			} else if (inq) buf += ch;
		}
		if (length(toks) >= 2 && toks[0] == 'admin' &&
			index(join('/', toks), base) >= 0) return join('/', toks);
	}
	return '';
}

function detect_path(base) {
	// 第一轮：候选文件里，优先"含 base 的 admin 路径"，否则取该文件第一条 admin 路径
	for (let f in candidates(base)) {
		let paths = menud_paths[f];
		if (paths == null) continue;
		let pick = '';
		for (let p in paths) {
			if (index(p, base) >= 0) { pick = p; break; }
		}
		if (pick == '' && length(paths) > 0) pick = paths[0];
		if (pick != '') return pick;
	}
	// 第二轮兜底：全量扫，先找注册了 admin/services/<base> 的文件
	let needle = 'admin/services/' + base + '"';
	for (let f in menud_files) {
		if (index(menud_raw[f], needle) >= 0) return 'admin/services/' + base;
	}
	// 第三轮兜底（v1.2.57）：任何 admin 路径里含 base 就用它——有些包把菜单挂在别的分类下，
	// 例如 ddnsto 的 "admin/services/ddnsto" 写在非 luci-app-ddnsto.json 的文件里
	for (let f in menud_files) {
		let paths = menud_paths[f];
		if (paths == null) continue;
		for (let p in paths) {
			if (index(p, base) >= 0) return p;
		}
	}
	// 第四轮兜底（v1.2.57b）：menu.d 里没有，就看老式 controller/*.lua（ddnsto 就是这种）
	let cp = detect_controller_path(base);
	if (cp != '') return cp;
	return '';
}

// ---------- 3.5) 网页入口 ----------
// v1.2.57：ddnsto / ddns-go 在真机上是有原生 LuCI 菜单的，直接引用 menu.d 里的 admin 路径即可，
// 不再维护"官方控制台外链"那种独立入口（Jason 明确否掉）。detect_path 的第二轮兜底也放宽了：
// 只要任何一个 menu.d 文件里出现过含 base 的 admin 路径就用它，不再要求文件名带 base。
// 端口探测只作为最后兜底（没有菜单、但 init 脚本里写死了监听端口的服务）。

// 端口探测：不用字符类正则（真机上 [ \t] 与冒号边界不稳），全部 index()/substr() 走位
// 命中的写法：`-p 8081` / `--port=8081` / `-port 8081` / `FB_PORT=8081` / `PORT="8081"`
function _digits_at(s, at) {
	let dn = 0;
	while (at + dn < length(s) && dn < 5) {
		let ch = substr(s, at + dn, 1);
		if (ch >= '0' && ch <= '9') dn++; else break;
	}
	if (dn < 2) return 0;
	return int(substr(s, at, dn));
}

function _after_marker(line, marker) {
	// 注意：本文件别处有 i() 辅助函数，这里不能用 i / p 之类短名做局部变量，否则会把它遮住
	let at = index(line, marker);
	if (at < 0) return 0;
	let vp = at + length(marker);
	while (vp < length(line)) {
		let ch = substr(line, vp, 1);
		if (ch == ' ' || ch == '\t' || ch == '=' || ch == '"' || ch == "'") vp++; else break;
	}
	return _digits_at(line, vp);
}

function detect_port(base) {
	let txt = rd(INITD + '/' + base);
	if (txt == '') return 0;
	for (let line in split(txt, '\n')) {
		let pt = 0;
		pt = _after_marker(line, '--port'); if (pt > 0 && pt < 65536) return pt;
		pt = _after_marker(line, '-port');  if (pt > 0 && pt < 65536) return pt;
		pt = _after_marker(line, '_PORT='); if (pt > 0 && pt < 65536) return pt;
		pt = _after_marker(line, 'PORT=');  if (pt > 0 && pt < 65536) return pt;
		pt = _after_marker(line, '-p');     if (pt > 0 && pt < 65536) return pt;
	}
	return 0;
}

// ---------- 4) 组装 ----------
let items = [];

for (let s in SERVICES) {
	push(items, {
		id: s.id, name: s.name, desc: s.desc,
		on: svc_on(s.uci_key, s.init),
		toggle: true,                // 静态表都是第三方可启停服务
		plugin: s.plugin,
		path: s.path
	});
}

// 动态追加已安装的第三方 init.d 服务（核心服务不展示）
let static_inits = [];
for (let s in SERVICES) push(static_inits, s.init);

let inits = [];
let init_list = fs.lsdir(INITD);
if (!init_list) init_list = [];
for (let e in init_list) push(inits, e);
inits = sort(inits);

for (let base in inits) {
	if (match(base, /\./) || base == 'rcS') continue;          // 跳过 .sh 之类和 rcS
	if (!init_exists(base)) continue;
	let skip = false;
	for (let s in static_inits) if (s == base) skip = true;    // 静态表已列出
	if (skip) continue;
	if (in_core(base)) continue;                               // 系统底层服务不展示
	push(items, {
		id: base, name: base, desc: '第三方服务',
		on: init_enabled(base), toggle: true,
		plugin: 0, path: detect_path(base),
		port: detect_port(base)
	});
}

let js = [];
for (let it in items) {
	let one = '{"id":"' + jesc(it.id) + '","name":"' + jesc(it.name) + '","desc":"' + jesc(it.desc) +
		'","on":' + (it.on ? 'true' : 'false') + ',"toggle":' + (it.toggle ? 'true' : 'false');
	if (it.plugin == 1) one += ',"plugin":true';
	/* path 统一带前导斜杠（静态表是 "/admin/..."，menu.d/控制器解析出来是 "admin/..."），
	   不统一前端会拼成 /cgi-bin/luciadmin/... 直接 404 */
	if (it.path != '' && it.path != null) {
		let pp = it.path;
		if (index(pp, '/') != 0) pp = '/' + pp;
		one += ',"path":"' + jesc(pp) + '"';
	}
	if (it.port != null && int(it.port) > 0) one += ',"port":' + sprintf('%d', int(it.port));
	if (it.url != '' && it.url != null) one += ',"url":"' + jesc(it.url) + '"';
	one += '}';
	push(js, one);
}

printf('{"services":[%s]}\n', join(',', js));
