#!/usr/bin/ucode
// AthenaWrt 已安装软件清单采集器（ucode 版，v1.2.51）
//
// 数据源：/lib/apk/db/installed（323KB 纯文本，每条 C:/P:/V:/A:/S:/I:/T: 后跟空行）
// 为什么不用 apk：shell 版走 `apk list -I` 真机 1.41s，而页面只要「名字 + 版本」。
// 直读数据库后 0.16s、execve 1 次。
//
// 正确性收益：shell 版 split_pv 的正则 /-[0-9]/ 取最左匹配，会把
// ipq-wifi-jdcloud_re-cs-02、kmod-nls-iso8859-1、libiptext6-0、libnghttp2-14、libusb-1.0-0
// 这类包名从"第一个 -数字"处切开（名字和版本都错，install/remove 也会传错名）。
// 直读 P:/V: 没有这个问题。
//
// 输出结构与 shell 版一致：{"ok":true,"packages":[{"name","version","installed":true}]}
// 顺序按 "<name>|<version>" 字节序（与 shell 版 sort 等价），同名去重。
// 数据库不存在或解析为空时什么都不打印，由入口脚本回退 shell 版。
//
// 可安装列表（available）不在这里做：apk 3.0 的索引缓存是 ADBd 二进制格式
// （不是 gzip、不是 tar，/var/cache/apk/APKINDEX.*.tar.gz 只是历史命名），
// 解析它没有性价比，改由 shell 版"读缓存 + 后台预热"（见 athena-packages-legacy.sh）。

import * as fs from 'fs';

const DB = '/lib/apk/db/installed';

function rd(p) {
	let s = fs.readfile(p);
	return (s == null) ? '' : s;
}

function jesc(v) {
	let s = (v == null) ? '' : ('' + v);
	s = replace(s, /\\/g, '\\\\');
	s = replace(s, /"/g, '\\"');
	return s;
}

function parse_records(txt) {
	let rows = [], seen = {}, name = null, ver = '';

	for (let line in split(txt, '\n')) {
		if (length(line) < 2) continue;
		let tag = substr(line, 0, 2);
		if (tag == 'P:') {
			if (name != null && seen[name] == null) {
				seen[name] = 1;
				push(rows, name + '|' + ver);
			}
			name = substr(line, 2, length(line) - 2);
			ver = '';
		} else if (tag == 'V:' && name != null) {
			ver = substr(line, 2, length(line) - 2);
		}
	}
	if (name != null && seen[name] == null) push(rows, name + '|' + ver);

	return sort(rows);
}

function main() {
	let txt = rd(DB);
	if (length(txt) < 100) return;

	let rows = parse_records(txt);
	if (length(rows) == 0) return;

	let out = [], first = true;
	for (let r in rows) {
		let bar = index(r, '|');
		if (bar < 0) continue;
		let nm = substr(r, 0, bar);
		if (nm == '') continue;
		if (!first) push(out, ',');
		first = false;
		push(out, '{"name":"' + jesc(nm) + '","version":"' +
			jesc(substr(r, bar + 1, length(r) - bar - 1)) + '","installed":true}');
	}
	if (length(out) == 0) return;
	printf('{"ok":true,"packages":[%s]}', join('', out));
}

main();
