---
id: comp-calendario
titulo: Componente — Calendario (isla)
estado: borrador
depende_de: [diseno-tokens, comp-etiqueta-tecnica, comp-aviso, arq-frontend-islas, ADR-009]
---

# Calendario

Disponibilidad de la sala por **semana** (vista por defecto) o por **mes**, con la misma información en las dos ([ADR-009](../../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)). Origen: "Selector de agenda" de la agenda de asesoría (`141:29060`: navegación del mes, días de semana, cuadrícula, leyenda). La vista semanal y los tramos de 30 min son **decisión del brief** (TAREA-RF03-1): Figma no tiene pantallas de sala ([brecha](../figma.md#brecha-detectada)).

## Anatomía

1. Barra del periodo ([panel](panel.md) Base, ranura `acciones`): enlaces "Anterior" / "Siguiente" con aspecto de [etiqueta](etiqueta-tecnica.md) e icono `chevron-left` / `chevron-right` + texto visible, enlace "Hoy", y el conmutador de vista: [etiquetas](etiqueta-tecnica.md) Filtro "SEMANA" · "MES" (y "LISTA" en el modo Personal). Título del periodo como `<h2>`: "SEMANA DEL 16 AL 22 NOV 2026" / "NOVIEMBRE 2026". Bajo el título, "Horario de Lima".
2. **Semana:** `<table>` de 7 columnas (lunes a domingo). Cabecera de día: `fuente-familia-tecnica` `fuente-tamano-micro` ("MAR 18") y, debajo, sus horas libres en texto ("4 h libres"). Filas de 30 min con la hora en `<th scope="row">` (`fuente-familia-tecnica`), alto `medida-control-tactil`. Solo se pintan las filas entre la primera hora de franja y la última de la semana.
3. **Tramos seguidos del mismo estado** se leen como un bloque: sin divisor entre sus celdas y con la etiqueta de estado solo en la primera (las ocupadas, cerradas y propias se unen con `rowspan`).
4. **Mes:** `<table>` de 7 columnas y 6 semanas (42 días, el tope de la API). Cada día: número (`fuente-familia-tecnica`) y su resumen en texto ("4 h libres", "Sin horas libres", "Cerrado", "Sin horario"); en el modo Personal, además, "3 reservas". El día es un enlace que abre su semana (`?vista=semana&fecha=AAAA-MM-DD`).
5. Leyenda bajo la tabla: una [etiqueta](etiqueta-tecnica.md) por estado presente, con el mismo texto que en la celda.
6. Región `role="status"` oculta y estable para los anuncios.

Hueco entre celdas `espacio-1`; caja de celda `borde-grosor-fino`.

## Modos

| Modo (`modo`) | Quién | Qué muestra | Interacción |
|---|---|---|---|
| Reserva | Visitante y cliente ([RF-04](../../03-requerimientos/RF-04.md)) | Libre, ocupado sin datos, cerrado con motivo, no reservable; con sesión, **sus** reservas | Cada media hora libre es un botón que elige el inicio; la reserva propia, enlace a su detalle |
| Personal | Personal y Administrador ([RF-03](../../03-requerimientos/RF-03.md)) | Lo mismo y, en cada reserva, cliente, servicio y [etiqueta](etiqueta-tecnica.md) de estado | La reserva es un enlace a su detalle; vista Lista con la [tabla](tabla.md) |
| Asesoría | Visitante y cliente ([RF-15](../../03-requerimientos/RF-15.md)) | Bloques de horario del profesional: libre, ocupado sin datos, con sesión **sus** asesorías, pasado y no reservable; sin cierres ni margen entre asesorías | Etapa A: solo lectura, sin botones ([perfil público](../pantallas/RF-15-perfil-publico.md#disponibilidad-modo-asesoría)). Elegir el inicio entra con la etapa B |

## Estados de la media hora

Comunes: [catálogo](README.md#estados-comunes). Ningún estado se distingue solo por color: cada bloque lleva su texto y su nombre accesible ([color](../fundamentos/color.md#reglas), regla 4).

| Estado | Visual | Texto del bloque |
|---|---|---|
| Libre | `color-fondo-claro`, `borde-grosor-fino` `color-borde-fuerte` | LIBRE |
| Ocupado | Rayas (`efecto-patron-paso`, `color-borde-fuerte` a `efecto-opacidad-capa`); el texto va en una [etiqueta](etiqueta-tecnica.md) Neutra sobre `color-fondo-superficie` **opaco** (la etiqueta es transparente por defecto: el calendario le pone el fondo), nunca sobre las rayas. En el modo Personal, el enlace (cliente, servicio, etiqueta de estado) va en una caja `color-fondo-superficie` con relleno `espacio-1` | OCUPADO (Personal: cliente, servicio y etiqueta de estado de la reserva) |
| Propio (cliente) | `color-fondo-destacado` + `borde-grosor-base` `color-borde-fuerte` | TU RESERVA + folio |
| Cerrado | `color-fondo-superficie`, sin caja, icono `lock` | CERRADO + motivo ("Feriado") |
| Pasado | `color-texto-secundario`, sin caja | PASADO (media hora que ya empezó; decisión TAREA-RF04-6: se distingue de NO RESERVABLE porque el motivo es otro) |
| No reservable | `color-texto-secundario`, sin caja | NO RESERVABLE (fuera de la anticipación o margen de preparación) |
| Sin franja | Celda vacía, sin caja | — |
| Inicio elegido | `color-fondo-invertido`, texto `color-texto-invertido`, icono `check` | INICIO |
| En el tramo | `color-fondo-destacado` + `borde-grosor-grueso` `color-borde-fuerte` | TU SELECCIÓN (en la primera celda) |
| Hoy | Cabecera del día subrayada `borde-grosor-base`, `aria-current="date"` | — |

**Qué es libre:** una media hora es libre si una reserva de 30 min puede **empezar** ahí: la media hora y los 30 min de buffer que la siguen caben en la franja y no tocan una ocupada ni un cierre ([RN-12](../../02-dominio/reglas-negocio.md)). El último buffer de cada hueco es "No reservable (margen de preparación)". Las horas libres del día salen de `dias[].minutos_libres`, nunca se cuentan en el navegador.

Bloque: carga con `aria-busy="true"` y "Cargando semana…" / "Cargando mes…" en `fuente-familia-tecnica`, mismo tamaño; error con [aviso](aviso.md) Error y "Reintentar"; periodo sin franjas según la spec de la pantalla.

## Adaptabilidad

- ≥ `punto-quiebre-tableta`: la tabla semanal completa.
- < `punto-quiebre-tableta`: la semana pasa a una lista de 7 días; cada día con horas libres es un `<details>` cuyo `<summary>` dice "MAR 18 NOV · 4 h libres" y, abierto, muestra sus bloques en texto ("10:00–14:00 · LIBRE") y, en el modo Reserva, los inicios libres como botones en fila que se ajusta (alto `medida-control-tactil`). Los días sin horas libres son texto, no `<details>`. El mes conserva la tabla con el resumen abreviado ("4 h").

## Tokens

`color-fondo-claro`, `color-fondo-superficie`, `color-fondo-invertido`, `color-fondo-destacado`, `color-borde-fuerte`, `color-texto-invertido`, `color-texto-secundario`, `borde-grosor-fino`, `borde-grosor-base`, `borde-grosor-grueso`, `espacio-1`, `medida-control-tactil`, `medida-icono-sm`, `efecto-patron-paso`, `efecto-opacidad-capa`, `fuente-familia-tecnica`, `fuente-tamano-micro`, `punto-quiebre-tableta`.

## Relaciones

Paso 01 del [flujo por pasos](../patrones/flujo-por-pasos.md) de la reserva ([reservar](../pantallas/RF-04-reservar.md)); agenda del personal ([calendario](../pantallas/RF-03-calendario.md)). Alimenta al [resumen persistente](resumen-persistente.md).

## Accesibilidad

- **Sin JS:** la salida es estática y los datos llegan en el navegador, así que no hay calendario. Un `<noscript>` muestra un [aviso](aviso.md) Información (texto en la spec de la pantalla).
- **Semana, modo Reserva:** `role="grid"` con foco itinerante (un solo `tabindex="0"`: el inicio elegido o la primera media hora libre). Flechas arriba y abajo: media hora anterior o siguiente con botón o enlace en el día; izquierda y derecha: la misma hora (o la más cercana) del día vecino; Inicio y Fin: primera y última del día; RePág y AvPág: semana anterior o siguiente. Intro o Espacio elige el inicio.
- **Mes:** `role="grid"` con el mismo foco itinerante sobre los enlaces de día (flechas día a día, Inicio y Fin la semana, RePág y AvPág el mes).
- **Modo Personal (semana):** tabla normal; los enlaces de reserva siguen el orden del Tab, sin foco itinerante.
- Nombre accesible completo en cada celda interactiva: "martes 18 de noviembre, 10:00, libre"; "…, 10:30, en tu selección"; "…, tu reserva RSV-0012, 10:00 a 12:00"; día del mes: "martes 18 de noviembre, 4 horas libres, abrir semana". La inicial elegida con `aria-pressed="true"`.
- Anuncios en la región `role="status"`, una vez: el periodo al cambiarlo ("Semana del 16 al 22 nov 2026: 32 horas libres") y la elección ("Inicio: martes 18 nov, 10:00. Hasta 4 h disponibles").
- Los enlaces del periodo y de la vista son `<a href>` que la isla intercepta: `history.pushState`, carga de datos y anuncio; el foco se queda en el enlace pulsado. Con la URL copiada se abre el mismo periodo.

## Código

Isla `frontend/src/islas/Calendario.astro` que registra `<bugalu-calendario>`. Atributos: `modo` (`reserva|personal|asesoria`), `profesional` (id; solo en `asesoria`, que llama a `obtenerDisponibilidadProfesional({ profesional, desde, hasta })` en lugar de la de sala), `vista` (`semana|mes|lista`; la página lo toma de `?vista=`), `fecha` (`AAAA-MM-DD`, ancla del periodo; `?fecha=`), `sala` (id; si falta, la primera de `listarSalas()`), `inicio` y `duracion` (minutos; restauran la selección al volver al paso). **Datos:** sin atributo de URL; la isla llama a `obtenerDisponibilidad({ sala, desde, hasta })` y `listarSalas()` de `servicios/reservas.js` (con el token si hay sesión); con sesión de cliente, también `listarMisReservas()` para poner folio y enlace a sus bloques (`ocupados` solo trae `propia`, se casan por `inicio`); en Lista, `listarReservas({ desde, hasta })`. **Evento:** en el modo Reserva emite `calendario-inicio` con `detail: { inicio, minutosMaximos }` (minutos que caben desde ese inicio, tope 480) para la isla del paso.
