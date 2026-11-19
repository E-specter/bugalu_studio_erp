---
id: pantalla-rf-15-agendar
titulo: Pantalla — Agendar una asesoría (flujo por pasos, etapa B)
estado: borrador
depende_de: [RF-15, RF-17, RF-18, RF-20, legal-condiciones-de-contratacion, pantalla-rf-15-perfil-publico, pantalla-rf-04-reservar, pantalla-rf-17-registro-y-aceptaciones, diseno-brief, patron-flujo-por-pasos, patron-formularios, patron-estados-sistema, comp-calendario, comp-pasos, comp-resumen-persistente, comp-casilla, comp-tabla, comp-resumen-legal, comp-aviso, comp-barra-acciones, comp-indicador-estado]
---

# Agendar una asesoría

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-05 (inicio válido), CA-06, CA-07, CA-16, CA-17 (selector de duración, modalidad y horario con precio e IGV) |
| Actores | Visitante (crea su cuenta o entra en el paso 03) y Artista/Cliente; Personal y Administrador pueden agendar para sí. El rol `profesional` no agenda (CA-01) |
| Estructura | Flujo ([flujo por pasos](../patrones/flujo-por-pasos.md)), [flujo de dominio](../../02-dominio/flujos/agendar-asesoria.md) |
| Ruta | `/asesorias/agendar` → `/asesorias/agendar/horario` → (sin sesión: `/acceso?volver=`; con faltantes: `/asesorias/agendar/cuenta`) → `/asesorias/agendar/confirmar` → `/asesorias/agendar/listo?id=` |
| URL | `profesional` (id), `duracion` (30 o 60), `modalidad` (`presencial` · `virtual`), `fecha`, `vista`, `inicio` (ISO con zona), `id`, `aviso` |
| Isla | `<bugalu-agendar paso="asesoria\|horario\|cuenta\|confirmar\|listo">` (nueva) con [`<bugalu-calendario modo="asesoria" duracion>`](../componentes/calendario.md#modos) en 02 |

**Decisión del brief:** es el [flujo de reservar sala](RF-04-reservar.md) con otro objeto: sin borrador en el servidor (la elección viaja en la URL de cada paso), mismo paso de cuenta ([aceptaciones](RF-17-registro-y-aceptaciones.md)), misma revisión antes de comprometer y mismo paso Listo. Cinco pasos: ASESORÍA · HORARIO · CUENTA · CONFIRMAR · LISTO. La duración va **antes** del calendario porque decide qué inicios valen. Si a un paso le falta un dato anterior, la isla va (`location.replace`) al primer paso incompleto.

## Entrada

En el [perfil público](RF-15-perfil-publico.md#agendar-asesoría-en-la-etapa-a), "Agendar asesoría" deja de estar deshabilitado y pasa a enlace Primario grande a `/asesorias/agendar?profesional={id}`; desaparece la ayuda "Disponible pronto". Con una sola duración ofrecida, el enlace ya lleva `duracion`. Para el rol `profesional` no se pinta.

## Recorrido

1. **01 Asesoría:** elige duración (con su precio e IGV) y modalidad; "Continuar".
2. **02 Horario:** ve la semana del profesional y elige un inicio donde cabe su asesoría; "Continuar".
3. **03 Cuenta:** con sesión y nada pendiente, se salta (HECHO). Sin sesión, va al acceso con `volver` = paso 04; con datos o textos pendientes o siendo menor, `/asesorias/agendar/cuenta`, igual que `/reservar/cuenta` ([aceptaciones](RF-17-registro-y-aceptaciones.md#recorrido), pasos 4 y la tabla de estados).
4. **04 Confirmar:** revisa todo, el precio, cómo se acuerda el lugar o el enlace, marca las condiciones y pulsa "Agendar asesoría" (`POST /asesorias`).
5. **05 Listo:** folio, fecha límite de pago y siguientes pasos; "Registrar pago" o "Ver mi asesoría".

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Profesional | `GET /profesionales/{profesional}` → `nombre_artistico` o `nombre`, `especialidades`, `foto_url`, `duraciones[].{minutos, precio, igv}` | [Avatar](../componentes/avatar.md) Medio + nombre; especialidades separadas por comas |
| Duración y precio | `duraciones[]` (solo las ofrecidas) | "30 min" · "1 h"; precio `S/ 80,00`; IGV como la tabla del [perfil público](RF-15-perfil-publico.md#composición) (`igv.incluido`: "Incluye IGV (18 %): S/ 12,20"; si no: "S/ 80,00 + IGV (18 %) S/ 14,40 = S/ 94,40") |
| Disponibilidad | `GET /profesionales/{id}/disponibilidad?desde=&hasta=` | Calendario modo Asesoría con `duracion` ([ficha](../componentes/calendario.md#modos)) |
| Inicio y fin | Evento `calendario-inicio` → `inicio`; fin = inicio + duración | `D MMM, HH:mm–HH:mm` ([formato](../patrones/estructura-app.md#formato-de-datos)), "Horario de Lima" |
| Condiciones | `GET /textos-legales` → `condiciones_contratacion` vigente | [Resumen legal](../componentes/resumen-legal.md) Obligatoria; casilla con la frase de [Asesoría](../../08-legal/resumenes-para-pantallas.md#asesoría) y la versión real |
| Agendar | `POST /asesorias {id_profesional, inicio, duracion, modalidad, version_condiciones}` → 201 `Asesoria` | — |
| Listo | `GET /asesorias/{id}` → `folio`, `total`, `vence_pago`, `cuotas[0].id` | Folio en [etiqueta](../componentes/etiqueta-tecnica.md) Invertida; `vence_pago` como plazo restante |

El navegador no calcula precios: cada cifra viene de `duraciones[]` antes de agendar y de la `Asesoria` después.

## Composición

Todas: [cabecera-app](../componentes/cabecera-app.md) Flujo → [encabezado](../componentes/encabezado-pantalla.md) Flujo ("PASO 02 / 05") → [pasos](../componentes/pasos.md) → principal + [resumen persistente](../componentes/resumen-persistente.md) Solicitud "TU ASESORÍA", etiqueta "SIN CONFIRMAR": PROFESIONAL, DURACIÓN, MODALIDAD, FECHA, HORARIO; al pie, TOTAL. En 04 no se pinta (R1 y R2 lo muestran).

| Paso | Principal | Cierre |
|---|---|---|
| 01 | [Panel](../componentes/panel.md) `CON QUIÉN` (avatar, nombre, especialidades; enlace "Cambiar de profesional" → `/asesorias/`) → `<fieldset>` DURACIÓN ([casillas](../componentes/casilla.md) Radio con detalle: precio e IGV) → `<fieldset>` MODALIDAD (Radio con detalle, Copy) | [Botón](../componentes/boton.md) Primario grande "Continuar" (`arrow-right`) |
| 02 | Panel del calendario (su `<h2>` es el periodo; "Horario de Lima"), modo Asesoría con `duracion`; bajo él, "Tu asesoría dura {duración}: elige dónde empieza." | [Barra de acciones](../componentes/barra-acciones.md) Flujo: "Anterior" + "Continuar" |
| 04 | `R1 TU ASESORÍA` (`<dl>` PROFESIONAL · DURACIÓN · MODALIDAD · FECHA Y HORARIO, con "Cambiar" por dato) → `R2 PRECIO` ([tabla](../componentes/tabla.md) Partidas: "Asesoría de {duración} con {nombre}" · IMPORTE; pie TOTAL y la fila de IGV de [RF-20](RF-20-cambios-sensibles.md#desglose-de-igv)) → `R3 LUGAR O ENLACE` (texto según modalidad) → `R4 CONDICIONES` (resumen legal Obligatoria) | Barra Flujo: "Anterior" + "Agendar asesoría" |
| 05 | [Aviso](../componentes/aviso.md) Éxito → panel Destacado `L1 ASESORÍA {folio}` (`<dl>` + [indicador](../componentes/indicador-estado.md) Barra Pendiente "PENDIENTE DE PAGO" con el plazo) → panel `SIGUIENTES PASOS` (`<ol>`) | Primario "Registrar pago" (→ [pagar](RF-15-pagar-y-reprogramar.md#pagar)) + Secundario "Ver mi asesoría". Sin barra de flujo |

Adaptabilidad: la de [reservar](RF-04-reservar.md#composición) (pasos Compacta, resumen tras el cierre, calendario en lista de días < `punto-quiebre-tableta` con los inicios como botones). En 1440, principal y resumen lateral; en 390, una columna.

## Estados

| Situación | Forma y texto |
|---|---|
| 01 sin `profesional`, 404 o perfil no publicado | En lugar del paso: `[404] PERFIL NO DISPONIBLE` "Este perfil no existe o ya no está publicado." + "Ver el directorio" |
| 01 sin duración o sin modalidad al continuar | Error de grupo: "Elige cuánto dura tu asesoría." · "Elige si es presencial o por videollamada." + resumen "Revisa 2 campos" |
| 01 `duraciones` vacío | Aviso Información "{Nombre} aún no tiene precios publicados. Vuelve pronto." + "Ver el directorio"; sin formulario |
| 02 sin inicio al continuar | Aviso Error "Elige una hora de inicio en el calendario." con foco en el primer inicio visible (como [reservar](RF-04-reservar.md#estados)) |
| 02 semana sin inicios válidos | Bajo la barra del periodo: "No hay horarios libres para {duración} esta semana." + Secundario "Ver semana siguiente"; si la otra duración cabe: "Prueba con {otra duración}" (enlace a 01) |
| 02 carga · error | Los del [calendario](../componentes/calendario.md#estados-de-la-media-hora): "Cargando semana…"; aviso Error + "Reintentar" |
| 04 condiciones no cargan | Estado Sin texto del [resumen legal](../componentes/resumen-legal.md#estados): "Agendar asesoría" deshabilitado con "Necesitamos mostrarte las condiciones antes de continuar." |
| 04 casilla sin marcar | "Marca la casilla para aceptar las condiciones; sin ella no podemos agendar tu asesoría." |
| Agendando | Botón en Carga "Agendando…", "Anterior" deshabilitado |
| 409 `horario_no_disponible` | Aviso Error "Alguien agendó ese horario hace un momento. Elige otro; lo demás se conserva." + "Elegir otro horario" (paso 02 sin `inicio`) |
| 409 `duracion_no_ofrecida` | "{Nombre} ya no ofrece asesorías de {duración}. Elige otra." + "Cambiar duración" (paso 01) |
| 409 `reaceptacion_requerida` · `perfil_incompleto` · `autorizacion_menor_pendiente` | Paso 03 con la elección intacta, como en [aceptaciones](RF-17-registro-y-aceptaciones.md#recorrido) (menor: el aviso Crítico de allí, con "agendar" en lugar de "reservar") |
| 409 `texto_desactualizado` | Estado Versión desactualizada del resumen legal; casilla desmarcada |
| 422 `fuera_de_horario` · `anticipacion_insuficiente` · `anticipacion_excesiva` | "Ese horario ya no está publicado." · "Ese horario empieza demasiado pronto para agendarlo." · "Ese horario aún no se puede agendar: está demasiado lejos." + "Elegir otro horario" |
| 422 `datos_invalidos` | "Algo en tu asesoría no es válido. Revisa los pasos." |
| 403 (rol `profesional`) | Aviso Información "Las cuentas de profesional no agendan asesorías. Para agendar como artista, usa otra cuenta." + "Volver al inicio" |
| 401 · 503 · red · no JSON | Los de [reservar](RF-04-reservar.md#estados) con "asesoría" en lugar de "reserva" ("Tu asesoría no se guardó…"; "Revisa en Mis asesorías si se guardó antes de repetir.") |
| Listo sin datos | Aviso Éxito "Asesoría agendada." + "Ver mis asesorías" |
| Sin JS | `<noscript>`: "Para agendar necesitas JavaScript. Actívalo en tu navegador y recarga la página." |

Los errores al confirmar van en un aviso arriba del paso con el foco en él; el paso afectado pasa a REVISAR.

## Copy

| Paso | Título (`<h1>`) | Descripción |
|---|---|---|
| 01 | ELIGE TU ASESORÍA | Cuánto dura y cómo prefieres hacerla. El precio es fijo. |
| 02 | ELIGE TU HORARIO | Elige el día y la hora de inicio. Horario de Lima. |
| 04 | CONFIRMA TU ASESORÍA | Revisa todo antes de agendar. |
| 05 | ASESORÍA AGENDADA | Tu horario queda apartado mientras pagas. |

- Modalidad: Presencial · "En un ambiente del estudio apartado de la sala o en un lugar que acuerden." · Virtual · "Por videollamada de Google Meet."
- R3: presencial "{Nombre} y el estudio te confirmarán el lugar antes de la cita; lo verás en tu asesoría y te llegará por correo." · virtual "El enlace de Google Meet te llega por correo y lo verás en tu asesoría antes de la cita."
- Bajo R2: "Pagas el total en un solo pago para confirmar. Si el plazo vence sin pago, la asesoría se cancela y el horario se libera."
- Listo, siguientes pasos: "1. Paga {total} antes del {vence_pago}. 2. Registra tu comprobante desde tu asesoría. 3. Cuando lo validemos, quedará confirmada y te enviaremos el evento para tu calendario." Debajo: "Te enviamos estos datos a {correo}."

## Accesibilidad

- `<title>` "Elige tu asesoría · Paso 1 de 5 · Agendar asesoría"; al cargar cada paso, foco al `<h1>`. Pasos: `<nav aria-label="Progreso de la asesoría">`.
- DURACIÓN y MODALIDAD son `<fieldset>` con `<legend>`; el precio va en el detalle de la casilla (lo lee el lector con la opción).
- Calendario: teclado y nombres de su [ficha](../componentes/calendario.md#accesibilidad); el estado NO CABE se dice en texto. Región `role="status"` de la isla: "Inicio: martes 18 nov, 10:00 a 11:00. Total S/ 80,00."

## Preguntas

1. El resumen de [Asesoría](../../08-legal/resumenes-para-pantallas.md#asesoría) es distinto del de la reserva de sala, pero `TextoResumen` trae un resumen por tipo, no por contexto. ¿La API sirve el de asesoría (p. ej. `?contexto=asesoria`)? Sin él, R4 muestra el resumen de las condiciones y la casilla de Asesoría.
2. ¿Personal y Administrador que agendan para sí ven sus asesorías? `GET /asesorias/mias` es solo de `cliente` en el contrato.
