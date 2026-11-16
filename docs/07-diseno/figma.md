---
id: diseno-figma
titulo: Figma — registro de origen de la extracción
estado: implementado
depende_de: [ADR-001]
---

# Figma — registro de origen

Figma es la **fuente de extracción única** del diseño ([ADR-001](../00-proyecto/decisiones/ADR-001-figma-fuente-extraccion.md)). Este archivo registra de dónde salió el brief; queda en `implementado` y congelado al terminar la extracción (fase 2). Después, el diseño se extiende desde el [brief](brief.md), no desde Figma.

## Archivo

| Campo | Valor |
|---|---|
| Nombre | `bugalu_studio_erp` |
| File key | `GxpFTDX6L0uFwg6xlulhXF` |
| Equipo requerido | «Integrador I» (plan Pro, asiento Full) |
| Volcado local de estructura | `.claude/cache/figma-metadata-2026-11-15.xml` (ignorado por git; tomado antes del reordenamiento de páginas) |

## Mapa de páginas (2026-11-15)

| Página | Contenido observado |
|---|---|
| `references` | Referencias visuales |
| `brief` | Guía de estilo brutalista (`bugalu-brutalist-design-guide`) y material de marca |
| `landing-page` | `bugalu-studio-landing` |
| `blueprint-funcional` | Blueprint funcional del portal |
| `login` | Acceso y registro, interno y de artista |
| `erp` | Portal del artista (escritorio y móvil: dashboard, proyecto, versión, revisión, historial, versión aprobada); flujo de contratación (servicio → brief → agenda de asesoría → cotización → revisión → proyecto activado); panel interno (dashboard operativo, clientes, tablero de proyectos, detalle interno, carga de WAV, publicar versión, centro de revisiones) |

Estado del archivo: hay unas 32 pantallas y no hay biblioteca de componentes (3 símbolos, casi todos del logo). Sí hay variables de color sueltas (`color/brand/primary`, `color/text/*`, `color/surface/default`, `color/border/default`, `color/background/canvas`, `color/navy-900`, `color/ink-950`, `color/mist-100`), ya traducidas a [tokens](tokens.md).

## Brecha detectada

Conciliación (fase 1, [spec 2026-11-15](../superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md)): el flujo de contratación diseñado (servicio → brief → agenda de asesoría → cotización → revisión → proyecto activado) es la **rama de asesoría** del flujo real y se conserva ([agendar-asesoria](../02-dominio/flujos/agendar-asesoria.md)).

No hay pantallas para estas partes, que se especifican desde el brief en la fase 7 (por RF, con `disenar-pantalla`):

| Pantalla faltante | Requerimiento |
|---|---|
| Franjas de sala, tramo y simulación de precio | [RF-02](../03-requerimientos/RF-02.md), [RF-03](../03-requerimientos/RF-03.md), [RF-04](../03-requerimientos/RF-04.md) |
| Publicación de franjas (Administrador) | [RF-03](../03-requerimientos/RF-03.md) |
| Reserva de ensayo | [RF-04](../03-requerimientos/RF-04.md) |
| Horarios del profesional (la modalidad sí está en `141:29060`) | [RF-15](../03-requerimientos/RF-15.md) |
| Registro de pago con captura y validación de pagos | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md) |
| Asignación de personal | [RF-07](../03-requerimientos/RF-07.md) |
| Reportes | [RF-14](../03-requerimientos/RF-14.md) |
| Perfil de usuario (solo hay acceso y registro) | [RF-01](../03-requerimientos/RF-01.md) |
| Estado de reserva y su historial; las notificaciones son correo | [RF-06](../03-requerimientos/RF-06.md) |
| Evaluación de satisfacción (la versión aprobada solo trae los pasos de cierre) | [RF-13](../03-requerimientos/RF-13.md) |

*Nota (2026-11-15, TAREA-RF01-3): RF-01 ya tiene spec de pantalla, sin abrir Figma (solo el volcado local de la página `login`): [acceso](pantallas/RF-01-acceso.md), [acceso interno](pantallas/RF-01-acceso-interno.md), [restablecer](pantallas/RF-01-restablecer.md), [perfil](pantallas/RF-01-perfil.md) y [solicitudes](pantallas/RF-01-solicitudes.md). Este registro sigue congelado.*

