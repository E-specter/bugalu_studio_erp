---
id: pantalla-rf-18-reprogramar
titulo: Pantalla — Reprogramar una reserva y elegir tras una cancelación del estudio
estado: aprobado
depende_de: [RF-18, ADR-015, pantalla-rf-18-cancelar, pantalla-rf-04-mis-reservas, pantalla-rf-04-reservar, pantalla-rf-03-calendario, diseno-brief, patron-formularios, patron-estados-sistema, comp-calendario, comp-panel, comp-tabla, comp-resumen-persistente, comp-barra-acciones, comp-aviso, comp-boton, comp-indicador-estado]
---

# Reprogramar

| Campo | Valor |
|---|---|
| Requerimiento | [RF-18](../../03-requerimientos/RF-18.md): CA-08, CA-09, CA-10, CA-13 (elección), CA-16 |
| Actores | Artista/Cliente (dueño); Administrador solo tras una cancelación del estudio, en nombre del cliente |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/reservas/reprogramar?id=` (URL: `id`, `fecha` y `vista` del calendario, `inicio` elegido). RESERVAS sigue como destino actual |
| Isla | `<bugalu-reservas vista="reprogramar">` (vista nueva) con [`<bugalu-calendario modo="reserva">`](../componentes/calendario.md) dentro |

**Decisión del brief: ruta propia**, como [registrar pago](RF-05-registrar-pago.md): el calendario no cabe en el lateral del detalle y la URL conserva la semana y el inicio si el móvil recarga.

## Entrada desde el detalle

En el lateral del [detalle](RF-18-cancelar.md#composición), solo para el dueño de una `Confirmada` con inicio futuro, con la `VistaCancelacion` pedida al cargar:

| Situación | Lateral |
|---|---|
| `puede_reprogramar` | Secundario "Reprogramar" + ayuda "Te quedan {reprogramaciones_restantes} cambios de horario." En nivel 2, además: "Faltan {h1} h o menos: reprogramar tiene una penalización del {p} %." |
| No puede, nivel 3 | Sin botón. Párrafo: "Ya no puedes reprogramarla: faltan {h2} h o menos para el inicio." |
| No puede, `reprogramaciones_restantes` = 0 | "Ya no puedes reprogramarla: usaste los cambios de horario que permite una reserva." |
| No puede, nivel 2 con restantes > 0 | "Ya la reprogramaste una vez con poco tiempo de aviso, que es el máximo en el nivel 2." |
| `Pre-reservada` | "Podrás reprogramarla cuando esté confirmada." |
| La vista previa falla | Se muestra "Reprogramar": la barrera es la API |

## Recorrido

1. Llega desde "Reprogramar" del detalle o desde "Reprogramar sin costo" (elección tras la cancelación del estudio).
2. Ve la semana de la reserva en el calendario de **su** sala, con su horario actual como TU RESERVA, y un resumen de la reserva actual.
3. Elige un inicio libre: el calendario marca el tramo con la duración de su reserva (no se elige duración) y la isla pide la simulación.
4. Lee cómo queda (nivel, penalización, nuevo precio, saldo y crédito) y pulsa "Confirmar reprogramación", o "Volver a la reserva".
5. Vuelve al detalle con `?aviso=reserva-reprogramada`; D5 muestra el cambio.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Reserva actual | `GET /reservas/{id}` → `folio`, `sala`, `servicio`, `especialistas`, `inicio`, `fin`, `precio.total`, `pagado`, `eleccion_estudio` | Como en [mis reservas](RF-04-mis-reservas.md#datos); duración como [duración de reserva](../patrones/estructura-app.md#formato-de-datos) |
| Calendario | `<bugalu-calendario modo="reserva" sala="{sala}" duracion="{minutos}">` | Evento `calendario-inicio` → `inicio`, `minutosMaximos` |
| Vista previa | `POST /reservas/{id}/reprogramar/simular {inicio}` → `VistaReprogramacion` | Se pide al elegir, si `minutosMaximos` ≥ la duración |
| Nivel | `nivel` (1, 2 o `null` sin costo) | "Nivel 1 · sin cargo" · "Nivel 2 · con penalización" · "Sin costo: el estudio canceló tu sesión" |
| Nuevo precio | `precio` (`Simulacion`) | [Tabla](../componentes/tabla.md) Partidas con el formateador de [reservar](RF-04-reservar.md#datos), con IGV |
| Saldo y crédito | `penalizacion`, `saldo`, `credito`, más `Reserva.pagado` | Tabla Partidas: NUEVO TOTAL · PENALIZACIÓN (si > 0) · YA PAGASTE (en negativo, "− S/ 100,00") · pie SALDO POR PAGAR; si `credito` > 0, fila "PASA A CRÉDITO" bajo el pie. El navegador no suma: cada cifra viene de la API |
| Restantes | `reprogramaciones_restantes` | "Después de este cambio te quedarán {n}." (ver Preguntas) |
| Confirmar | `POST /reservas/{id}/reprogramar {inicio, nivel_esperado, total_esperado}` → 200 `Reserva` | `nivel_esperado` = `nivel` (`null` sin costo); `total_esperado` = `precio.total` |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, título y descripción (Copy); sin acción |
| Avisos | [aviso](../componentes/aviso.md) | Sin costo: Información fija "Sin costo: el estudio canceló tu sesión. Mantienes el precio y lo que pagaste." Errores y 409 |
| Principal | panel `R1 ELIGE EL NUEVO HORARIO` + [calendario](../componentes/calendario.md) Reserva | La sala va fija (sin selector). Bajo el calendario: "Tu sesión dura {duración}: elige dónde empieza." |
| Principal | panel `R2 CÓMO QUEDA` (tras elegir) | `<p>` NUEVO HORARIO: "mar 25 nov, 10:00–12:00" y el nivel en palabras → tabla NUEVO PRECIO → tabla SALDO → [aviso](../componentes/aviso.md) Información "El precio se recalcula con las tarifas vigentes del nuevo horario. Si sube, la diferencia va a tu saldo; si baja, lo pagado de más pasa a crédito, sin devolución." (sin costo: no se pinta) |
| Lateral | [resumen persistente](../componentes/resumen-persistente.md) Ficha `RESERVA ACTUAL` | `<dl>`: FOLIO, FECHA Y HORARIO actuales, SERVICIO, ESPECIALISTAS, TOTAL, PAGADO |
| Pie | [barra de acciones](../componentes/barra-acciones.md) Formulario | "Volver a la reserva" (Secundario, enlace) + Primario "Confirmar reprogramación" (deshabilitado con `aria-disabled` y ayuda "Elige un horario para ver cómo queda." hasta tener vista previa) |

Patrones: [formularios](../patrones/formularios.md#prevención-de-errores) (R2 es la confirmación), [estados del sistema](../patrones/estados-sistema.md). Adaptabilidad: < `punto-quiebre-escritorio`, el lateral va después de R2 y la barra pasa a Móvil; el calendario usa su lista de días.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Todo | Carga | Paneles con "Cargando…", `aria-busy` |
| R1 | Inicio donde no cabe la sesión | Bajo el calendario, error: "Tu sesión dura {duración} y desde las {HH:mm} solo caben {minutosMaximos}. Elige otro inicio." Sin simulación |
| R1 | Elige su propio horario actual | "Ese es tu horario actual. Elige otro." |
| R2 | Simulando | "Calculando cómo queda…", `aria-busy`; el Primario sigue bloqueado |
| R2 | 409 `tramo_no_disponible` | Aviso Error "Alguien reservó ese horario hace un momento. Elige otro." Se quita la elección y se recarga la semana; foco al título de R1 |
| R2 | 422 `fuera_de_franja` · `anticipacion_insuficiente` · `anticipacion_excesiva` | Textos de [reservar](RF-04-reservar.md#estados) bajo el calendario, sin vista previa |
| Todo | 409 `reprogramacion_no_permitida` · `limite_reprogramaciones` (al simular o confirmar) | Sin calendario: aviso Información "Ya no puedes reprogramar esta reserva: faltan {h2} h o menos para el inicio." / "… ya usaste los cambios de horario que permite." + "Volver a la reserva" |
| Envío | Enviando | Primario en Carga "Reprogramando…"; "Volver a la reserva" y el calendario deshabilitados |
| Envío | 409 `nivel_cambiado` · `precio_cambiado` | R2 se repinta con `detalles` y aviso Aviso arriba de R2: "Mientras revisabas pasó un plazo: ahora es nivel 2, con penalización. Revisa cómo queda y confirma de nuevo." / "El precio de ese horario cambió mientras revisabas. Revisa el nuevo total y confirma de nuevo." Foco al aviso |
| Envío | 503 · red · no JSON | Textos de [registrar pago](RF-05-registrar-pago.md#estados) ("No pudimos reprogramar…; tu elección sigue aquí…"), sin "Reintentar" |
| Todo | 401 · 403 · 404 · sin JS | Como en [mis reservas](RF-04-mis-reservas.md#estados) |
| Éxito | 200 | Redirige a `/app/reservas/detalle?id=&aviso=reserva-reprogramada`: Éxito "Reserva reprogramada al {D MMM, HH:mm}. Te enviamos el correo con el nuevo horario para tu calendario." + con `credito` "{credito} pasaron a crédito." |

Permisos: dueño; el Administrador solo con `eleccion_estudio = pendiente` (si no, 403 de la API).

## Elección tras una cancelación del estudio

Detalle de una `Cancelada` con `eleccion_estudio = pendiente`, para el dueño y para el Administrador ("Elegir por el cliente"):

| Región | Contenido |
|---|---|
| Lateral | Barra Pendiente "EL ESTUDIO CANCELÓ TU SESIÓN · ELIGE QUÉ HACER" + nota del estudio. Debajo, dos opciones con el mismo peso, cada una [botón](../componentes/boton.md) Secundario con su párrafo: "Reprogramar sin costo" (enlace a esta ruta) · "Eliges otro horario libre de la misma sala. Mantienes el precio y lo que pagaste." y "Pedir la devolución íntegra" · "Te devolvemos {pagado} por el mismo medio, en un máximo de 7 días hábiles." Al pie: "Mientras no elijas, nada vence." Sin Primario: ninguna opción se empuja |
| Lateral (al pedir devolución) | Panel `DEVOLUCIÓN ÍNTEGRA · {folio}`: "Te devolvemos {pagado} por el mismo medio con que pagaste, en un máximo de 7 días hábiles. Después ya no podrás reprogramar esta reserva." → barra Móvil "Volver" + Primario "Confirmar devolución" → `POST /reservas/{id}/eleccion-estudio {opcion: "devolucion"}` |
| Tras elegir | `devolucion`: Barra Neutro "CANCELADA POR EL ESTUDIO · DEVOLUCIÓN ÍNTEGRA" + "Te devolvemos {pagado} en un máximo de 7 días hábiles. Te avisaremos por correo cuando esté hecha." Con `?aviso=devolucion-elegida`: Éxito "Elegiste la devolución íntegra. Avisamos al estudio." `reprogramada`: la reserva vuelve a su estado con el nuevo horario |
| 409 `eleccion_no_disponible` | Aviso Información "Ya se eligió qué hacer con esta reserva, quizá desde otra sesión." y el detalle se recarga |

Claves `aviso` nuevas (lista cerrada de [mis reservas](RF-04-mis-reservas.md#estados)): `reserva-reprogramada`, `devolucion-elegida`.

## Copy

| Elemento | Texto |
|---|---|
| Ruta · título | Inicio / Reservas / {folio} / Reprogramar · REPROGRAMAR RESERVA {folio} (sin costo: ELIGE TU NUEVO HORARIO) |
| Descripción | "Misma sala, servicio, duración y especialistas. Antes de confirmar verás cómo cambian el precio y tu saldo." |
| Tablas | NUEVO PRECIO (CONCEPTO · CANTIDAD · IMPORTE) · SALDO (CONCEPTO · IMPORTE): "Nuevo total" · "Penalización (nivel 2, {p} %)" · "Ya pagaste" · SALDO POR PAGAR ("Nada por pagar" si 0) · PASA A CRÉDITO |
| Acciones | "Confirmar reprogramación" · "Volver a la reserva" · "Reprogramar sin costo" · "Pedir la devolución íntegra" · "Confirmar devolución" |

## Accesibilidad

- `<h1>` del encabezado; R1 y R2 `<section>` con `<h2>`; el lateral `<aside aria-labelledby>`. Teclado y nombres del calendario: los de su [ficha](../componentes/calendario.md#accesibilidad).
- Al elegir inicio, el foco se queda en el calendario; la región `role="status"` anuncia "Nuevo horario mar 25 nov, 10:00 a 12:00: nivel 1, saldo S/ 0,00, pasan S/ 20,00 a crédito." Los 409 llevan el foco al aviso.
- Las dos opciones de la elección son botones del mismo tamaño, en el orden del texto legal.

## Preguntas para leader

1. `reprogramaciones_restantes`: ¿cuenta las que quedan **antes** o **después** de este cambio, y en el nivel actual o en total? El copy asume "en total, antes del cambio" en el detalle y resta 1 en R2.
2. `GET /disponibilidad` marca el horario actual como ocupado (`propia`): mover la sesión 30 min no se puede ofrecer. ¿Debe el backend excluir la propia reserva al reprogramar?
3. Tras elegir la devolución íntegra, el cliente no puede consultar su estado (`GET /devoluciones` es del Administrador y `Reserva` no la trae). Propuesta: `Reserva.devolucion?: {estado, monto_aprobado, limite, realizada_en}`.
