"""Tiny static server rooted at the repo (viewer reads harness/world, harness/out and characters/)."""
import http.server, os, functools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def log_message(self, *a): pass
def make_server(port=8765):
    """Bind to `port`, or the next free port if it is taken."""
    for p in range(port, port + 20):
        try: return http.server.ThreadingHTTPServer(('127.0.0.1', p), functools.partial(H, directory=ROOT)), p
        except OSError: continue
    raise SystemExit(f'[harness] no free port in {port}..{port + 19}')
def serve(port=8765, live=False, block=True):
    httpd, port = make_server(port)
    url = f'http://127.0.0.1:{port}/harness/viewer/index.html' + ('?live=1' if live else '')
    print(f'[harness] viewer: {url}   (Ctrl+C to stop)', flush=True)
    if not block: return httpd, port
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
