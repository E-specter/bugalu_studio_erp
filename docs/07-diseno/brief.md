---
id: diseno-brief
titulo: Brief técnico de diseño — índice
estado: borrador
depende_de: [ADR-001]
---

# Brief técnico de diseño

Fuente de verdad visual del proyecto. Se extrajo una vez de Figma ([origen](figma.md)) y desde entonces se **extiende de forma coherente** desde aquí. Las skills `aplicar-brief` y `disenar-pantalla` lo resumen y enlazan, nunca lo copian.

## Principios

- Ningún valor visual (color, tamaño, espaciado, radio, sombra) se escribe a mano en el código: todo sale de [tokens](tokens.md).
- Toda pantalla se compone con componentes del [catálogo](componentes/README.md); si falta uno, primero se agrega al catálogo.
- Cada pantalla tiene su spec en `pantallas/RF-xx-<pantalla>.md`, con el RF que cubre.
- Insumo de identidad: *Taller de marca Bugalú* (Alesin Branding Studio, 2026) y la guía brutalista del archivo de Figma.

## Decisiones artísticas

**Dirección visual: brutalismo técnico de estudio.** La guía (`bugalu-brutalist-design-guide`, "Manual de sistema v1.0") y la ficha de marca definen el estilo como *Photographic Brutalist Techno Digital FX*: la interfaz se lee como el panel de un rack analógico o una consola — estructura expuesta, bordes de alta definición, sombras planas, etiquetas técnicas — y la fotografía con tratamiento oscuro aporta la atmósfera. Lema: **"Converge y crea."**

| Principio (guía [01]) | Qué significa en la interfaz | Dónde se concreta |
|---|---|---|
| Brutalismo técnico | Estructura explícita: cada bloque tiene borde, título con código y regla. Sin ambigüedad visual | [forma y elevación](fundamentos/forma-elevacion.md), [panel](componentes/panel.md) |
| Rigor sonoro | Medición en lugar de ornamento: vúmetros, ondas, versiones numeradas, tiempos exactos | [barra de progreso](componentes/barra-progreso.md), [reproductor](componentes/reproductor.md), [tipografía técnica](fundamentos/tipografia.md) |
| Contraste puro | Lavanda + navy como tensión base; el naranja reactivo solo donde hay que actuar | [color](fundamentos/color.md) |

**Atributos de marca** (ficha `14:2` y pilares de la landing): *creativa, versátil, humana, profesional, sofisticada*. El sistema los traduce así:

- **Profesional y sofisticada** → precisión: retícula estricta, datos alineados, registro técnico (`[01]`, `PRY-014`, `V3_MASTER.wav`), nada decorativo en el panel interno.
- **Creativa y versátil** → la expresión vive en la landing, los accesos y las portadas: display Unbounded, fotografía tratada, marcas de registro, patrones.
- **Humana** → el lenguaje: mensajes que explican qué pasa y qué sigue, comentarios en primer plano, el artista ve su avance sin jerga interna.

**Por qué este reparto:** el ERP sirve a dos públicos. El artista compra una experiencia de estudio de alto nivel (la identidad debe sentirse); el personal opera todo el día (la identidad no debe estorbar). Por eso la intensidad de marca **baja** de la landing al portal y del portal al panel interno, pero la estructura (bordes, etiquetas, retícula) es la misma en las tres.

**Voz:** español, segunda persona ("tu proyecto"), frases cortas. Títulos y etiquetas en mayúsculas técnicas; contenido en minúsculas. Los anglicismos de Figma ("READY", "CREATORS WELCOME") se traducen; se conservan los términos de oficio del audio (WAV, máster, mezcla).

### Origen de cada decisión

