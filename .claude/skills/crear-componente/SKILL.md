---
name: crear-componente
description: Úsala cuando dev-frontend deba implementar o modificar un componente estático `.astro` del catálogo de Bugalú (sin JavaScript) a partir de su ficha en docs/07-diseno/componentes/. Si el componente necesita interactividad, usa crear-isla.
---

# Crear un componente estático

Carga antes `aplicar-brief`. La ficha manda: el código implementa lo que dice, y si la ficha no lo dice, no se inventa.

**Ejemplo canónico:** [Boton.astro](../../../frontend/src/componentes/Boton.astro) (variantes, tamaños, estados, reenvío de atributos) y sus pruebas en [componentes.spec.js](../../../frontend/pruebas/componentes.spec.js).

## Pasos

0. **Lee el ejemplo canónico** (componente y su bloque de pruebas) antes de planificar.
1. **Lee la ficha** `docs/07-diseno/componentes/<componente>.md` entera: anatomía, variantes, estados propios, tokens, relaciones, accesibilidad y la sección Código (ruta y props). Lee también los [estados comunes](../../../docs/07-diseno/componentes/README.md#estados-comunes) y las [piezas internas](../../../docs/07-diseno/componentes/README.md) (`Icono`, `MensajeError`).
2. **Ambigüedad o hueco en la ficha:** aplica la lectura más conservadora, anótala en la ENTREGA y pide a `leader` que `disenador-ui` la cierre. No amplíes la ficha tú.
3. **Prueba primero** (Playwright en `frontend/pruebas/`): una aserción por estado y variante de la ficha, y siempre:
   - axe WCAG 2.2 AA sin violaciones en `/catalogo` a 1440 y 390;
   - cada estado seleccionado/actual/activo/error tiene **señal no cromática** (borde, icono o texto) **y** su atributo ARIA;
   - a 200 % de zoom y con letra raíz de 20 px nada se corta ni se solapa.
   Mírala fallar.
4. **Implementa** `frontend/src/componentes/<Nombre>.astro`:
   - props exactamente los de la ficha; lo que no es prop se reenvía al control nativo;
   - `<style>` del componente solo con `var(--token)` de rol (`color-texto-*`, `color-fondo-*`…), nunca `color-marca-*` ni valores literales;
   - HTML semántico; ARIA solo si el elemento nativo no basta.
5. **Añádelo a `/catalogo`**: es la ruta dinámica `src/pages/[catalogo].astro`, que solo se genera en desarrollo o con `PUBLIC_CATALOGO=1` (el build de pruebas, en `dist-pruebas/`). Añade una sección con título y todas sus variantes y estados.
6. **Verifica:** `npm run check` (tokens, literales y `astro check`), `npm run build` (sin `/catalogo`) y `npm run test:e2e`, que regenera las capturas en `frontend/pruebas/capturas/` (ignoradas por git).
7. **Estado en el catálogo:** columna Estado → `Implementado` en `docs/07-diseno/componentes/README.md`. El `estado` del frontmatter de la ficha no lo cambias tú: es de `disenador-ui`.
8. **Componente que agrupa otros** (p. ej. una fila de métricas) sin ficha propia: no lo crees; pide la ficha a `leader`.

## Errores que ya ocurrieron

| Error | Cómo evitarlo |
|---|---|
| Estado distinguido solo por un relleno lavanda (1,31:1) | Paso 3: señal no cromática + ARIA obligatorias |
| Token de marca en vez de rol (`--color-marca-navy`) | `comprobar-literales` lo rechaza; usa el rol |
| Etiqueta que se parte a 390 px | Respeta los límites de longitud de la ficha |
| Logo por debajo de `medida-logo-min` en móvil | Comprueba medidas mínimas de la ficha en 390 px |

Entrega con el [formato ENTREGA](../../../docs/05-protocolos/implementacion.md#formato-de-entrega) y la captura de cada estado.
