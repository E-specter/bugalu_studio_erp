---
id: pantalla-rf-15-correos
titulo: Pantalla — Correos de asesorías y recordatorio de 24 h (contenido)
estado: borrador
depende_de: [RF-15, RF-18, ADR-016, correo-plantilla, correo-avisos, correo-evento-calendario, pantalla-rf-15-mis-asesorias, pantalla-rf-15-gestion]
---

# Correos de asesorías

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-06 (datos para pagar), CA-09 (cambio de lugar o enlace), CA-11, CA-13 (constancia), CA-14 (recordatorio y `.ics`) |
| Envoltorio | [Plantilla de marca](../correos/plantilla.md) sin cambios: aquí solo asunto, cuerpo, botón, pie y evento. El cuerpo es texto que la plantilla convierte con las [reglas de siempre](../correos/avisos.md#del-texto-al-html) |
| Evento de calendario | [Evento de calendario](../correos/evento-calendario.md): `UID` `asesoria-{id}@bugalu`, título, ubicación y enlace de Meet de la sección Asesorías de allí |

Nombres de tipo propuestos (los fija dev-backend). Etiqueta `// ASESORÍA`; pie Cuenta para el cliente y el profesional. "Detalle" = `{url}/app/asesorias/detalle?id={id}`. Formato de valores: el de [reclamaciones](RF-16-correos.md#formato-de-los-valores); `{lugar}` vacío → "Por confirmar".

## Por tipo

| Tipo | Para | Cuándo | Asunto | Botón | Evento |
|---|---|---|---|---|---|
| `asesoria_creada` | Cliente | Al agendar | Asesoría {folio}: paga antes del {vence_pago} | Registrar pago → `{url}/app/asesorias/pagar?id={id}&cuota={id_cuota}` | No |
| `pago_aprobado` (existente) | Cliente | Al confirmarse | Asesoría {folio} confirmada | Ver mi asesoría → Detalle | `REQUEST` |
| `asesoria_confirmada_profesional` | Profesional | Al confirmarse | Nueva asesoría: {fecha}, {HH:mm} | Ver la asesoría → Detalle | `REQUEST` |
| `asesoria_encuentro_cambiado` | Cliente y profesional | Al registrar o cambiar modalidad, lugar o enlace | Asesoría {folio}: {lugar confirmado / enlace listo / cambió el lugar} | Ver mi asesoría / Ver la asesoría → Detalle | `REQUEST` si tiene evento |
| `reserva_reprogramada` (existente) | Cliente | Al reprogramar | Asesoría {folio}: nuevo horario | Ver mi asesoría → Detalle | `REQUEST` si tiene evento |
| `asesoria_reprogramada_profesional` | Profesional | Al reprogramar | Asesoría {folio} movida al {fecha}, {HH:mm} | Ver la asesoría → Detalle | `REQUEST` si tiene evento |
| `reserva_cancelada_*` (existentes) | Cliente | Al cancelar (cliente, estudio, caducada) | Los de hoy con "asesoría" | Ver mi asesoría → Detalle | `CANCEL` si tiene evento |
| `asesoria_cancelada_profesional` | Profesional | Al cancelar por cualquier motivo, si estaba `confirmada` | Asesoría {folio} cancelada | Ver mis asesorías → `{url}/app/asesorias/agenda` | `CANCEL` |
| `recordatorio_asesoria` | Cliente y profesional | Una vez por horario, con 24 h o menos, si estaba `confirmada` con más de 24 h | Recordatorio: asesoría del {D MMM} a las {HH:mm} | Ver mi asesoría / Ver la asesoría → Detalle | No |
| `recordatorio_reserva` | Cliente | Igual, reserva de sala `confirmada` | Recordatorio: tu sesión del {D MMM} a las {HH:mm} | Ver mi reserva → `{url}/app/reservas/detalle?id={id}` | No |
| `asesoria_realizada` | Cliente | Al marcar Realizada | Tu constancia de asistencia · {folio} | Ver mi constancia → `{url}/app/asesorias/constancia?id={id}` | No |
| `inasistencia_marcada` (existente) | Cliente | Al marcar No asistió | Asesoría {folio}: no asististe | Ver mi asesoría → Detalle | No |

Al profesional nunca van importes, pagos ni créditos (CA-08), y a nadie las notas internas (CA-13).

## Cuerpos nuevos

`asesoria_creada`:

```
Agendaste una asesoría con {profesional}. Queda apartada mientras pagas.

Folio: {folio}
Profesional: {profesional}
Fecha y hora: {fecha}, {HH:mm}–{HH:mm} (hora de Lima)
Duración: {duración}
Modalidad: {Presencial | Virtual (Google Meet)}
Total: {total} (incluye IGV)

Paga antes del {vence_pago} y registra tu comprobante desde tu asesoría. Si vence sin pago, se cancela y el horario se libera.

Datos para pagar:
- {método}: {texto}
```

`pago_aprobado` de una asesoría (sustituye al párrafo de la reserva): "Validamos tu pago. Tu asesoría con {profesional} está confirmada." + tabla (Folio, Fecha y hora, Duración, Modalidad, Lugar o Enlace) + presencial sin lugar: "Te confirmaremos el lugar antes de la cita." / virtual sin enlace: "Te enviaremos el enlace de Google Meet antes de la cita."

`asesoria_confirmada_profesional`:

```
{cliente} agendó una asesoría contigo y ya está confirmada.

Folio: {folio}
Cliente: {cliente}
Teléfono: {telefono}
Correo: {correo}
Fecha y hora: {fecha}, {HH:mm}–{HH:mm} (hora de Lima)
Modalidad: {Presencial | Virtual}
Lugar: {lugar}

{Si falta el lugar o el enlace:} Registra {el lugar / el enlace de Google Meet} en la asesoría para que le llegue a {cliente}.
```

`asesoria_encuentro_cambiado`: "{Profesional} {registró / cambió} {el lugar / el enlace} de tu asesoría." (al profesional: "Quedó registrado el cambio de tu asesoría con {cliente}.") + tabla (Folio, Fecha y hora, Modalidad, Lugar o Enlace) + "Si ya habías añadido el evento a tu calendario, el archivo adjunto lo actualiza."

`recordatorio_asesoria`: "Te recordamos tu asesoría con {profesional | cliente}." + tabla (Folio, Fecha y hora, Duración, Modalidad, Lugar o Enlace) + presencial: "Llega unos minutos antes. Si no llegas en los primeros {t} minutos, cuenta como inasistencia." · virtual: "Entra al enlace a la hora. Si no te conectas en los primeros {t} minutos, cuenta como inasistencia." Al profesional, sin la frase de inasistencia y, si falta el lugar o el enlace: "Aún falta registrar {el lugar / el enlace}."

`recordatorio_reserva`: "Te recordamos tu sesión en Bugalú Studio." + tabla (Folio, Servicio, Sala, Fecha y hora) + "Si no llegas en los primeros {t} minutos, cuenta como inasistencia." + con saldo: "El resto ({saldo}) se paga al terminar la sesión."

`asesoria_realizada`: "Gracias por tu asesoría con {profesional}. Tu constancia de asistencia está lista: ábrela para verla, imprimirla o guardarla en PDF." + tabla (Folio, Fecha, Duración, Modalidad). Sin adjunto: el enlace exige sesión.

`asesoria_cancelada_profesional`: "Se canceló tu asesoría con {cliente}. El horario quedó libre en tu agenda." + tabla (Folio, Fecha y hora) + "A pedido de: {el cliente | el estudio}." Si el estudio canceló: "Si {cliente} elige reprogramar contigo, te avisaremos."

`asesoria_reprogramada_profesional`: "{Cliente} movió su asesoría contigo." + tabla (Folio, Antes, Ahora, Modalidad, Lugar o Enlace).

## Preguntas

1. Copy del evento: el aviso de ADR-016 dice "lo vigente es lo que ves en Mis reservas"; en asesorías debe decir "en Mis asesorías" (o "en la plataforma"). ¿Lo ajusta [evento de calendario](../correos/evento-calendario.md)?
2. Estos tipos necesitan su fila en [avisos](../correos/avisos.md) (lo pide esa página antes de implementarse): tarea para `documentador`.
3. ¿El profesional recibe aviso de una asesoría `pre_reservada` que caduca o se cancela antes de confirmarse? CA-14 solo nombra confirmada; la spec no le envía nada.
