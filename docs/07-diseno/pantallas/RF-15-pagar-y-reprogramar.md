---
id: pantalla-rf-15-pagar-y-reprogramar
titulo: Pantalla — Pagar y reprogramar una asesoría (cliente, etapa B)
estado: borrador
depende_de: [RF-15, RF-05, RF-18, ADR-015, pantalla-rf-05-registrar-pago, pantalla-rf-18-creditos, pantalla-rf-18-reprogramar, pantalla-rf-15-mis-asesorias, diseno-brief, patron-formularios, patron-estados-sistema, comp-calendario, comp-panel, comp-tabla, comp-resumen-persistente, comp-barra-acciones, comp-aviso]
---

# Pagar y reprogramar una asesoría

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-08 (pago y crédito), CA-10 b (reprogramar), CA-11 (reprogramar sin costo), CA-17 |
| Actores | Artista/Cliente, dueño. El Administrador reprograma solo tras una cancelación del estudio, como en [RF-18](RF-18-reprogramar.md) |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/asesorias/pagar?id=&cuota=` · `/app/asesorias/reprogramar?id=` (URL: `fecha`, `vista`, `inicio`) |
| Isla | `<bugalu-pago tipo="asesoria">` (existente, atributo nuevo) · `<bugalu-asesorias vista="reprogramar">` con `<bugalu-calendario modo="asesoria" duracion excluir>` |

**Decisión del brief:** las dos pantallas son las de sala ([registrar pago](RF-05-registrar-pago.md), [pago con crédito](RF-18-creditos.md#pago-con-crédito), [reprogramar](RF-18-reprogramar.md)) con otra fuente de datos y otro objeto. Aquí solo van las diferencias. `POST /pagos` y `POST /cuotas/{id}/credito` no cambian (contrato de RF-15).

## Pagar

| Qué cambia | En la asesoría |
|---|---|
| Fuente | `GET /asesorias/{id}` en lugar de `GET /reservas/{id}`; la cuota sale de `Asesoria.cuotas[]` |
| Lateral `CUOTA A PAGAR` | `<dl>`: ASESORÍA (folio) · PROFESIONAL · FECHA · DURACIÓN · CUOTA ("Pago único" o "Penalización por reprogramar · {p} %") · si `Pendiente de pago`, PAGA ANTES DE; al pie IMPORTE DE LA CUOTA con "Incluye IGV" ([desglose](RF-20-cambios-sensibles.md#desglose-de-igv)) |
| P0 CRÉDITO | Igual; el crédito sirve en sala o asesoría (CA-10). Ayuda del panel `CÓMO FUNCIONA` de créditos: "Úsalo en tus reservas o asesorías." |
| Resumen legal | El de [registro de un pago](../../08-legal/resumenes-para-pantallas.md#registro-de-un-pago), sin cambios |
| Volver y éxito | "Volver a la asesoría" → `/app/asesorias/detalle?id=`; éxito con `?aviso=pago-registrado` o `pagado-con-credito` ("Pagaste con tu crédito. Tu asesoría quedó confirmada.") |
| Ruta del encabezado | Inicio / Asesorías / {folio} / Pagar |
| Cuota no pagable | Los avisos de RF-05 con "asesoría": "Esta asesoría está cancelada: ya no admite pagos." |
| 403 | Rol `profesional` (no paga, CA-01): `[403] SIN PERMISO` "Las cuentas de profesional no registran pagos." |

Estados, validación, errores de envío, accesibilidad y copy restantes: los de [registrar pago](RF-05-registrar-pago.md#estados) sin cambios.

## Reprogramar

Mismo profesional, misma duración, dentro de sus horarios, **conservando el precio** (CA-10 b, decisión 3). La penalización de nivel 2 no se retiene de lo pagado: nace una cuota `al_terminar` del {p} %, pagable hasta 48 h después del fin (decisión 4).

### Entrada desde el detalle

Las reglas de [reprogramar](RF-18-reprogramar.md#entrada-desde-el-detalle), con estos textos:

| Situación | Lateral |
|---|---|
| `puede_reprogramar`, nivel 1 | Secundario "Reprogramar" + "Te quedan {n} cambios de horario. Mantienes el precio." |
| `puede_reprogramar`, nivel 2 | Lo mismo + "Faltan {h1} h o menos: reprogramar suma un pago del {p} % del precio." |
| Ya empezó | Sin botón ni párrafo (CA-10 c: hasta el inicio) |
| Resto | Los textos de RF-18, con "asesoría" en lugar de "reserva" |

### Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Copy |
| Principal | [panel](../componentes/panel.md) `R1 ELIGE EL NUEVO HORARIO` + [calendario](../componentes/calendario.md#modos) Asesoría con `duracion` y `excluir` | El profesional va fijo; su asesoría actual se ve como TU ASESORÍA. Bajo el calendario: "Tu asesoría dura {duración}: elige dónde empieza." |
| Principal | panel `R2 CÓMO QUEDA` (tras elegir) | NUEVO HORARIO y el nivel en palabras (los de RF-18) → [tabla](../componentes/tabla.md) Partidas SALDO: "Precio de la asesoría (se conserva)" · "Ya pagaste" (− importe) · "Penalización (nivel 2, {p} %)" si > 0 · pie PAGO NUEVO ("Nada por pagar" si 0). Con penalización, debajo: "Se crea un pago de {penalizacion} que haces hasta 48 h después de tu asesoría." Sin NUEVO PRECIO ni aviso de tarifas |
| Lateral | [resumen persistente](../componentes/resumen-persistente.md) Ficha `ASESORÍA ACTUAL` | FOLIO · PROFESIONAL · FECHA Y HORARIO · DURACIÓN · MODALIDAD · TOTAL · PAGADO |
| Pie | [barra de acciones](../componentes/barra-acciones.md) Formulario | "Volver a la asesoría" + Primario "Confirmar reprogramación" (bloqueado hasta tener vista previa, como en RF-18) |

Datos: disponibilidad con `excluir_asesoria={id}` (como `excluir_reserva`, [precisión 10 de RF-18](../../03-requerimientos/RF-18.md#precisiones-de-contrato-leader-tras-las-specs-de-pantalla-2026-11-17)); simulación y confirmación con `POST /reservas/{id}/reprogramar/simular` y `…/reprogramar {inicio, nivel_esperado, total_esperado}`. El lugar o enlace se conserva; si cambia, lo avisa el profesional ([gestión](RF-15-gestion.md#lugar-o-enlace)). Adaptabilidad: la de [reprogramar](RF-18-reprogramar.md#composición).

### Estados

| Situación | Forma y texto |
|---|---|
| 409 `horario_no_disponible` | Aviso Error "Alguien agendó ese horario hace un momento. Elige otro." Se quita la elección y se recarga la semana |
| 422 `fuera_de_horario` · `anticipacion_insuficiente` · `anticipacion_excesiva` | Los de [agendar](RF-15-agendar.md#estados), bajo el calendario |
| 409 `no_cancelable` | Sin calendario: aviso Información "Tu asesoría ya empezó: ya no se puede reprogramar." + "Volver a la asesoría" |
| 409 `reprogramacion_no_permitida` · `limite_reprogramaciones` · `nivel_cambiado` · 503 · red · no JSON · 401 · 404 | Los de [reprogramar](RF-18-reprogramar.md#estados) con "asesoría"; `precio_cambiado` no aplica (el precio se conserva) |
| Sin costo (cancelación del estudio) | Aviso Información fijo "Sin costo: el estudio canceló tu asesoría. Mantienes el precio y lo que pagaste." |
| Éxito | `/app/asesorias/detalle?id=&aviso=asesoria-reprogramada`: "Asesoría reprogramada al {D MMM, HH:mm}. Te enviamos el correo con el nuevo horario para tu calendario." Con penalización, además: "Tienes un pago de {penalizacion} pendiente." |

### Copy

| Elemento | Texto |
|---|---|
| Ruta · título | Inicio / Asesorías / {folio} / Reprogramar · REPROGRAMAR ASESORÍA {folio} (sin costo: ELIGE TU NUEVO HORARIO) |
| Descripción | "Mismo profesional y misma duración. Mantienes el precio; antes de confirmar verás si hay algo que pagar." |

### Accesibilidad

Las de [reprogramar](RF-18-reprogramar.md#accesibilidad). Anuncio al elegir: "Nuevo horario martes 25 nov, 10:00 a 11:00: nivel 1, nada por pagar."

## Preguntas

1. ¿`GET /reservas/{id}` acepta el `id` de una asesoría? Si sí, `<bugalu-pago>` no necesita `tipo`; la spec asume que no y lee `GET /asesorias/{id}`.
2. ¿Qué pasa si la cuota de penalización no se paga en las 48 h? (La sala tiene su saldo; aquí no hay regla.) Sin respuesta, R2 dice solo el plazo.
3. ¿`VistaReprogramacion.precio` de una asesoría es la `Simulacion` guardada? R2 no lo muestra como tabla; si no viene, basta `Asesoria.total`.
