import * as fs from 'fs';

let p = (length(ARGV) > 0) ? ARGV[0] : '/bin/ls';
let s = fs.readfile(p);
if (s == null) { printf('无法读取 %s\n', p); } else {
	printf('file=%s len=%d\n', p, length(s));
	let out = [];
	let n = length(s) < 64 ? length(s) : 64;
	for (let i = 0; i < n; i++)
		push(out, sprintf('%02x', ord(substr(s, i, 1))));
	printf('hex: %s\n', join(' ', out));
	let txt = [];
	for (let i = 0; i < n; i++) {
		let c = ord(substr(s, i, 1));
		push(txt, (c >= 32 && c < 127) ? chr(c) : '.');
	}
	printf('asc: %s\n', join('', txt));
}
