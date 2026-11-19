---
id: pantalla-rf-15-gestion
titulo: Pantalla — Detalle de la asesoría para el profesional y el Administrador (etapa B)
estado: borrador
depende_de: [RF-15, RF-18, ADR-015, pantalla-rf-15-mis-asesorias, pantalla-rf-15-cierre, pantalla-rf-18-acciones-administrador, pantalla-rf-18-reprogramar, pantalla-rf-04-mis-reservas, diseno-brief, patron-formularios, patron-estados-sistema, comp-panel, comp-campo, comp-casilla, comp-boton, comp-barra-acciones, comp-aviso, comp-etiqueta-tecnica, comp-indicador-estado]
---

# Detalle de la asesoría (profesional y Administrador)

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-09, CA-10 (acciones del Administrador), CA-11, CA-16, CA-17 |
| Actores | Profesional artístico (las suyas); Administrador (todas) |
| Estructura | App, panel interno; **amplía** el detalle de [mis asesorías](RF-15-mis-asesorias.md#composición) |
| Ruta | `/app/asesorias/detalle?id=` (URL: `id`, `aviso`, `accion=lugar\|cerrar`) |
| Isla | `<bugalu-asesorias vista="detalle">` |

Mismo detalle que el del cliente, con estas reglas: los paneles de acción siguen la [decisión de cancelar](RF-04-mis-reservas.md#cancelar) (el botón del lateral se sustituye por un panel con consecuencias y [barra de acciones](../componentes/barra-acciones.md) Móvil "Volver a la asesoría" + la acción; foco al `<h2>` del panel y, al volver, al botón que lo abrió; uno a la vez). Cerrar y notas: [cierre](RF-15-cierre.md).

## Qué ve cada rol

| Panel | Profesional | Administrador |
|---|---|---|
| `D1 ASESORÍA {folio}` | Sí, sin CONDICIONES | Sí |
| `D0 CLIENTE` (antes de D1) | `<dl>`: NOMBRE (artístico, y nombre debajo) · TELÉFONO (enlace `tel:`) · CORREO (enlace `mailto:`) | Igual |
| `D2 PRECIO` · `D3 CUOTAS` | No (CA-08: no ve pagos ni montos) | Sí, con el pago enlazado a [revisar pago](RF-05-pagos.md) |
| `D4 CANCELACIÓN` | Solo AVISO y A PEDIDO DE ("Del cliente" · "Del estudio" · "Inasistencia"), sin montos ni nota | El de [cancelar](RF-18-cancelar.md#composición) |
| `D5 REPROGRAMACIONES` | FECHA DEL CAMBIO · ANTES · AHORA | Más NIVEL y PENALIZACIÓN |
| `N1 NOTAS INTERNAS` | Sí ([cierre](RF-15-cierre.md#notas-internas)) | Sí |

## Lugar o enlace

Profesional o Administrador, en `Pendiente de pago` o `Confirmada` y antes del `fin` (CA-09).

| Región | Contenido |
|---|---|
| Lateral | Bloque `LUGAR O ENLACE`: el valor actual (o etiqueta Aviso POR CONFIRMAR) + Secundario "Registrar lugar" · "Cambiar lugar" (presencial) / "Registrar enlace" · "Cambiar enlace" (virtual). Si falta y la cita es en menos de 48 h, encima, aviso Aviso "Falta confirmar {el lugar / el enlace}. El cliente lo espera antes de la cita." |
| Panel (al pulsar o con `?accion=lugar`) | `LUGAR O ENLACE · {folio}`: `<fieldset>` MODALIDAD ([casillas](../componentes/casilla.md) Radio, marcada la actual) → si Presencial, LUGAR ([campo](../componentes/campo.md) Área, 1–300, `maxlength="300"`); si Virtual, ENLACE (Texto `type="url"`, `inputmode="url"`, `spellcheck="false"`) → consecuencias → "Volver a la asesoría" + Primario "Guardar y avisar" |
| Envío | `PATCH /asesorias/{id}/encuentro {modalidad, lugar}` o `{modalidad, enlace}` → 200 `Asesoria` |

El cliente no lo edita (CA-09). Hasta [RF-19](../../03-requerimientos/RF-19.md) el enlace se pega a mano.

## Cancelación del estudio y acciones del Administrador

Las de [acciones del Administrador](RF-18-acciones-administrador.md#composición), con `POST /reservas/{id}/…` y estas diferencias:

| Acción | En la asesoría |
|---|---|
| "Cancelar asesoría" (Peligro, solo Administrador) | Visible en `Pendiente de pago` o `Confirmada` **también tras el inicio**, mientras no esté cerrada (CA-11). Opción "El estudio", detalle: "El profesional no puede darla, falla técnica o fuerza mayor." Opción "El cliente, por otro canal": solo antes del inicio (después, solo se pinta "El estudio") |
| Consecuencias de "El estudio" con pagos | "El horario se libera al momento. El cliente elegirá en la app entre reprogramar sin costo con {profesional} o la devolución íntegra de {pagado}, que haces en un máximo de 7 días hábiles. Si prefiere a otro profesional, agenda una asesoría nueva. Avisamos al cliente y a {profesional} por correo." |
| "Elegir por el cliente" | La [elección](RF-18-reprogramar.md#elección-tras-una-cancelación-del-estudio), con el copy de [mis asesorías](RF-15-mis-asesorias.md#composición) |
| "Tratar como nivel 1" | Igual; consecuencias: "Lo retenido ({retenido}) pasa a un crédito de caso excepcional que vence {d} días después de hoy. Nació de una asesoría: no admite devolución en dinero (sí la parte que venía de un crédito de sala). Solo una vez por asesoría." |
| "Marcar no asistió" | Va en [cierre](RF-15-cierre.md#cerrar-la-asesoría): lo hacen el profesional y el Administrador, no el personal |

**Profesional:** no cancela. En el lateral, en `Pendiente de pago` o `Confirmada`: "¿No puedes darla? Pide al Administrador que la cancele por el estudio. El cliente podrá reprogramar contigo sin costo o pedir la devolución."

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lugar | Validación local · 422 `datos_invalidos` | "Escribe el lugar, hasta 300 caracteres." · "Elige si es presencial o virtual." |
| Lugar | 422 `enlace_invalido` (también local) | Bajo ENLACE: "Pega un enlace de Google Meet que empiece por https://meet.google.com/." |
| Lugar | 409 `no_editable` | Panel cerrado, detalle recargado; aviso Información "Esta asesoría ya no admite cambios de lugar o enlace: está {estado} o ya terminó." |
| Lugar | Enviando · éxito | "Guardando…"; `?aviso=lugar-guardado` "Guardado. Avisamos a {cliente} y a {profesional} por correo con el evento actualizado." |
| Cancelar y nivel 1 | Todos | Los de [acciones del Administrador](RF-18-acciones-administrador.md#estados) con "asesoría"; éxito de "El estudio": "Asesoría cancelada. Avisamos al cliente para que elija y a {profesional}." |
| Detalle | 404 (ajena o inexistente) | `[404] ASESORÍA NO ENCONTRADA` "No encontramos esta asesoría." + "Volver a asesorías" (CA-16: una ajena es 404) |
| Todas | 401 · 503 · red · no JSON · sin JS | Como en [agenda](RF-15-agenda.md#estados); al enviar, sin "Reintentar" y con los datos conservados |

Claves `aviso` nuevas (lista cerrada de la isla): `lugar-guardado`. `?accion=lugar` abre el panel solo si la acción está disponible.

## Copy

| Elemento | Texto |
|---|---|
| Ruta | Profesional: Inicio / Asesorías / {folio} · Administrador: Inicio / Asesorías / Agendadas / {folio} |
| Título · descripción | ASESORÍA {folio} · "Con {cliente} · {fecha}, {HH:mm}–{HH:mm}" (Administrador: "{cliente} con {profesional} · …") |
| Ayudas | LUGAR: "Ambiente del estudio o dirección, con una referencia. Por ejemplo: «Ambiente 2 del estudio, segundo piso»." · ENLACE: "Crea la reunión en Google Meet y pega aquí su enlace." |
| Consecuencias del lugar | "Avisamos a {cliente} y a {profesional} por correo, con el evento de calendario actualizado. Escribe solo lo que ya acordaron." |
| Etiquetas | MODALIDAD · LUGAR · ENLACE · NOMBRE · TELÉFONO · CORREO |

## Accesibilidad

- D0 es `<section>` con `<h2>` CLIENTE; los enlaces `tel:` y `mailto:` llevan el dato visible como nombre.
- MODALIDAD es `<fieldset>` + `<legend>`; el campo de la opción aparece justo después de su casilla (`aria-controls`) y, al cambiar, el foco se queda en la casilla.
- Región `role="status"` para cada resultado; al fallar un envío, el foco va al aviso.

## Preguntas

1. Al pasar de presencial a virtual sin enlace (o al revés), ¿la API guarda la modalidad con el dato en `null` ("por confirmar") y borra el de la otra modalidad? La spec envía solo el campo de la modalidad elegida y admite dejarlo vacío solo si la API lo acepta.
2. `Devolucion` no dice si su reserva es sala o asesoría: la cola de [devoluciones](RF-18-devoluciones.md) no sabe a qué detalle enlazar. Proponemos `Devolucion.tipo_reserva` (o `reserva: {id, folio, tipo}`).
