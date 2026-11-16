---
id: pantalla-rf-04-mis-reservas
titulo: Pantalla — Mis reservas (lista, detalle y cancelar)
estado: borrador
depende_de: [RF-04, ADR-009, estados-reserva, diseno-brief, patron-estructura-app, patron-tablas-y-tableros, patron-formularios, patron-estados-sistema, comp-tabla, comp-panel, comp-etiqueta-tecnica, comp-indicador-estado, comp-aviso, comp-boton, comp-barra-acciones]
---

# Mis reservas

| Campo | Valor |
|---|---|
| Requerimiento | [RF-04](../../03-requerimientos/RF-04.md): CA-05, CA-07, CA-08 (detalle), CA-10 |
| Actores | Artista/Cliente (las suyas); Personal y Administrador abren el detalle desde la [agenda](RF-03-calendario.md) |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/reservas?ver=proximas\|historial`, `/app/reservas/detalle?id=`, `/app/reservas/cancelar?id=`. URL: `ver`, `id`, `aviso` |
| Isla | `<bugalu-reservas vista="lista\|detalle\|cancelar">` (nueva) |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)) |

## Recorrido

1. El cliente entra por "RESERVAS" (`calendar-check`) o desde "Ver mi reserva" del [paso Listo](RF-04-reservar.md). Ve sus próximas reservas; HISTORIAL muestra las finalizadas y canceladas.
2. Abre una con "Ver reserva {folio}": estado, horario, precio, cuotas y, si está `Pre-reservada`, la fecha límite de pago con lo que falta.
3. Si no pagó nada, "Cancelar reserva" lleva a la confirmación; al confirmar vuelve al detalle con `?aviso=reserva-cancelada`.
4. "Reservar sala" abre el [flujo](RF-04-reservar.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Reservas | `GET /reservas/mias` → `[Reserva]` | PRÓXIMAS: `Pre-reservada`, `Confirmada`, `En curso`, por `inicio` ascendente. HISTORIAL: `Finalizada`, `Cancelada`, descendente. Total "3 reservas" |
| Reserva | `GET /reservas/{id}` | — |
| Folio, servicio, sala | `folio`, `servicio`, `sala` | Folio en `fuente-familia-tecnica`; el resto tal cual |
| Horario | `inicio`, `fin` | `D MMM AAAA` + `HH:mm–HH:mm` y [duración](../patrones/estructura-app.md#formato-de-datos) |
| Estado | `estado`, `motivo_cancelacion` | [Etiqueta](../componentes/etiqueta-tecnica.md) según [estados de reserva](../../02-dominio/estados-reserva.md): PRE-RESERVADA (Aviso), CONFIRMADA y FINALIZADA (Éxito), EN CURSO (Activa), CANCELADA (Alerta) + motivo en texto |
| Fecha límite | `vence_pago` | [Plazo restante](../patrones/estructura-app.md#formato-de-datos) |
| Precio | `precio` (`Simulacion`) | [Tabla](../componentes/tabla.md) Partidas, igual que en [reservar](RF-04-reservar.md#datos) |
| Cuotas | `cuotas[].{hito, monto, estado}` | Tabla Partidas: CUOTA ("Al reservar · 50 %", "Al terminar la sesión · 50 %") · IMPORTE · ESTADO (etiqueta) |
| Especialistas | `especialistas[].nombre` | Lista separada por comas |
| Cliente | `cliente` (solo personal y Administrador) | Tal cual |
| Cancelar | `POST /reservas/{id}/cancelar` → 200 `Reserva` | — |

## Composición

### Lista

[Encabezado](../componentes/encabezado-pantalla.md) App con acción [botón](../componentes/boton.md) Primario "Reservar sala" → [etiquetas](../componentes/etiqueta-tecnica.md) Filtro PRÓXIMAS · HISTORIAL → [panel](../componentes/panel.md) `RESERVAS` + [tabla](../componentes/tabla.md) Directorio: RESERVA (folio y servicio debajo) · FECHA · ESTADO · PAGO ("Antes del 18 nov, 14:30" si `Pre-reservada`; si no, "—") · "Ver reserva {folio}" (Secundario como enlace). < `punto-quiebre-escritorio`, tarjetas (`<dl>`), como en la ficha de tabla.

### Detalle

- Principal: panel `D1 RESERVA {folio}` (`<dl>`: estado, fecha y horario, servicio, especialistas, sala; cliente para el personal) → panel `D2 PRECIO` (tabla Partidas + "Precio calculado al reservar.") → panel `D3 CUOTAS` (tabla Partidas).
- Lateral: [indicador de estado](../componentes/indicador-estado.md) Barra con lo que toca según el estado (tabla Estados) y, si se puede cancelar, [botón](../componentes/boton.md) Peligro "Cancelar reserva" como enlace a la confirmación.
- Cancelar se muestra al dueño solo en `Pre-reservada` (con pagos el backend responde 409) y al Administrador en `Pre-reservada` y `Confirmada`. El personal no lo ve.

### Cancelar

Confirmación en página propia ([formularios](../patrones/formularios.md#prevención-de-errores)): panel `CANCELAR RESERVA {folio}` con `<dl>` (fecha, horario, servicio) y las consecuencias, cerrado por [barra de acciones](../componentes/barra-acciones.md) Formulario: "Volver a la reserva" (Secundario, enlace) + Peligro "Cancelar reserva {folio}".

Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md), [estados del sistema](../patrones/estados-sistema.md). Adaptabilidad: el lateral pasa debajo del principal.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lista | Sin reservas | Vacío: "Aún no tienes reservas" + "Elige un horario libre y reserva la sala en unos pasos." + Primario "Reservar sala" (sin filtros ni acción en el encabezado) |
| Lista | Filtro sin resultados | "No tienes reservas próximas." / "Aún no hay reservas en tu historial." + "Ver historial" / "Ver próximas" (Secundario, el otro filtro) |
| Lista, detalle | Carga | Panel con "Cargando…", `aria-busy` |
| Detalle | `Pre-reservada` | Barra Pendiente "PAGA EL ANTICIPO ANTES DEL 18 NOV, 14:30" + dato "faltan 2 d 3 h". Con menos de 1 h, además [aviso](../componentes/aviso.md) Aviso "Tu reserva vence en 45 min. Si no registras el pago, se cancelará y el horario se liberará." |
| Detalle | `Pre-reservada` con `vence_pago` pasado | Se muestra como caducada (la disponibilidad ya la trata como libre): Barra Problema "CADUCADA" + "Venció sin pago el 18 nov, 14:30. El horario quedó libre." Sin cancelar |
| Detalle | `Confirmada` / `En curso` / `Finalizada` | Barra Correcto "CONFIRMADA · Pagas el resto al terminar la sesión." / Neutro "EN CURSO" / Correcto "FINALIZADA" (cuota `al_terminar` pendiente: "Falta pagar el resto: {monto}.") |
| Detalle | `Cancelada` | Barra Neutro "CANCELADA" + motivo: caducada "Caducó sin pago el {vence_pago}. El horario se liberó." · cliente "La cancelaste." · administrador "La canceló el estudio." |
| Detalle | `?aviso=reserva-cancelada` | Aviso Éxito "Reserva cancelada. El horario quedó libre y no se te cobró nada." |
| Cancelar | Enviando | Botón en Carga "Cancelando…"; "Volver a la reserva" deshabilitado |
| Cancelar | 409 `tiene_pagos` | Aviso Error "Ya registraste un pago para esta reserva, así que no puedes cancelarla desde aquí. Escríbenos para revisar tu caso." + "Volver a la reserva" |
| Cancelar | 409 `no_cancelable` | Aviso Información "Esta reserva ya no se puede cancelar: está {estado}." + "Volver a la reserva" |
| Todas | 401 | Aviso "Tu sesión no es válida. Inicia sesión para ver tus reservas." + "Ir al acceso" (`?volver=` con la vista) |
| Detalle, cancelar | 403 / 404 | En lugar del bloque: `[403] SIN PERMISO` "Esta reserva no es tuya." / `[404] RESERVA NO ENCONTRADA` "No encontramos esta reserva." + "Volver a mis reservas" |
| Todas | 503 · red caída · no JSON | Aviso Error "El servicio no responde. Inténtalo de nuevo en unos minutos." · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal. Inténtalo de nuevo." Al cargar, con "Reintentar"; al cancelar, sin él (el botón sigue disponible) |
| Todas | Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Claves `aviso` (lista cerrada): `reserva-cancelada`. Permisos: el cliente solo ve las suyas; la API es la barrera (403).

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Lista | Inicio / Reservas · `[P2] SALA / RESERVAS` | MIS RESERVAS | Tus horarios en la sala, su estado y lo que falta pagar. |
| Detalle | Inicio / Reservas / {folio} (personal: Inicio / Agenda / {folio}) | RESERVA {folio} | {servicio} · {fecha}, {HH:mm}–{HH:mm} |
| Cancelar | Inicio / Reservas / {folio} / Cancelar | CANCELAR RESERVA | Revisa lo que pasa antes de cancelar. |

Consecuencias (RN-20): "El horario se libera al momento y no se te cobra nada. No se puede deshacer: si quieres ese horario otra vez, tendrás que reservarlo de nuevo si sigue libre." Columnas: RESERVA · FECHA · ESTADO · PAGO.

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`. Tablas con `<caption>` y folio o cuota como `<th scope="row">`.
- Filtros: enlaces con `aria-current="true"` en el aplicado. El plazo restante se recalcula cada minuto sin región viva; el aviso de menos de 1 h aparece al cargar y no se anuncia solo.
- Región `role="status"` estable de la isla: anuncia la carga ("3 reservas próximas") y el resultado; al fallar la cancelación, el foco va al aviso.

## Pendientes

- **dev-backend:** valores de `motivo_cancelacion` (propuesta: `caducada`, `cliente`, `administrador`) y de `cuotas[].estado` (propuesta: `pendiente`, `pagada`).
- **leader:** destino RESERVAS (`calendar-check`) para el cliente; registrar `<bugalu-reservas>` en [frontend-islas](../../01-arquitectura/frontend-islas.md). La acción "Registrar pago" del detalle llega con [RF-05](../../03-requerimientos/RF-05.md).
