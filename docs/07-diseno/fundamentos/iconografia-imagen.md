---
id: fund-iconografia-imagen
titulo: Fundamento — Iconografía e imagen
estado: borrador
depende_de: [diseno-tokens, diseno-brief]
---

# Iconografía e imagen

Fuentes: guía brutalista secciones [05] "Tratamiento imagen" (`86:198`) y [06] "Catálogo de efectos" (`88:57`); iconos observados en `landing-page`, `login` y `erp`.

## Iconos

Figma usa dos sistemas: glifos de texto como marcadores en las pantallas del `erp` (capas "Icono") e iconos de trazo con nombres de Lucide en landing y accesos (`arrow-right`, `check-circle`, `eye`, `audio-waveform`). **Se unifica en Lucide** (decisión del usuario, 2026-11-15: los glifos son marcadores de posición y Lucide ya es el sistema nombrado).

1. Estilo: trazo, sin relleno, extremos rectos; grosor de trazo `borde-grosor-base`.
2. Tamaños: `medida-icono-sm` en línea con texto y dentro de campos; `medida-icono-md` en navegación. No hay otros tamaños.
3. Color: hereda `currentColor` del texto que acompaña.
4. Un icono siempre va con texto visible, salvo en botones de solo icono (reproducir, mostrar contraseña, navegación del mes), que llevan `aria-label`. El icono decorativo lleva `aria-hidden="true"`.
5. SVG en línea dentro del componente `.astro` (sin fuente de iconos ni dependencia en tiempo de ejecución).

| Concepto | Icono Lucide |
|---|---|
| Avanzar / continuar | `arrow-right` |
| Mes anterior / siguiente | `chevron-left` / `chevron-right` |
| Validado / incluido / marca de casilla | `check-circle` / `check` |
| Mostrar contraseña | `eye` / `eye-off` |
| Audio, versión | `audio-waveform` |
| Imagen (captura de pago), otro archivo | `image`, `file` |
| Reproducir / pausar | `play` / `pause` |
| Subir / descargar | `upload` / `download` |
| Comentario | `message-square` |
| Calendario, franja | `calendar` |
| Información / pendiente / error | `info` / `clock` / `alert-triangle` |
| Cerrar, quitar | `x` |
| Buscar | `search` |
| Ordenar columna | `arrow-up-down`, `arrow-up`, `arrow-down` |
| Tendencia | `arrow-up-right` / `arrow-down-right` |

Conceptos nuevos: se elige de Lucide y se agrega a esta tabla.

## Imagen fotográfica

| Correcto (`86:204`) | Incorrecto (`86:210`) |
|---|---|
| Fotografía propia del estudio, sesiones y artistas, con tratamiento de contraste oscuro | Fotografía de stock clara o genérica |
| Duotono lavanda + navy, grano, scanlines | Color natural saturado, filtros ajenos a la paleta |
| Recorte recto o fragmentado | Esquinas redondeadas, viñetas suaves |

Reglas:

1. La imagen es **atmósfera**, no información: siempre con `alt` descriptivo si aporta contenido o `alt=""` si es decorativa.
2. Texto sobre imagen solo con una superficie opaca debajo o un degradado de ocultación que garantice el contraste de [color](color.md#contraste-verificado).
3. En el panel interno no hay fotografía: solo datos. La imagen vive en la landing, los accesos y el portal del artista (portadas de proyecto).
4. Formatos: AVIF/WebP con respaldo, dimensiones explícitas para evitar saltos.

## Efectos

El catálogo de la guía (17 efectos, `88:157`–`88:489`) son **recetas de preparación de assets** en herramientas de edición. Su resultado se exporta como imagen; la interfaz solo reproduce en CSS los que tienen token:

| Efecto de la guía | En CSS | Token |
|---|---|---|
| 05 Degradado de ocultación · 12 Fondos con degradados | Sí | `efecto-degradado-suave` |
| 07 Rejilla, scanlines, puntos · 16 Rellenos con patrones | Sí (`repeating-linear-gradient`) | `efecto-patron-paso`, `efecto-opacidad-capa`, `color-borde-tecnico` |
| 11 Líneas técnicas y marcas de registro | Sí ([marco-registro](../componentes/marco-registro.md)) | `color-borde-tecnico`, `borde-grosor-grueso` |
| 13 Transparencias superpuestas | Sí | `efecto-opacidad-capa` |
| 15 Desenfoque de fondo | Sí (`backdrop-filter`) | `efecto-desenfoque-fondo` |
| 01–04, 06, 08, 09, 14, 17 | No: se aplican al asset exportado | — |

Los efectos refuerzan la estética **sin perder legibilidad** (`88:156`): nunca sobre texto de interfaz, tablas o formularios.

## Ilustración

El archivo de referencias incluye ilustraciones de *Streamline Bangalore* (`14:3`, `14:76`). **Descartadas** (decisión del usuario, 2026-11-15): no aparecen en ninguna pantalla y chocan con la dirección fotográfica. Solo iconos Lucide ([brief](../brief.md#decisiones-artísticas)).
