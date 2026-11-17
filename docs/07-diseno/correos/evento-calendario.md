---
id: correo-evento-calendario
titulo: Correo — Evento de calendario (.ics y enlaces)
estado: borrador
depende_de: [ADR-016, correo-plantilla]
---

# Evento de calendario

Bloque 6 de la [plantilla](plantilla.md) y el `.ics` que lo acompaña ([ADR-016](../../00-proyecto/decisiones/ADR-016-correos-con-plantilla-y-calendario.md), puntos 2 a 4).

## Qué avisos lo llevan

El cliente tiene un evento en su calendario solo desde que su reserva se **confirma** (antes es una pre-reserva que puede caducar). Por eso:

| Aviso | Evento | Condición |
|---|---|---|
| `pago_aprobado` | `REQUEST` (alta) | `reserva_confirmada` es verdadero: es la confirmación de la reserva |
| `reserva_reprogramada` | `REQUEST` (reemplaza) | La reserva tiene evento |
| `reserva_cancelada_estudio` | `CANCEL` | La reserva tiene evento |
| `reserva_cancelada_con_pagos` | `CANCEL` | La reserva tiene evento |
| Todos los demás | Ninguno | — |

**La reserva tiene evento** si antes de este aviso existe en `notificacion` un `pago_aprobado` de la misma `id_reserva` con `reserva_confirmada = true`. Cubre los casos límite sin columnas nuevas: una pre-reserva cancelada o reprogramada no recibe nada; una reserva cancelada por el estudio y luego reprogramada sin costo recibe `CANCEL` y después un `REQUEST` con `SEQUENCE` mayor, que la devuelve al calendario.

No llevan evento: `reserva_creada` (aún pre-reserva), `inasistencia_marcada` (el horario ya pasó), `reserva_caducada` (nunca se confirmó), los avisos de pagos, créditos, devoluciones y textos legales, y todos los del Administrador.

Asesorías ([RF-15](../../03-requerimientos/RF-15.md), cuando exista): mismas reglas con su confirmación, reprogramación y cancelación; `UID` `asesoria-{id_asesoria}@bugalu` y la ubicación de abajo.

## Archivo `.ics`

