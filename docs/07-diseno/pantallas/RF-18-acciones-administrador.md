---
id: pantalla-rf-18-acciones-administrador
titulo: Pantalla — Inasistencia, caso excepcional y cancelación por el estudio o a pedido del cliente
estado: borrador
depende_de: [RF-18, ADR-015, pantalla-rf-18-cancelar, pantalla-rf-18-reprogramar, pantalla-rf-04-mis-reservas, pantalla-rf-03-calendario, diseno-brief, patron-formularios, patron-estados-sistema, comp-panel, comp-campo, comp-casilla, comp-boton, comp-barra-acciones, comp-aviso, comp-etiqueta-tecnica, comp-tabla]
---

# Acciones del estudio sobre una reserva

| Campo | Valor |
|---|---|
| Requerimiento | [RF-18](../../03-requerimientos/RF-18.md): CA-04, CA-11, CA-12, CA-13 (cancelar por el estudio), CA-16 |
| Actores | Administrador (todo); Personal (solo "No asistió") |
| Estructura | App, panel interno; **amplía** el detalle de [mis reservas](RF-04-mis-reservas.md#detalle) y la [agenda](RF-03-calendario.md) |
| Ruta | `/app/reservas/detalle?id=` (URL: `id`, `aviso`, `accion=inasistencia` para abrir su panel desde la agenda); `/app/agenda?vista=lista` |
| Isla | `<bugalu-reservas vista="detalle">` y `<bugalu-calendario modo="personal">` (existentes) |

Las tres acciones siguen la [decisión de cancelar](RF-04-mis-reservas.md#cancelar): el botón del lateral se sustituye por un panel con consecuencias y una barra de acciones Móvil ("Volver a la reserva" + la acción); foco al `<h2>` del panel y, al volver, al botón que lo abrió. Una sola a la vez.

## Recorrido

1. **No asistió.** Personal o Administrador abre la reserva desde la agenda (o pulsa "Marcar no asistió · {folio}" en LISTA, que llega con `?accion=inasistencia`). Pasados los minutos de tolerancia, confirma; la reserva queda `No asistió`.
2. **Tratar como nivel 1.** El Administrador, ante una emergencia con sustento, abre una reserva cancelada por el cliente en nivel 2 o 3, o una inasistencia, escribe el motivo y confirma.
3. **Cancelar.** El Administrador pulsa "Cancelar reserva", elige si cancela el estudio o el cliente por otro canal, completa nota (y fecha y hora del aviso) y confirma. Si cancela el estudio con pagos, el cliente elige después ([elección](RF-18-reprogramar.md#elección-tras-una-cancelación-del-estudio)); el Administrador también puede elegir por él.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Tolerancia | `parametros_aplicados.minutos_tolerancia_inasistencia` → `{t}` (ver [preguntas de cancelar](RF-18-cancelar.md#preguntas-para-leader)) | "15 minutos"; hora desde la que se puede: `inicio + t`, `HH:mm` |
| Marcar | `POST /reservas/{id}/inasistencia` → 200 `Reserva` | — |
| Caso excepcional | `POST /reservas/{id}/excepcion {motivo}` → 200 `Reserva` | Área MOTIVO, 10–500 |
| Retenido | `cancelacion.retenido` o, en `No asistió`, `pagado` | Importe |
| Cancelar | `POST /reservas/{id}/cancelar {por, nota, aviso_en?}` → 200 `Reserva` | `por`: `estudio` \| `cliente`; nota Área ≤ 300; `aviso_en` con FECHA (`date`) y HORA (`time`, `step="60"`) en hora de Lima, enviados como ISO 8601 con zona |
| Créditos del cliente | En su ficha ([créditos](RF-18-creditos.md#ficha-del-cliente-administrador)) | — |

## Composición

| Acción | Botón en el lateral | Panel |
|---|---|---|
| No asistió | Peligro "Marcar no asistió". Se ve desde `inicio` hasta `fin` en `Pre-reservada`, `Confirmada` o `En curso`. Antes de `inicio + t`: `aria-disabled="true"` (sigue enfocable) y ayuda "Podrás marcarlo desde las {HH:mm}, {t} minutos después del inicio." | `MARCAR INASISTENCIA · {folio}`: "{cliente} no llegó en los primeros {t} minutos." → consecuencias → "Volver a la reserva" + Peligro "Marcar no asistió" |
| Tratar como nivel 1 | Secundario "Tratar como nivel 1". Solo Administrador; en `Cancelada` con `cancelacion.por = cliente`, nivel 2 o 3 y `retenido` > 0, o en `No asistió` con `pagado` > 0; sin `cancelacion.excepcion` | `TRATAR COMO NIVEL 1 · {folio}`: "Para emergencias de salud, duelos, desastres o paros que impidieron avisar a tiempo, con un sustento razonable." → `<dl>` RETENIDO HOY → Área MOTIVO → consecuencias → "Volver a la reserva" + Primario "Tratar como nivel 1" |
| Cancelar | Peligro "Cancelar reserva" (como hoy: Administrador, `Pre-reservada` o `Confirmada`, antes del inicio) | `CANCELAR RESERVA {folio}`: `<fieldset>` ¿QUIÉN PIDE CANCELAR? con [casillas](../componentes/casilla.md) Radio sin valor por defecto → campos de la opción → consecuencias → "Volver a la reserva" + Peligro "Cancelar reserva {folio}" |

**Opciones de cancelar** (sustituye la NOTA SOBRE EL REEMBOLSO de RF-04):

| Opción (detalle de la casilla) | Campos | Consecuencias |
|---|---|---|
| "El estudio" ("Falla técnica, ausencia del especialista o fuerza mayor.") | NOTA PARA EL CLIENTE (obligatoria si hay pagos) | Con pagos: "El horario se libera al momento. El cliente elegirá en la app entre reprogramar sin costo o la devolución íntegra de {pagado}, que haces en un máximo de 7 días hábiles. Le avisamos por correo." Sin pagos: "El horario se libera al momento y avisamos al cliente por correo." |
| "El cliente, por otro canal" ("Te escribió por WhatsApp, correo o teléfono.") | FECHA DEL AVISO + HORA DEL AVISO (en fila; una columna < `punto-quiebre-tableta`) y NOTA (obligatoria) | "Se aplica la misma política que si cancelara desde la app, con el nivel que corresponde a la fecha y hora de su mensaje. El horario se libera al momento y le avisamos por correo con el detalle." Con vista previa (Preguntas): el `<dl>` del [panel del cliente](RF-18-cancelar.md#composición) |

**Agenda:** en la cuadrícula y en LISTA, la etiqueta de estado suma NO ASISTIÓ (Alerta); el bloque sigue ocupado. En LISTA, la fila que está entre `inicio + t` y `fin`, en un estado que lo admite, suma Secundario "Marcar no asistió · {folio}" (enlace al detalle con `?accion=inasistencia`). Fuera de esa ventana no hay acción en la fila: el detalle explica por qué.

## Estados

| Acción | Situación | Forma y texto |
|---|---|---|
| Todas | Enviando | Botón en Carga ("Marcando…", "Aplicando…", "Cancelando…"); "Volver a la reserva" deshabilitado |
| No asistió | Pulsado antes de tiempo | Bajo el botón: "Aún no pasaron {t} minutos desde el inicio. Podrás marcarlo desde las {HH:mm}." Mismo texto para el 409 `tolerancia_no_cumplida` |
| No asistió | 409 `no_aplicable` | Panel cerrado, detalle recargado; aviso Información "Esta reserva ya no admite marcar la inasistencia: está {estado}." |
| No asistió | Éxito | `?aviso=inasistencia-marcada` "Inasistencia registrada. Avisamos al cliente por correo." |
| Nivel 1 | Validación local / 422 | "Escribe el motivo, de 10 a 500 caracteres." |
| Nivel 1 | 409 `excepcion_ya_aplicada` · `excepcion_no_aplicable` | Panel cerrado, detalle recargado; aviso Información "Esta reserva ya se trató como nivel 1, quizá desde otra sesión." · "Esta reserva no admite el caso excepcional." |
| Nivel 1 | Éxito | `?aviso=excepcion-aplicada` "Tratada como nivel 1. {credito} pasaron a crédito del cliente, con devolución posible." |
| Cancelar | Sin opción | Error del grupo: "Elige quién pide cancelar." |
| Cancelar | 422 `nota_requerida` / local | Bajo la nota: "Escribe la nota para el cliente." · "La nota admite hasta 300 caracteres." |
| Cancelar | 422 `aviso_invalido` / local | Bajo FECHA DEL AVISO: "El aviso no puede ser futuro ni anterior a cuando se hizo la reserva." |
| Cancelar | 409 `no_cancelable` | Como en [mis reservas](RF-04-mis-reservas.md#estados) |
| Cancelar | Éxito | `?aviso=reserva-cancelada` para el Administrador: estudio con pagos "Reserva cancelada. El horario quedó libre y avisamos al cliente para que elija entre reprogramar sin costo o la devolución íntegra." · a pedido del cliente "Reserva cancelada a pedido del cliente ({nivel en palabras}). Le avisamos con el detalle." · sin pagos, el de RF-04 |
| Todas | 401 · 403 · 404 · 503 · red · no JSON · sin JS | Como en [mis reservas](RF-04-mis-reservas.md#estados); al enviar, sin "Reintentar" |

Claves `aviso` nuevas: `inasistencia-marcada`, `excepcion-aplicada`. `?accion=inasistencia` abre el panel solo si el botón está habilitado; si no, se ignora y queda la ayuda. Permisos: el personal no ve "Tratar como nivel 1" ni "Cancelar reserva"; el cliente no ve ninguna de las tres.

## Copy

| Elemento | Texto |
|---|---|
| Consecuencias de no asistió | "Se retiene lo pagado ({pagado}), se anula el saldo y no hay crédito ni cobro adicional. El horario sigue ocupado. Avisamos al cliente por correo. No se puede deshacer: solo el Administrador puede tratarla después como nivel 1." |
| Consecuencias de nivel 1 | "Lo retenido ({retenido}) pasa a un crédito de caso excepcional que vence {d} días después de hoy y admite devolución. Solo se puede hacer una vez por reserva y queda registrado quién y por qué. No se puede deshacer." |
| Ayudas | Motivo: "Qué pasó y qué sustento recibiste. El cliente lo verá en su reserva." · Nota a pedido del cliente: "Canal y lo que pidió. Por ejemplo: «WhatsApp: no puede venir por un viaje»." · Fecha y hora: "Las de su mensaje, hora de Lima." |
| Etiquetas | ¿QUIÉN PIDE CANCELAR? · NOTA PARA EL CLIENTE · FECHA DEL AVISO · HORA DEL AVISO · NOTA · MOTIVO · RETENIDO HOY |

## Accesibilidad

- Cada panel es `<section aria-labelledby>` con `<h2>`; ¿QUIÉN PIDE CANCELAR? es `<fieldset>` + `<legend>`, y los campos de la opción aparecen justo después de su casilla (`aria-controls`).
- "Marcar no asistió" deshabilitado sigue enfocable y su ayuda va en `aria-describedby`. La hora en que se habilita no se actualiza sola: al pulsarlo se vuelve a comprobar.
- Región `role="status"` de la isla para cada resultado; al fallar un envío, el foco va al aviso. En LISTA, la acción lleva el folio en el nombre.

## Preguntas para leader

1. `GET /reservas/{id}/cancelacion` no admite `aviso_en`: el Administrador no puede ver el nivel antes de cancelar a pedido del cliente. Propuesta: `?aviso_en=` en la vista previa; sin él, solo el texto de consecuencias.
2. En `No asistió`, ¿dónde queda la excepción: `cancelacion.excepcion` también? El detalle la muestra en D4 ([cancelar](RF-18-cancelar.md#composición)).
3. `{d}` (días de vigencia) y `{t}` (tolerancia) dependen de exponer `parametros_aplicados` (misma pregunta que en cancelar).
