// Compara docs/07-diseno/tokens.md con src/estilos/tokens.css: falla si falta, sobra o difiere un token.
// Uso: node scripts/comprobar-tokens.mjs            (comprueba)
//      node scripts/comprobar-tokens.mjs --generar  (reescribe tokens.css desde tokens.md)
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const rutaMd = fileURLToPath(new URL('../../docs/07-diseno/tokens.md', import.meta.url));
const rutaCss = fileURLToPath(new URL('../src/estilos/tokens.css', import.meta.url));

export function leerTokensMd(texto) {
  const tokens = new Map();
  for (const linea of texto.split('\n')) {
    const celdas = linea.split('|').map((c) => c.trim());
    const nombre = /^`([a-z0-9-]+)`$/.exec(celdas[1] ?? '')?.[1];
    const valor = /^`(.+?)`/.exec(celdas[2] ?? '')?.[1];
    if (nombre && valor) tokens.set(nombre, valor);
  }
  // Un valor que es el nombre de otro token se escribe var(--token).
  for (const [nombre, valor] of tokens) {
    if (tokens.has(valor)) tokens.set(nombre, `var(--${valor})`);
  }
  return tokens;
}

export function leerTokensCss(texto) {
  const tokens = new Map();
  for (const m of texto.matchAll(/^\s*--([a-z0-9-]+):\s*(.+?);\s*$/gm)) tokens.set(m[1], m[2]);
  return tokens;
}

export function comparar(esperado, real) {
  const errores = [];
  for (const [n, v] of esperado) {
    if (!real.has(n)) errores.push(`falta --${n}`);
    else if (real.get(n) !== v) errores.push(`--${n}: tokens.md "${v}" != tokens.css "${real.get(n)}"`);
  }
  for (const n of real.keys()) if (!esperado.has(n)) errores.push(`sobra --${n} (no está en tokens.md)`);
  return errores;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const esperado = leerTokensMd(readFileSync(rutaMd, 'utf8'));
  if (process.argv.includes('--generar')) {
    const cuerpo = [...esperado].map(([n, v]) => `  --${n}: ${v};`).join('\n');
    writeFileSync(rutaCss, `/* Reflejo exacto de docs/07-diseno/tokens.md. Se verifica con scripts/comprobar-tokens.mjs. */\n:root {\n${cuerpo}\n}\n`);
  }
  const errores = comparar(esperado, leerTokensCss(readFileSync(rutaCss, 'utf8')));
  if (errores.length) {
    console.error(errores.join('\n'));
    process.exit(1);
  }
  console.log(`tokens.css coincide con tokens.md (${esperado.size} tokens)`);
}
