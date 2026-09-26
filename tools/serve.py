#!/usr/bin/env python3
"""Static file server for the Portrayal demo.

`python -m http.server` sends Last-Modified but no Cache-Control and no ETag.
With no explicit freshness, browsers fall back to a heuristic and will happily
reuse a stale copy without asking - which cost a full session chasing a 3D
rendering bug that a deploy had already fixed, because the demo iframe kept
loading the old 3d.html while a cache-busted URL loaded the new one.

This forces revalidation on every request. Content is still cached; the browser
just has to ask first, and SimpleHTTPRequestHandler answers If-Modified-Since
with a 304, so unchanged files still cost nothing to re-check.
"""
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9003
    root = sys.argv[2] if len(sys.argv) > 2 else "."
    # THIS MACHINE ONLY, by default: 0.0.0.0 put a directory listing of the
    # checkout on the local network. PORTRAYAL_SERVE_HOST=0.0.0.0 opts back in,
    # for looking at the explorer from another device.
    host = os.environ.get("PORTRAYAL_SERVE_HOST", "127.0.0.1")
    # threaded: the demo shell loads an iframe plus dist/ fetches concurrently,
    # and a single-threaded server serialises them behind one slow request
    with ThreadingHTTPServer((host, port),
                             partial(NoCacheHandler, directory=root)) as httpd:
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