iCalendar (RFC 5545 y 5546), UTF-8, líneas con CRLF y plegadas a 75 octetos; textos escapados (`\\`, `\;`, `\,`, saltos como `\n`). Nombre: `bugalu-{folio}.ics`. Un `VEVENT` por archivo.

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Bugalú Studio//Plataforma//ES
CALSCALE:GREGORIAN
METHOD:{REQUEST|CANCEL}
BEGIN:VTIMEZONE
TZID:America/Lima
BEGIN:STANDARD
DTSTART:19700101T000000
TZOFFSETFROM:-0500
TZOFFSETTO:-0500
TZNAME:-05
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
UID:reserva-{id_reserva}@bugalu
SEQUENCE:{segundos Unix de notificacion.creada_en}
DTSTAMP:{momento del envío, UTC, AAAAMMDDTHHMMSSZ}
DTSTART;TZID=America/Lima:{inicio en Lima, AAAAMMDDTHHMMSS}
DTEND;TZID=America/Lima:{fin en Lima}
SUMMARY:{título}
LOCATION:{ubicación}
DESCRIPTION:{descripción}
URL:{url}/app/reservas/detalle?id={id_reserva}
STATUS:{CONFIRMED|CANCELLED}
TRANSP:OPAQUE
ORGANIZER;CN=Bugalú Studio:mailto:{remitente}
ATTENDEE;CN={destinatario};ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=FALSE:mailto:{destinatario}
END:VEVENT
END:VCALENDAR
```

- **`UID`** estable por reserva: el mismo en el alta, cada reprogramación y la cancelación.
- **`SEQUENCE`**: los segundos Unix de `creada_en` del aviso. Crece con cada cambio y respeta el orden aunque un envío se reintente o salga tarde; no necesita contador propio.
- `RSVP=FALSE` y `PARTSTAT=ACCEPTED`: es una copia, no una invitación; evita los botones "Sí / No / Quizás" donde el cliente lo respeta.
- `CANCEL` repite `UID`, `DTSTART`, `DTEND` y `SUMMARY` del evento, con `SEQUENCE` nuevo y `STATUS:CANCELLED`.
- En el mensaje va dos veces ([estructura](plantilla.md#mensaje)): como parte `text/calendar; method=…` dentro de `multipart/alternative` (Gmail y Outlook muestran la tarjeta del evento) y como adjunto `application/ics` (clientes que solo muestran adjuntos).

**Datos que necesita:** `id_reserva`, `folio`, `inicio`, `fin`, `servicio` (nombre) y `sala` (nombre de `sala_tecnica`). Hoy `pago_aprobado` no trae `inicio`, `fin`, `servicio` ni `sala`, y los demás no traen `servicio` ni `sala`: el backend los añade al aviso o los lee de la reserva al enviar.

## Copy del evento

| Campo | Texto |
|---|---|
| Título (`SUMMARY`) | `Bugalú Studio · {servicio} · {folio}` |
| Ubicación (`LOCATION`) | `Bugalú Studio, {sala}, Av. Javier Prado Este 5920, La Molina, Lima, Perú` |
| Descripción (`DESCRIPTION`) | Tres líneas, abajo |

```
Reserva {folio} en Bugalú Studio: {servicio}, {sala}.
Esta es una copia para tu calendario y no se sincroniza con la agenda de Bugalú. Lo vigente es lo que ves en Mis reservas: {url}/app/reservas/detalle?id={id_reserva}
¿Dudas? WhatsApp +51 925 530 800.
```

Asesorías: título `Bugalú Studio · Asesoría con {profesional} · {folio}`; ubicación presencial = el lugar escrito en la asesoría; virtual = `Videollamada`, con el enlace de Meet en `URL` y como primera línea de la descripción.

## Enlaces de respaldo

Solo en los avisos `REQUEST`. Hora en UTC (`AAAAMMDDTHHMMSSZ`) para Google e ISO con desfase para Outlook; parámetros con `urllib.parse.urlencode`.

| Texto del enlace | URL |
|---|---|
| Añadir a Google Calendar | `https://calendar.google.com/calendar/render?action=TEMPLATE&text={título}&dates={inicio UTC}/{fin UTC}&details={descripción}&location={ubicación}&ctz=America/Lima` |
| Añadir a Outlook | `https://outlook.live.com/calendar/0/deeplink/compose?path=/calendar/action/compose&rru=addevent&subject={título}&startdt={inicio ISO -05:00}&enddt={fin ISO -05:00}&body={descripción}&location={ubicación}` |

## Copy del bloque

Título del bloque (`<h2>`, técnica): **Evento de calendario**.

| Caso | Texto | Aviso de ADR-016 | Enlaces |
|---|---|---|---|
| `REQUEST` en `pago_aprobado` | Adjuntamos el evento de tu reserva (archivo bugalu-{folio}.ics). Ábrelo para añadirlo a Google Calendar, Outlook, Apple Calendar u otro calendario. | Sí | Sí |
| `REQUEST` en `reserva_reprogramada` | Adjuntamos el evento con el nuevo horario (archivo bugalu-{folio}.ics). Si ya habías añadido el archivo anterior, este lo reemplaza. Si usaste los enlaces de Google o Outlook, borra el evento anterior: esos enlaces crean uno nuevo y no reemplazan el que ya tenías. | Sí | Sí |
| `CANCEL` | Adjuntamos la cancelación del evento (archivo bugalu-{folio}.ics). Si añadiste tu reserva con el archivo, al abrirlo se quita de tu calendario. Si usaste los enlaces de Google o Outlook, bórrala a mano. | No | No |

**Aviso de ADR-016** (texto exacto, párrafo propio): "Este evento es una copia para tu calendario y no se sincroniza con la agenda de Bugalú. Si tu reserva cambia, te enviaremos una actualización; lo vigente es lo que ves en Mis reservas."

Texto plano del bloque:

```
EVENTO DE CALENDARIO
{Texto del caso}
{Aviso de ADR-016, si aplica}
Añadir a Google Calendar: {url_google}     (si aplica)
Añadir a Outlook: {url_outlook}            (si aplica)
```

## Prueba manual antes de producción

ADR-016, consecuencias: con una cuenta de Gmail y una de Outlook.com, confirmar, reprogramar y cancelar una reserva; comprobar que el evento se crea, se mueve y se quita sin duplicarse, que el logo se ve y que Apple Mail muestra el HTML (no la parte de calendario) como cuerpo.
