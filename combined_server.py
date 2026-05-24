"""
Combined server: serves static files on / (including index.html, game_script.json)
AND handles API endpoints (/command, /commands, /set_api_key, /status).
Runs on a single port so frontend fetch() works without CORS issues.
"""
import os, sys, json, http.server, socketserver, threading, mimetypes

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_PORT = 9001  # brain.py's API server

class CombinedHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CURRENT_DIR, **kwargs)
    
    def do_GET(self):
        # API proxy
        if self.path.startswith(('/commands', '/status')):
            import urllib.request
            try:
                resp = urllib.request.urlopen(f'http://127.0.0.1:{API_PORT}{self.path}', timeout=3)
                data = resp.read()
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception:
                self.send_response(502)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'backend not reachable'}).encode())
                return
        # Static files (including game_script.json)
        return super().do_GET()
    
    def do_POST(self):
        import urllib.request
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            req = urllib.request.Request(
                f'http://127.0.0.1:{API_PORT}{self.path}',
                data=body,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = resp.read()
            self.send_response(resp.status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.end_headers()
    
    def log_message(self, *args):
        pass

if __name__ == '__main__':
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = socketserver.ThreadingTCPServer(('0.0.0.0', PORT), CombinedHandler)
    print(f"🌐 Combined server running on http://0.0.0.0:{PORT}")
    print(f"   Static files from: {CURRENT_DIR}")
    print(f"   API proxied to: 127.0.0.1:{API_PORT}")
    server.serve_forever()
