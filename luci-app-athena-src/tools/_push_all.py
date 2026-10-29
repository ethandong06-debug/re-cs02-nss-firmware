# -*- coding: utf-8 -*-
import os, json, base64, subprocess, urllib.request, urllib.error, ssl, time

ROOT = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt"
OWNER = "ethandong06-debug"
REPO = "re-cs02-nss-firmware"
PREFIX = "luci-app-athena-src"
BRANCH = "main"

# --- get token from git credential ---
out = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n",
                     capture_output=True, text=True).stdout
tok = None
for line in out.splitlines():
    if line.startswith("password="):
        tok = line[len("password="):]
        break
assert tok, "no token"

# --- curated file list ---
EXCLUDE_DIRS = ("output", "preview", ".workbuddy", "__pycache__", "_gomodcache",
                "_pkg54", "_shots", "node_modules", "_backup")
files = []
for dp, dn, fn in os.walk(ROOT):
    rel_dir = os.path.relpath(dp, ROOT)
    if any(x in rel_dir for x in EXCLUDE_DIRS):
        continue
    for f in fn:
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        sz = os.path.getsize(p)
        if sz > 2 * 1024 * 1024:
            continue
        if f.endswith((".pyc", ".bak", ".tmp", ".log", ".zip", ".tar.gz", ".bin", ".itb", ".img", ".png", ".jpg", ".mp4")):
            continue
        if "_dbg" in rel or "_shots" in rel or rel.endswith("_old.txt"):
            continue
        files.append(rel)
files.sort()
print(f"will push {len(files)} files")

# --- current ref ---
def api(method, path, body=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {tok}")
    req.add_header("User-Agent", "athena-backup")
    req.add_header("Accept", "application/vnd.github+json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, path, e.read()[:200])
        return None

ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
if not ref:
    print("no ref, exiting"); raise SystemExit(1)
base_sha = ref["object"]["sha"]
base = api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{base_sha}")
base_tree = base["tree"]["sha"]

# --- create blobs ---
blobs = []
for i, rel in enumerate(files):
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    with open(p, "rb") as f:
        content = f.read()
    b = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", {"content": base64.b64encode(content).decode(), "encoding": "base64"})
    if not b:
        print("blob fail", rel); continue
    blobs.append({"path": f"{PREFIX}/{rel}", "mode": "100644", "type": "blob", "sha": b["sha"]})
    if (i+1) % 10 == 0:
        print(f"  blobs {i+1}/{len(files)}")
    time.sleep(0.1)

print(f"created {len(blobs)} blobs, building tree")
tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", {"base_tree": base_tree, "tree": blobs})
if not tree:
    print("tree fail"); raise SystemExit(1)
commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits",
             {"message": "AthenaWrt v1.2.59 luci-app-athena 源码备份", "tree": tree["sha"], "parents": [base_sha]})
if not commit:
    print("commit fail"); raise SystemExit(1)
upd = api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": False})
print("DONE commit", commit["sha"][:8])