*Nota (2026-11-15, TAREA-RF03-1): las pantallas de sala ya tienen spec desde el brief, sin abrir Figma: [calendario](pantallas/RF-03-calendario.md), [reservar](pantallas/RF-04-reservar.md) (simulación incluida), [mis reservas](pantallas/RF-04-mis-reservas.md), [franjas](pantallas/RF-03-franjas.md) y [tarifas](pantallas/RF-02-tarifas.md). La reserva de ensayo es la misma pantalla con otro servicio.*

Brechas transversales (sin RF propio): estados vacío, carga y error; diálogo de confirmación; notificación emergente. Se cubren con el patrón [estados del sistema](patrones/estados-sistema.md) y la sección "Fuera del catálogo" del [catálogo](componentes/README.md).

## Extracción

Ejecutada por `disenador-ui` ([procedimiento](../04-agentes/disenador-ui.md#fase-2--extracción)). **Fecha de extracción: 2026-11-15.**

| Tarea | Llamadas al MCP de Figma | Qué se hizo |
|---|---|---|
| TAREA-201 | **0** (el MCP no se cargó) | Brief completo desde el volcado local `.claude/cache/figma-metadata-2026-11-15.xml`: estructura, medidas y nombres de capa (los textos de la guía y de la ficha de marca están en los nombres) |
| TAREA-201b | **12** de 20 | Verificación de los valores `inferido` y exportación del logotipo |
| **Total** | **12** | — |

`whoami` (2026-11-15): asiento **Full** en el plan **Pro** «Integrador I»; además, asiento View en un plan Starter. El servicio no informa el saldo de llamadas; el gasto quedó muy por debajo del límite Pro (~200/día).

Llamadas de TAREA-201b: `whoami`, `create_session`, `get_variable_defs` (`86:20`), `get_design_context` sobre `86:152` (componentes de la guía), `86:100` (tipografía), `161:700` (métricas), `161:727` (tarjeta de proyecto), `112:365` (campo de acceso) y `161:689` (encabezado de pantalla), y `download_assets` de `58:2`, `40:150` y `58:77`. Se consultaron nodos hijos en lugar de los marcos completos `161:609`, `141:28788`, `112:286` y `145:3617` que preveía el plan, para no traer pantallas enteras.

Resultado: [brief](brief.md), `fundamentos/` (con [assets del logotipo](fundamentos/logotipo.md#assets)), [tokens](tokens.md), [componentes](componentes/README.md), [patrones](patrones/README.md).

Nodos fuente principales: guía `86:20` (principios `86:55`, paleta `86:70`, tipografía `86:100`, componentes `86:152`, imagen `86:198`, efectos `88:57`); ficha de marca `35:29` y `14:2`; logos `58:2`, `40:150`, `58:77`; pantallas `161:689`, `161:700`, `161:727`, `112:365`.

### Verificación cerrada (TAREA-201b)

Ningún token queda `inferido`: cada uno tiene nodo de Figma o es `brief:` con su razón en [tokens](tokens.md). Correcciones principales:

1. Superficie de paneles: lienzo, no blanco (`color/surface/default`); el blanco queda para campos (`color-fondo-claro`, `112:365`).
2. Texto secundario: Figma usa `#5D5F89`; se mantiene `#4A4B7D` porque aquel falla sobre lavanda (3,95:1).
3. Sombra: una sola, 4 px en lavanda (`112:365`); botones, paneles y tarjetas sin sombra.
4. Botón secundario: relleno lienzo y texto navy (`86:168`), no navy.
5. Geist Mono, Unbounded 900 y radio 0 confirmados; texto mínimo de la guía 11 px (`86:164`), las pantallas usan 8 px y no se adopta.

Este archivo queda **congelado**: el diseño se extiende desde el [brief](brief.md), no desde Figma.

*Corrección de hecho (TAREA-203): la especificación de las pantallas faltantes es de la fase 7, no de la fase 2; el archivo sigue congelado.*
