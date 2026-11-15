// Sirve una carpeta estática (astro preview no admite dos instancias a la vez). Uso: node servidor-estatico.mjs <carpeta> <puerto>
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, extname, normalize } from 'node:path';

const [carpeta, puerto] = process.argv.slice(2);
const tipos = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.woff': 'font/woff', '.json': 'application/json' };

createServer(async (req, res) => {
  const ruta = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (ruta.includes('..')) return res.writeHead(400).end();
  for (const candidato of [ruta, join(ruta, 'index.html'), `${ruta}.html`]) {
    try {
      const cuerpo = await readFile(join(carpeta, candidato));
      res.writeHead(200, { 'Content-Type': tipos[extname(candidato)] ?? 'application/octet-stream' });
      return res.end(cuerpo);
    } catch {}
  }
  res.writeHead(404).end('No encontrado');
}).listen(Number(puerto), '127.0.0.1');
