"""The local dev server: python3 tools/serve.py [port] (default 8765) from the project root.

Like `python3 -m http.server`, but (1) every response says `Cache-Control: no-store`, so a browser
never mixes a cached old file (the house shell, a level json) with new ones after a rebuild, and
(2) each file is read whole before it is sent, so a file iCloud has evicted (a "dataless"
placeholder that downloads on first read) isn't sent short."""
import http.server
import os
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def copyfile(self, source, outputfile):
        outputfile.write(source.read())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    http.server.ThreadingHTTPServer(("", port), Handler).serve_forever()
