"""Receives the WebGPU call records tracer.js POSTs and appends them to a JSONL file, one record per line.

    py -3 trace_server.py [port=8793] [out=trace.jsonl]

tracer.js posts text/plain bodies holding one or more newline-separated JSON records (no CORS preflight), and this server
answers every request with Access-Control-Allow-Origin: * so a page on any origin can post to it. Stop it with Ctrl+C.
"""
import http.server
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8793
OUT = sys.argv[2] if len(sys.argv) > 2 else 'trace.jsonl'


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(n).decode('utf-8')
        with open(OUT, 'a', encoding='utf-8') as f:
            for line in body.splitlines():
                if line.strip():
                    f.write(line.strip() + '\n')
        self.send_response(204)
        self._cors()
        self.end_headers()

    def log_message(self, *args):
        pass


print(f'trace server on http://127.0.0.1:{PORT}/trace -> {OUT}')
http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
