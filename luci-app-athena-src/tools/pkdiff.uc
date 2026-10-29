// 比较两份软件包列表 JSON，按位置逐条对比并打印差异（最多 40 条）
import * as fs from 'fs';

function rd(p) {
	let s = fs.readfile(p);
	return (s == null) ? '' : s;
}

let A = json(rd('/tmp/pk_old.json'));
let B = json(rd('/tmp/pk_new.json'));
let a = (A && A.packages) ? A.packages : [];
let b = (B && B.packages) ? B.packages : [];

printf('old=%d new=%d\n', length(a), length(b));
let n = (length(a) < length(b)) ? length(a) : length(b);
let shown = 0;
for (let i = 0; i < n; i++) {
	let x = a[i], y = b[i];
	if (x.name == y.name && x.version == y.version) continue;
	printf('[%d] old=%s | %s    new=%s | %s\n', i, x.name, x.version, y.name, y.version);
	shown++;
	if (shown >= 40) { printf('... 还有更多\n'); exit; }
}
if (shown == 0) printf('前 %d 条完全一致\n', n);
if (length(a) > n) print('old 多出：', a[n], '\n');
if (length(b) > n) print('new 多出：', b[n], '\n');
