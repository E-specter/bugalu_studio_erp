---
name: disenar-pantalla
description: Procedimiento para especificar una pantalla nueva desde el brief de diseño (RF → recorrido y datos → composición con el catálogo → estados → copy → accesibilidad) y dejarla en docs/07-diseno/pantallas/RF-xx-<pantalla>.md. Úsala cuando disenador-ui deba especificar o ampliar la spec de una pantalla; no abre Figma.
---

# Diseñar una pantalla

Salida: `docs/07-diseno/pantallas/RF-xx-<pantalla>.md`, una spec por pantalla, compuesta **solo** con el [catálogo](../../../docs/07-diseno/componentes/README.md) y los [patrones](../../../docs/07-diseno/patrones/README.md). Carga antes `aplicar-brief`: sus reglas valen en todos los pasos. Figma no se abre; el diseño se extiende desde el [brief](../../../docs/07-diseno/brief.md). Enlaza a la ficha, al token o al patrón en vez de copiar sus valores.

## 1. RF

1. Lee el RF en `docs/03-requerimientos/RF-xx.md`: actores, flujo, reglas, isla y decisiones abiertas.
2. Lee su flujo en [flujos](../../../docs/02-dominio/flujos/), las reglas en [reglas de negocio](../../../docs/02-dominio/reglas-negocio.md), los estados en [estados de reserva](../../../docs/02-dominio/estados-reserva.md) y los roles en [actores](../../../docs/02-dominio/actores-roles.md).
3. Mira en la [brecha de Figma](../../../docs/07-diseno/figma.md#brecha-detectada) si la pantalla tenía diseño de origen.
4. Si el RF deja una decisión de negocio abierta que cambia la pantalla, no la inventes: anótala en "Pendientes" y avisa a `leader`.

## 2. Recorrido y datos

1. Escribe el recorrido en pasos numerados: quién llega, desde dónde, qué decide, adónde va al terminar.
2. Lista cada dato visible o editable con su origen (entidad o endpoint del módulo del RF) y su formato ([formato de datos](../../../docs/07-diseno/patrones/estructura-app.md#formato-de-datos)).
3. Decide qué estado vive en la URL (filtros, paso, vista) ([principios UX](../../../docs/07-diseno/brief.md#principios-ux)).

## 3. Composición

1. Elige una de las cuatro [estructuras](../../../docs/07-diseno/patrones/estructura-app.md); no se inventan estructuras.
2. Aplica los patrones que correspondan: [formularios](../../../docs/07-diseno/patrones/formularios.md), [tablas y tableros](../../../docs/07-diseno/patrones/tablas-y-tableros.md), [flujo por pasos](../../../docs/07-diseno/patrones/flujo-por-pasos.md), [audio y versiones](../../../docs/07-diseno/patrones/audio-y-versiones.md).
3. Compón por regiones (encabezado, principal, lateral, pie) con componentes del catálogo y su variante. Una sola acción principal.
4. ¿Falta un componente? Detente: escribe primero su ficha en `componentes/<nombre>.md` con la estructura de las existentes (anatomía, variantes, estados, tokens, relaciones, accesibilidad, código) y su fila en el catálogo. ¿Una composición nueva que se repetirá? Primero el patrón.
5. ¿Falta un token? Primero en [tokens](../../../docs/07-diseno/tokens.md).
6. HTML nativo antes que isla; si hace falta isla, debe estar en [frontend-islas](../../../docs/01-arquitectura/frontend-islas.md).

## 4. Estados

Para cada bloque con datos del servidor: vacío, carga, error y éxito según [estados del sistema](../../../docs/07-diseno/patrones/estados-sistema.md), más permisos (qué no ve cada rol, qué se muestra deshabilitado y con qué motivo). Distingue vacío de sin resultados.

## 5. Copy

Todo texto visible, en español y con la [voz](../../../docs/07-diseno/brief.md#decisiones-artísticas) del brief: título, descripción, etiquetas, botones (verbo + objeto), ayudas, mensajes de error (qué pasó y cómo corregir), vacíos y éxitos. Los textos legales o de precio salen del RF, no se redactan.

## 6. Accesibilidad

Puntos de referencia (`header`, `nav`, `main`), jerarquía de encabezados, orden de foco, qué se anuncia con `aria-live`, textos alternativos, teclado de cada isla y objetivos táctiles. Contraste solo con pares [verificados](../../../docs/07-diseno/fundamentos/color.md#contraste-verificado).

## 7. Salida y verificación

1. Escribe la spec con la plantilla de abajo (≤ 150 líneas; si no cabe, divide la pantalla).
2. `id` en minúsculas (`pantalla-rf-xx-<pantalla>`), nunca `RF-xx` a secas, y ninguna fila de tabla empieza por `| RF-xx |`: el validador lo tomaría como una segunda definición del RF.
3. Ejecuta `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md` hasta `docs OK`.
4. Actualiza la fila "Pantallas" del índice del brief si es la primera.

## Plantilla

```markdown
---
id: pantalla-rf-xx-<pantalla>
titulo: Pantalla — <nombre>
estado: borrador
depende_de: [RF-xx, diseno-brief, patron-<patron>, comp-<componente>]
---

# <Nombre de la pantalla>

| Campo | Valor |
|---|---|
| Requerimiento | [RF-xx](../../03-requerimientos/RF-xx.md) |
| Actores | <roles que la ven> |
| Estructura | <Landing · Acceso · Flujo · App> ([estructura de app](../patrones/estructura-app.md)) |
| Ruta | `/<ruta>` (estado en la URL: <parámetros>) |
| Isla | <ninguna · `<bugalu-x>`> |

## Recorrido

1. <Quién llega y desde dónde>
2. <Qué decide>
3. <Adónde va al terminar>

## Datos

| Dato | Origen | Formato |
|---|---|---|
| <dato> | <entidad o endpoint> | <formato de datos> |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) (App) | <ruta, índice, título, acción principal> |
| Principal | <componente> | <qué muestra> |
| Lateral | <componente> | <qué muestra> |

Patrones: <enlaces>. Adaptabilidad: <qué cambia en móvil y tableta>.

## Estados

| Bloque | Vacío | Carga | Error | Éxito |
|---|---|---|---|---|
| <bloque> | <mensaje y acción> | <forma> | <mensaje y salida> | <aviso o cambio> |

Permisos: <qué no ve cada rol; qué se muestra deshabilitado y por qué>.

## Copy

| Elemento | Texto |
|---|---|
| Título | <TÍTULO> |
| Acción principal | <Verbo + objeto> |

## Accesibilidad

- <Encabezados y puntos de referencia>
- <Orden de foco y teclado>
- <Anuncios `aria-live`>

## Pendientes

- <Decisión abierta y a quién corresponde, o "Ninguno">
```
