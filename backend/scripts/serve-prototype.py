"""Serve preserved prototype references; the former home URL opens the live home."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

prototype = Path(__file__).resolve().parents[2] / "prototype"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(prototype), **kwargs)

    def do_GET(self):
        requested = urlsplit(self.path)
        if requested.path in {"/", "/index.html"}:
            self.send_response(302)
            self.send_header(
                "Location",
                "http://localhost:8768/"
                + ("?" + requested.query if requested.query else ""),
            )
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        super().do_GET()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8767), Handler).serve_forever()
