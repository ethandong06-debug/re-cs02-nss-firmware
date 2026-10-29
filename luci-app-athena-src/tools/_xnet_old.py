# -*- coding: utf-8 -*-
"""Try official proxy.golang.org for the old x/net pseudo version; if reachable, download .mod/.info/.zip."""
import urllib.request, os, sys

m = "golang.org/x/net"
v = "v0.0.0-20191105084925-a882066a44e0"
dst = r"C:\Users\Administrator\WorkBuddy\2026-10-22-23-23-11\athena-openwrt\tools\_gomodcache\cache\download\golang.org\x\net\@v"

sources = [
    ("proxy.golang.org", "https://proxy.golang.org/%s/@v/%s%s"),
    ("goproxy.io", "https://goproxy.io/%s/@v/%s%s"),
]
for name, tpl in sources:
    for ext in (".info", ".mod", ".zip"):
        url = tpl % (m, v, ext)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "go"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            print("%s %s -> %d bytes" % (name, ext, len(data)))
            with open(os.path.join(dst, v + ext), "wb") as f:
                f.write(data)
        except Exception as e:
            print("%s %s -> FAIL %s" % (name, ext, e))