Verificado en Figma el 2026-11-15 ([registro](figma.md#verificación-cerrada-tarea-201b)).

| Viene de Figma | Decidido en el brief (y por qué) |
|---|---|
| Paleta de cinco colores y sus variables (`86:70`, `86:20`) | Colores de estado: éxito verde, aviso ámbar, error naranja oscuro; Figma no los define (**usuario**, 2026-11-15) |
| Unbounded 900, Mona Sans, Geist y **Geist Mono** (`86:100`, `86:154`; Geist Mono confirmada por el **usuario**) | Texto mínimo 11 px: las pantallas `erp` usan 8 px, ilegible |
| Radio 0, borde 2 px navy, etiqueta con radio 4 px (`86:152`, `161:705`) | Texto secundario `#4A4B7D` y tinta sobre naranja: los valores de Figma no pasan AA |
| Superficie del color del lienzo, campos blancos, una sombra plana lavanda de 4 px (`161:705`, `112:365`) | Acción principal en lavanda (guía `86:161`); el naranja de las pantallas `erp` (`161:695`, 2,65:1 con texto lienzo) queda para el hover (**usuario**, 2026-11-15) |
| Botón secundario lienzo con texto navy (`86:168`); párrafos en tinta `#231F20` (`color/text/primary`) y títulos en navy (**usuario**, 2026-11-15) | Navy del logotipo: el SVG del texto trae `#23275C` y la marca `#262757`; pendiente del taller de marca, sin efecto en la interfaz porque los SVG usan `currentColor` (**usuario**, 2026-11-15) |
| Navegación táctil móvil arriba, bajo la cabecera (`169:5490`; conservada por el **usuario**) | Movimiento, foco y puntos de quiebre: Figma no los dibuja |
| Logotipo en tres variantes, exportado en SVG (`58:2`, `40:150`, `58:77`; **usuario**) | Solo iconos Lucide; ilustraciones de Streamline descartadas (**usuario**) |

Decisiones del **usuario** posteriores al cierre (2026-11-15):

- **Medidas relativas:** fuentes, espacios y medidas en `rem`, puntos de quiebre en `em`; solo bordes, sombra y efectos en px ([espaciado-reticula](fundamentos/espaciado-reticula.md#unidades)).
- **Logotipo:** un archivo por forma con el color por `currentColor`; navy sobre claros y lavanda (primario) sobre navy, mínimo 7:1 ([logotipo](fundamentos/logotipo.md#reglas)).

Decisiones `brief:` de la auditoría de cierre (TAREA-203):

- **Un foco naranja en reposo por pantalla:** el aviso Crítico. Los estados de alerta repetibles usan el naranja oscuro (`color-texto-alerta`, `color-fondo-peligro`); [color](fundamentos/color.md#reglas), regla 1.
- **Seleccionado, actual y activo** suman al lavanda un borde, un icono `check` o texto y su atributo ARIA ([color](fundamentos/color.md#reglas), regla 4).
- **Listado vacío:** la acción del vacío es la primaria y la fila de controles no se muestra ([estados del sistema](patrones/estados-sistema.md#vacío)).
- **Foco no tapado en móvil:** `scroll-padding-top` con `medida-zona-fija-movil` ([estructura de app](patrones/estructura-app.md#app)).

## Índice

| Tema | Archivo | Estado |
|---|---|---|
| Logotipo y variantes | [logotipo](fundamentos/logotipo.md) | Borrador (SVG exportados de Figma) |
| Color | [color](fundamentos/color.md) | Borrador |
| Tipografía | [tipografía](fundamentos/tipografia.md) | Borrador |
| Espaciado y retícula | [espaciado y retícula](fundamentos/espaciado-reticula.md) | Borrador |
| Forma y elevación | [forma y elevación](fundamentos/forma-elevacion.md) | Borrador |
| Movimiento | [movimiento](fundamentos/movimiento.md) | Borrador (decisión del brief) |
| Iconografía e imagen | [iconografía e imagen](fundamentos/iconografia-imagen.md) | Borrador |
| Tokens | [tokens](tokens.md) | Borrador |
| Componentes | [catálogo](componentes/README.md) (28 fichas) | Borrador |
| Patrones | [patrones](patrones/README.md) (6) | Borrador |
| Pantallas | `pantallas/`: RF-01 ([acceso](pantallas/RF-01-acceso.md), [acceso interno](pantallas/RF-01-acceso-interno.md), [restablecer](pantallas/RF-01-restablecer.md), [perfil](pantallas/RF-01-perfil.md), [solicitudes](pantallas/RF-01-solicitudes.md)); RF-02 ([tarifas](pantallas/RF-02-tarifas.md)); RF-03 ([calendario](pantallas/RF-03-calendario.md), [franjas](pantallas/RF-03-franjas.md)); RF-04 ([reservar](pantallas/RF-04-reservar.md), [mis reservas](pantallas/RF-04-mis-reservas.md)) | Borrador; el resto se especifica por RF desde el brief |

## Transversales

- **Audiencias:** Artista/Cliente (experiencia pública y portal, móvil y escritorio); personal interno y Administrador (panel operativo, escritorio).
- **Accesibilidad:** WCAG 2.2 AA: contraste verificado en [color](fundamentos/color.md#contraste-verificado), foco visible ([estados comunes](componentes/README.md#estados-comunes)), navegación por teclado, textos alternativos, objetivos ≥ 24 px.
- **Movimiento:** respeto de `prefers-reduced-motion` ([movimiento](fundamentos/movimiento.md)).

### Principios UX

1. **Jerarquía clara:** cada vista responde primero "dónde estoy" (ruta + título) y "qué hago aquí" (una acción principal, botón primario único).
2. **Densidad según el perfil:** el panel interno admite tablas compactas y más datos por pantalla; el portal muestra menos, con más aire y lenguaje del artista ([tablas y tableros](patrones/tablas-y-tableros.md#densidad)).
3. **Retroalimentación de estados:** todo lo que cambia (guardado, sincronización, validación de pago, nueva versión) tiene un estado visible en texto ([estados del sistema](patrones/estados-sistema.md)).
4. **Prevención de errores:** precio visible antes de comprometer, confirmación en acciones irreversibles, validación nativa primero ([formularios](patrones/formularios.md)).
5. **El estado vive en la URL:** filtros, pasos y vistas son enlaces; el sistema funciona sin JS salvo en las islas.

### Adaptabilidad

| Punto de quiebre | Ancho | Diseño |
|---|---|---|
| Móvil (base) | < `punto-quiebre-tableta` (lienzo móvil de Figma) | Una columna, cabecera móvil + navegación táctil, controles ≥ `medida-control-tactil` |
| Tableta | `punto-quiebre-tableta` hasta < `punto-quiebre-escritorio` | Navegación móvil, retícula de 2 columnas |
| Escritorio | ≥ `punto-quiebre-escritorio` | Navegación lateral, principal + lateral |
| Amplio | ≥ `punto-quiebre-amplio` (lienzo de Figma) | Contenido limitado a `medida-contenedor-max`, centrado |

Tokens `punto-quiebre-*` en [tokens](tokens.md#medidas-quiebres-y-forma); reglas en [espaciado y retícula](fundamentos/espaciado-reticula.md#adaptabilidad). La cabina y el Administrador trabajan en escritorio, pero el panel interno sigue siendo usable en tableta; el portal y el flujo son completos en móvil.
