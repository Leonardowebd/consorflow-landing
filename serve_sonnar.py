import http.server, socketserver, os, posixpath, urllib.parse

ROOT = '/Users/niina/Documents/IA/proto/sonnar'

class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split('?', 1)[0].split('#', 1)[0]
        path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        parts = [p for p in path.split('/') if p and p not in ('.', '..')]
        full = ROOT
        for p in parts:
            full = os.path.join(full, p)
        if not parts or os.path.isdir(full):
            full = os.path.join(full, 'index.html')
        return full

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', 4386), Handler) as httpd:
    httpd.serve_forever()
