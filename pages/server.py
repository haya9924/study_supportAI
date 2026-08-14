"""pages 配信 + /api のリバースプロキシ。

ブラウザは常に同一オリジン (:8700) へアクセスし、/api/* だけを
バックエンド (127.0.0.1:8000) へ中継する。CORS 不要で、
ホスト名やポートの到達性問題に依存しなくなる。
"""
from __future__ import annotations

import http.server
import socketserver
import urllib.error
import urllib.request
from functools import partial
from pathlib import Path

API = "http://127.0.0.1:8000"
PORT = 8700
ROOT = Path(__file__).resolve().parent

_FORWARD_HEADERS = (
    "Content-Type",
    "Accept",
    "Origin",
    "Access-Control-Request-Method",
    "Access-Control-Request-Headers",
)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else None
        url = API + self.path
        req = urllib.request.Request(url, data=body, method=self.command)
        for h in _FORWARD_HEADERS:
            if h in self.headers:
                req.add_header(h, self.headers[h])
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:  # noqa: BLE001
            msg = f'{{"detail": "proxy error: {exc}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return self._not_allowed()

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return self._not_allowed()

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return self._not_allowed()

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            return self._proxy()
        return super().do_OPTIONS()

    def _not_allowed(self):
        self.send_response(405)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    with ThreadingHTTPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"serving {ROOT} on :{PORT}, /api -> {API}")
        httpd.serve_forever()
