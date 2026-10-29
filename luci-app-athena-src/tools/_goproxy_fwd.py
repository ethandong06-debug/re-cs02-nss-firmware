# -*- coding: utf-8 -*-
"""Minimal GOPROXY forwarder: VM -> host(localhost:8899) -> goproxy.cn"""
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sys

UPSTREAM = "https://goproxy.cn"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = UPSTREAM + self.path
        req = urllib.request.Request(url, headers={"User-Agent": "go/1.21"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
                self.send_response(r.status)
                self.send_header("Content-Type", r.headers.get("Content-Type", "application/octet-stream"))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            msg = ("proxy error: %s" % e).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    port = 8899
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    sys.stderr.write("goproxy forwarder listening on :%d -> %s\n" % (port, UPSTREAM))
    sys.stderr.flush()
    srv.serve_forever()
