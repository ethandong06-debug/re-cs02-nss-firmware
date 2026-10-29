"""修正验证：模拟真实 sed 流程 + 检查 glob 特殊字符"""
import json, re

BASE = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\frontend\luci-app-athena"
oaf = json.load(open(BASE + r"\root\usr\share\athena\oaf-app-map.json", encoding="utf-8"))

# ---- 模拟真实 sed 流程 ----
raw = open(BASE + r"\root\usr\share\athena\oaf-app-map.json", encoding="utf-8").read()
step1 = raw[1:-1]  # sed 's/^{//; s/}$//'
step2 = re.sub(r'\},', '}\n', step1)  # sed 's/},/}\n/g'
lines = [l for l in step2.splitlines() if l.strip()]

restored = {}
parse_fail = 0
for l in lines:
    m = re.match(r'^"(.*)":\{"id":"([^"]*)","name":"([^"]*)"\}$', l)
    if not m:
        parse_fail += 1
        if parse_fail <= 5:
            print("PARSE FAIL:", l[:90])
        continue
    restored[m.group(1)] = (m.group(2), m.group(3))

print("sed lines:", len(lines), "restored:", len(restored), "of", len(oaf), "parse_fail:", parse_fail)
miss = [k for k in oaf if k not in restored]
print("missing:", len(miss), miss[:5])
wrong = [k for k in oaf if k in restored and restored[k] != (oaf[k]["id"], oaf[k]["name"])]
print("wrong values:", len(wrong))

# ---- glob 特殊字符检查（case *"$key"* 模式匹配会出问题的字符）----
glob_chars = set('*?[]')
bad_glob = [k for k in oaf if any(c in k for c in glob_chars)]
print("keys with glob special chars:", bad_glob)

# ---- 模拟 case 匹配验证（python fnmatch 近似 glob）----
import fnmatch
def match_case(pattern, s):
    return fnmatch.fnmatchcase(s, pattern)
# case "$dom" in *"$key"*) → fnmatch(dom, "*"+key+"*")
tests = ["www.douyin.com", "a-b-dy-x.com", "youtube.com", "v10-dy.ixigua.com", "item.jd.com"]
for t in tests:
    hits = [k for k in oaf if match_case(t, "*" + k + "*")]
    longest = max(hits, key=len) if hits else None
    print(f"{t} -> glob hits={hits[:3]} longest={longest}")
