const http = require('http');
const fs = require('fs');
const path = require('path');
const root = '/Users/niina/Documents/IA/proto';
try { process.chdir(root); } catch (e) {}
const types = { '.html':'text/html', '.svg':'image/svg+xml', '.png':'image/png', '.css':'text/css', '.js':'text/javascript' };
http.createServer((req, res) => {
  let u = req.url.split('?')[0];
  if (u === '/') u = '/index.html';
  const f = path.join(root, u);
  fs.readFile(f, (err, data) => {
    if (err) { res.statusCode = 404; res.end('not found'); return; }
    res.setHeader('Content-Type', types[path.extname(f)] || 'application/octet-stream');
    res.end(data);
  });
}).listen(4321, () => console.log('serving on 4321'));
