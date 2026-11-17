---
id: ADR-016
titulo: Correos con plantilla de marca y evento de calendario adjunto
estado: aprobado
depende_de: [ADR-011, ADR-015]
---

# ADR-016: Correos con plantilla de marca y evento de calendario adjunto

## Contexto

ADR-015 pide correos de la plataforma "con `.ics` y una plantilla con el diseño de la marca e información útil de la empresa (sin invitación propia de Google)". Hoy los avisos salen solo en texto plano por el SMTP de Gmail del estudio ([ADR-011](ADR-011-correo-gmail-del-estudio.md)) y sin `.ics`. El usuario (2026-11-17) pide la plantilla y el archivo de calendario para que el cliente lo añada a Google Calendar, Outlook u otro, avisando que ese evento no está sincronizado con la agenda real de Bugalú, y que la opción no cargue costos.

## Opciones

| Opción | Costo | Cobertura | Actualizaciones |
|---|---|---|---|
| `.ics` adjunto (iCalendar, RFC 5545/5546) | 0: se genera en el backend y viaja en el mismo correo | Gmail, Outlook, Apple Calendar y casi cualquier cliente | Con `UID` estable por reserva y `SEQUENCE` creciente, una reprogramación reemplaza el evento y una cancelación (`METHOD:CANCEL`) lo quita |
| Enlaces "Añadir a Google Calendar" y "Outlook.com" | 0 | Solo esos dos; abren el navegador | No se actualizan: crean un evento nuevo cada vez |
| Calendario suscrito por cliente (`webcal://` con token) | 0 en dinero, pero un endpoint público más y su seguridad | Todos los que admiten suscripción | Automáticas, pero Google refresca cada 8 a 24 h |
| Invitaciones con la API de Google Calendar | 0 en dinero, credenciales OAuth y cuotas | Todos | Automáticas | 

## Decisión

1. **Plantilla de marca** para todos los correos de la plataforma: HTML sencillo compatible con clientes de correo (tablas, estilos en línea, sin imágenes remotas obligatorias), con su versión de **texto plano** en el mismo mensaje (`multipart/alternative`), logo, datos útiles de la empresa (razón social, dirección, WhatsApp, redes, enlace a "Mis reservas") y pie legal.
2. **`.ics` adjunto** en los correos de reserva confirmada, reprogramada y cancelada (y en las asesorías cuando exista [RF-15](../../03-requerimientos/RF-15.md)): un `VEVENT` por archivo, `UID` estable por reserva, `SEQUENCE` que crece con cada cambio, `METHOD:REQUEST` al confirmar o reprogramar y `METHOD:CANCEL` al cancelar, hora en zona `America/Lima`, sala, dirección y folio.
3. **Enlaces de respaldo** "Añadir a Google Calendar" y "Añadir a Outlook" en la plantilla, para clientes que no muestran el adjunto.
4. **Aviso visible** junto al evento: "Este evento es una copia para tu calendario y no se sincroniza con la agenda de Bugalú. Si tu reserva cambia, te enviaremos una actualización; lo vigente es lo que ves en Mis reservas."
5. Sin dependencias nuevas ni servicios de pago: se reutiliza el SMTP actual y la biblioteca estándar de Python para el mensaje y el `.ics`.

Se descartan el calendario suscrito (más superficie pública y refresco lento) y la API de Google (ADR-015 la excluye; credenciales y cuotas que mantener).

## Consecuencias

- El comportamiento de Gmail con `METHOD:REQUEST` varía según la cuenta: antes de producción se prueba a mano con una cuenta de Gmail y una de Outlook (confirmar, reprogramar y cancelar).
- Gmail gratuito limita los envíos diarios ([ADR-011](ADR-011-correo-gmail-del-estudio.md)); el `.ics` no cambia ese límite.
- La tarea vive en el módulo `notificaciones`; la spec visual del correo la escribe `disenador-ui` desde el brief.
