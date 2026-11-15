// Falla si un componente, isla, layout o página escribe a mano colores, tamaños o duraciones (aplicar-brief: todo sale de tokens.css).
// También prohíbe los tokens color-marca-* (solo se definen en tokens.css).
// Permitido: 0 (con o sin unidad) y las consultas de medios en em con comentario al token (tokens.md: los punto-quiebre-* no entran en @media).
import { readdirSync, readFileSync } from 'node:fs';
import { join, extname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = fileURLToPath(new URL('..', import.meta.url));
const carpetas = ['src/componentes', 'src/islas', 'src/layouts', 'src/pages'];
const sueltos = ['src/estilos/base.css']; // tokens.css queda fuera: es donde se definen los valores

// Colores CSS por nombre (transparent, currentColor e inherit se permiten); solo se buscan en el valor de una declaración.
const nombresDeColor = 'aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen'.split(' ');
const reColorNombrado = new RegExp(String.raw`^[^:]*(?:color|background|border|outline|fill|stroke|shadow)[^:]*:[^;]*\b(?:${nombresDeColor.join('|')})\b`, 'i');

const patrones = [
  [reColorNombrado, 'color por nombre'],
  [/#[0-9a-fA-F]{3,8}\b/, 'color hexadecimal'],
  [/\b(?:rgba?|hsla?|oklch|oklab)\(/, 'color funcional'],
  [/(?<![\w.#-])-?(?!0(?:px|rem|em|ms|s)\b)\d*\.?\d+(?:px|rem|em|ms|s|vw|vh|ch|pt)\b/, 'tamaño o duración literal'],
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
    if (/min-block-size:\s*100vh;\s*\/\*.*viewport/.test(linea)) continue; // el alto de la ventana no es un valor visual
    // Tokens de rol, nunca color-marca-* (aplicar-brief). Excepción: logotipo.md pide lavanda para el logo sobre navy; la línea lo declara con "logotipo".
    if (/--color-marca-/.test(linea) && !(/--color-marca-lavanda/.test(linea) && /logotipo/.test(linea))) errores.push(`línea ${n}: token de marca "${/--color-marca-\w+/.exec(linea)[0]}" (usa un token de rol)`);
    for (const [re, tipo] of patrones) {
      const m = re.exec(linea);
      if (m) errores.push(`línea ${n}: ${tipo} "${tipo === 'color por nombre' ? m[0].split(/[\s:,(]/).pop() : m[0]}"`);
    }
  }
  return errores;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  let total = 0;
  let revisados = 0;
  for (const carpeta of carpetas.concat(sueltos)) {
    for (const ruta of sueltos.includes(carpeta) ? [join(raiz, carpeta)] : archivos(join(raiz, carpeta))) {
      revisados++;
      const errores = revisar(readFileSync(ruta, 'utf8'), extname(ruta) === '.astro');
      for (const e of errores) console.error(`${relative(raiz, ruta)}: ${e}`);
      total += errores.length;
    }
  }
  if (total) process.exit(1);
  console.log(`sin literales visuales (${revisados} archivos revisados)`);
}
