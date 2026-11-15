// Falla si un componente, isla, layout o página escribe a mano colores, tamaños o duraciones (aplicar-brief: todo sale de tokens.css).
// Permitido: 0 sin unidad y las consultas de medios en em con comentario al token (tokens.md: los punto-quiebre-* no entran en @media).
import { readdirSync, readFileSync } from 'node:fs';
import { join, extname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = fileURLToPath(new URL('..', import.meta.url));
const carpetas = ['src/componentes', 'src/islas', 'src/layouts', 'src/pages'];

const patrones = [
  [/#[0-9a-fA-F]{3,8}\b/, 'color hexadecimal'],
  [/\b(?:rgba?|hsla?|oklch|oklab)\(/, 'color funcional'],
  [/(?<![\w.#-])-?\d*\.?\d+(?:px|rem|em|ms|s|vw|vh|ch|pt)\b/, 'tamaño o duración literal'],
];

function* archivos(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const ruta = join(dir, e.name);
    if (e.isDirectory()) yield* archivos(ruta);
    else if (['.astro', '.css'].includes(extname(e.name))) yield ruta;
  }
}

// En .astro solo se revisan los bloques <style>; en .css, todo el archivo.
export function lineasDeEstilo(texto, esAstro) {
  if (!esAstro) return texto.split('\n').map((l, i) => [i + 1, l]);
  const lineas = texto.split('\n');
  let dentro = false;
  const salida = [];
  lineas.forEach((l, i) => {
    if (/<style\b/.test(l)) dentro = true;
    else if (/<\/style>/.test(l)) dentro = false;
    else if (dentro) salida.push([i + 1, l]);
  });
  return salida;
}

export function revisar(texto, esAstro) {
  const errores = [];
  for (const [n, linea] of lineasDeEstilo(texto, esAstro)) {
    if (/@media/.test(linea) && /punto-quiebre-/.test(linea)) continue;
    for (const [re, tipo] of patrones) {
      const m = re.exec(linea);
      if (m) errores.push(`línea ${n}: ${tipo} "${m[0]}"`);
    }
  }
  return errores;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  let total = 0;
  let revisados = 0;
  for (const carpeta of carpetas) {
    for (const ruta of archivos(join(raiz, carpeta))) {
      revisados++;
      const errores = revisar(readFileSync(ruta, 'utf8'), extname(ruta) === '.astro');
      for (const e of errores) console.error(`${relative(raiz, ruta)}: ${e}`);
      total += errores.length;
    }
  }
  if (total) process.exit(1);
  console.log(`sin literales visuales (${revisados} archivos revisados)`);
}
