---
id: pantalla-rf-04-mis-reservas
titulo: Pantalla — Mis reservas (lista, detalle y cancelar)
estado: borrador
depende_de: [RF-04, RF-05, RF-06, ADR-009, ADR-010, estados-reserva, diseno-brief, patron-estructura-app, patron-tablas-y-tableros, patron-formularios, patron-estados-sistema, comp-tabla, comp-panel, comp-etiqueta-tecnica, comp-indicador-estado, comp-aviso, comp-boton, comp-barra-acciones, comp-campo]
---

# Mis reservas

| Campo | Valor |
|---|---|
| Requerimiento | [RF-04](../../03-requerimientos/RF-04.md): CA-05, CA-07, CA-08 (detalle), CA-10; [RF-05](../../03-requerimientos/RF-05.md): CA-09 (cuotas); [RF-06](../../03-requerimientos/RF-06.md): CA-04, CA-05 |
| Actores | Artista/Cliente (las suyas); Personal y Administrador abren el detalle desde la [agenda](RF-03-calendario.md) |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/reservas?ver=proximas\|historial`, `/app/reservas/detalle?id=`. URL: `ver`, `id`, `aviso` |
| Isla | `<bugalu-reservas vista="lista\|detalle">` |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)) |

## Recorrido

1. El cliente entra por "RESERVAS" (`calendar-check`) o desde "Ver mi reserva" del [paso Listo](RF-04-reservar.md). Ve sus próximas reservas; HISTORIAL muestra las finalizadas y canceladas.
2. Abre una con "Ver reserva {folio}": estado, horario, precio, cuotas y, si está `Pre-reservada`, la fecha límite de pago con lo que falta.
3. Si una cuota es `pagable`, "Registrar pago" lleva a [registrar pago](RF-05-registrar-pago.md); al terminar vuelve con `?aviso=pago-registrado`.
4. Si no pagó nada, "Cancelar reserva" abre la confirmación en el propio detalle; al confirmar, el detalle se recarga con `?aviso=reserva-cancelada`. Con pagos registrados, el lateral le dice que lo pida al estudio. El Administrador cancela también con pagos, con una nota del reembolso.
5. "Reservar sala" abre el [flujo](RF-04-reservar.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Reservas | `GET /reservas/mias` → `[Reserva]` | PRÓXIMAS: `Pre-reservada`, `Confirmada`, `En curso`, por `inicio` ascendente. HISTORIAL: `Finalizada`, `Cancelada`, descendente. Total "3 reservas" |
| Reserva | `GET /reservas/{id}` | — |
| Folio, servicio, sala | `folio`, `servicio`, `sala` | Folio en `fuente-familia-tecnica`; el resto tal cual |
| Horario | `inicio`, `fin` | `D MMM AAAA` + `HH:mm–HH:mm` y [duración](../patrones/estructura-app.md#formato-de-datos) |
| Estado | `estado`, `motivo_cancelacion`, `nota_cancelacion` | [Etiqueta](../componentes/etiqueta-tecnica.md) según [estados de reserva](../../02-dominio/estados-reserva.md): PRE-RESERVADA (Aviso), CONFIRMADA y FINALIZADA (Éxito), EN CURSO (Activa), CANCELADA (Alerta) + motivo en texto; la nota, tal cual |
| Pago por validar | `pago_por_validar` | Etiqueta Aviso PAGO POR VALIDAR junto al estado en D1; en la lista lo dice la columna PAGO |
| Saldo | Cuota `al_terminar` en `pendiente` | Importe ("Resto: S/ 225,00") |
| Tiene pagos | Algún `cuotas[].pagos[]` en `pendiente_validacion` o `aprobado` (lo que cuenta `tiene_pagos`, [ADR-010](../../00-proyecto/decisiones/ADR-010-pagos-estados-y-cancelacion.md)) | Decide qué cancelar se ofrece |
| Fecha límite | `vence_pago` | [Plazo restante](../patrones/estructura-app.md#formato-de-datos) |
| Total | `precio.total` | Importe; columna TOTAL de la lista |
| Precio | `precio` (`Simulacion`) | [Tabla](../componentes/tabla.md) Partidas, igual que en [reservar](RF-04-reservar.md#datos) (mismo formateador de CANTIDAD y pie TOTAL / ANTICIPO 50 %) |
| Cuotas | `cuotas[].{hito, monto, estado, pagable, pagos}` | Tabla Partidas: CUOTA ("Al reservar · 50 %", "Al terminar la sesión · 50 %") · IMPORTE · ESTADO: PENDIENTE (Aviso), EN VALIDACIÓN (Aviso), PAGADA (Éxito). Si el último pago de una cuota `pendiente` está `rechazado`, bajo la cuota: "Pago rechazado el 16 nov: {motivo_rechazo}" (`color-texto-cuerpo`, motivo tal cual) |
| Especialistas | `especialistas[].nombre` | Lista separada por comas |
| Cliente | `cliente` (solo personal y Administrador) | Tal cual |
| Cancelar | `POST /reservas/{id}/cancelar` `{nota?}` → 200 `Reserva` | Nota: [campo](../componentes/campo.md) Área, 1–300 caracteres, solo para el Administrador con pagos |

## Composición

### Lista

[Encabezado](../componentes/encabezado-pantalla.md) App con acción [botón](../componentes/boton.md) Primario "Reservar sala" → [etiquetas](../componentes/etiqueta-tecnica.md) Filtro PRÓXIMAS · HISTORIAL → [panel](../componentes/panel.md) `RESERVAS` + [tabla](../componentes/tabla.md) Directorio: RESERVA (folio y servicio debajo) · FECHA · ESTADO · TOTAL · PAGO (`Pre-reservada`: "Antes del 18 nov, 14:30" y, debajo, el plazo restante; con `pago_por_validar`, "En validación"; con saldo, "Resto: S/ 225,00"; resto en validación, "En validación"; todo pagado, "Pagada"; cancelada, "—"; sin más texto en la celda) · "Ver reserva" con el folio en el nombre accesible (Secundario como enlace). < `punto-quiebre-escritorio`, tarjetas (`<dl>`), como en la ficha de tabla.

### Detalle

- Principal: panel `D1 RESERVA {folio}` (`<dl>`: estado, fecha y horario, servicio, especialistas, sala; cliente para el personal) → panel `D2 PRECIO` (tabla Partidas + "Precio calculado al reservar.") → panel `D3 CUOTAS` (tabla Partidas).
- Lateral: [indicador de estado](../componentes/indicador-estado.md) Barra con lo que toca según el estado (tabla Estados) → "Registrar pago" si hay una cuota `pagable` (la primera por hito) → si se puede cancelar, [botón](../componentes/boton.md) Peligro "Cancelar reserva", que abre la confirmación.
- "Registrar pago" es Primario cuando la cuota toca ya (`al_reservar`; `al_terminar` con la reserva `Finalizada`) y Secundario "Adelantar el pago del resto" cuando es opcional (`al_terminar` en `Confirmada` o `En curso`). Solo para el dueño.
- Cancelar se muestra al dueño solo en `Pre-reservada` **sin pagos**; con pagos, en su lugar, el párrafo "Ya registraste un pago, así que la cancelación la gestiona el estudio. Escríbele y te dirá qué pasa con tu pago." y, debajo, el contacto del estudio (`GET /contacto-estudio`, tal cual; vacío → sin línea). Ni el Administrador ni el dueño sin pagos ven ese párrafo: o hay "Cancelar reserva" o hay párrafo, nunca los dos. Al Administrador, en `Pre-reservada` y `Confirmada`, con o sin pagos. El personal no lo ve.

### Cancelar

**Decisión del brief (TAREA-RF04-6):** confirmación en un paso dentro del detalle, sin página propia ([formularios](../patrones/formularios.md#prevención-de-errores) lo admite). "Cancelar reserva" se sustituye en el lateral por el panel `CANCELAR RESERVA {folio}`: un párrafo con servicio, fecha y horario, otro con las consecuencias, y "Volver a la reserva" (Secundario) + Peligro "Cancelar reserva {folio}". El foco va al título del panel; "Volver a la reserva" cierra el panel y devuelve el foco a "Cancelar reserva". Sin `<dl>`: son dos datos que ya están en D1.

**Administrador con pagos** (RF-06 CA-04): el mismo panel suma, antes de los botones, NOTA SOBRE EL REEMBOLSO (Área, obligatoria, `maxlength="300"`) y cambia las consecuencias (Copy). La nota se valida antes de enviar; 422 `nota_requerida` pinta el mismo error bajo el campo.

Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md), [estados del sistema](../patrones/estados-sistema.md). Adaptabilidad: < `punto-quiebre-escritorio`, el lateral (lo que toca y cancelar) va **antes** del principal, bajo el encabezado: es lo que el cliente viene a ver. El folio del título no se parte (`white-space: nowrap` en el folio).

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lista | Sin reservas | Vacío: "Aún no tienes reservas" + "Elige un horario libre y reserva la sala en unos pasos." + Primario "Reservar sala" (sin filtros ni acción en el encabezado) |
| Lista | Filtro sin resultados | "No tienes reservas próximas." / "Aún no hay reservas en tu historial." + "Ver historial" / "Ver próximas" (Secundario, el otro filtro) |
| Lista, detalle | Carga | Panel con "Cargando…", `aria-busy` |
| Detalle | `Pre-reservada` | Barra Pendiente "PAGA EL ANTICIPO ANTES DEL 18 NOV, 14:30" + dato "faltan 2 d 3 h". Con menos de 1 h, además [aviso](../componentes/aviso.md) Aviso "Tu reserva vence en 45 min. Si no registras el pago, se cancelará y el horario se liberará." |
| Detalle | `Pre-reservada` con `pago_por_validar` | Barra Pendiente "PAGO EN VALIDACIÓN" + "Registraste tu pago. No caduca mientras el estudio lo revisa; te avisaremos por correo." Sin plazo ni aviso de vencimiento (RN-18). Igual si ya llegó el inicio: sigue `Pre-reservada` (RN-23) |
| Detalle | `Pre-reservada` con `vence_pago` pasado y sin `pago_por_validar` | Se muestra como caducada (la disponibilidad ya la trata como libre): Barra Problema "CADUCADA" + "Venció sin pago el 18 nov, 14:30. El horario quedó libre." Sin cancelar |
| Detalle | `Confirmada` / `En curso` | Barra Correcto "CONFIRMADA · Pagas el resto al terminar la sesión." / Neutro "EN CURSO · Pagas el resto al terminar." Con el resto pagado o en validación: "CONFIRMADA · Pagada" / "· Pago del resto en validación" |
| Detalle | `Finalizada` | Con saldo: Barra Pendiente "FALTA PAGAR EL RESTO: S/ 225,00" + Primario "Registrar pago". Resto en validación: Pendiente "PAGO DEL RESTO EN VALIDACIÓN". Todo pagado: Correcto "FINALIZADA · Pagada" |
| Detalle | `Cancelada` | Barra Neutro "CANCELADA" + motivo: caducada "Caducó sin pago el {vence_pago}. El horario se liberó." · cliente "La cancelaste." · administrador "La canceló el estudio." Con `nota_cancelacion`, debajo: "Nota del estudio:" + la nota tal cual (también la ve el Administrador) |
| Detalle | `?aviso=reserva-cancelada` | Aviso Éxito: dueño "Reserva cancelada. El horario quedó libre y no se te cobró nada." · Administrador "Reserva cancelada. El horario quedó libre y avisamos al cliente por correo." |
| Detalle | `?aviso=pago-registrado` | Aviso Éxito "Pago registrado. Queda pendiente de validación." + "Te avisaremos por correo cuando el estudio lo revise." ([registrar pago](RF-05-registrar-pago.md)) |
| Cancelar | Enviando | Botón en Carga "Cancelando…"; "Volver a la reserva" deshabilitado |
| Cancelar | 409 `tiene_pagos` (pago registrado desde otra pestaña) | El panel se cierra, el detalle se recarga y queda el párrafo de "pídelo al estudio"; aviso Información "Ya registraste un pago para esta reserva. La cancelación la gestiona el estudio: escríbele." |
| Cancelar | 409 `no_cancelable` | Igual, con aviso Información "Esta reserva ya no se puede cancelar: está {estado}." y el detalle recargado |
| Cancelar | 422 `nota_requerida` · `datos_invalidos` | Bajo NOTA SOBRE EL REEMBOLSO: "Escribe qué pasa con el pago: cómo se devuelve o por qué no." · "La nota admite hasta 300 caracteres." |
| Todas | 401 | Aviso "Tu sesión no es válida. Inicia sesión para ver tus reservas." + "Ir al acceso" (`?volver=` con la vista) |
| Detalle, cancelar | 403 / 404 | En lugar del bloque: `[403] SIN PERMISO` "Esta reserva no es tuya." / `[404] RESERVA NO ENCONTRADA` "No encontramos esta reserva." + "Volver a mis reservas" |
| Todas | 503 · red caída · no JSON | Aviso Error "El servicio no responde. Inténtalo de nuevo en unos minutos." · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal. Inténtalo de nuevo." Al cargar, con "Reintentar"; al cancelar, sin él (el botón sigue disponible) |
| Todas | Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Claves `aviso` (lista cerrada): `reserva-cancelada`, `pago-registrado`. Permisos: el cliente solo ve las suyas; la API es la barrera (403).

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Lista | Inicio / Reservas · `[P2] SALA / RESERVAS` | MIS RESERVAS | Tus horarios en la sala, su estado y lo que falta pagar. |
| Detalle | Inicio / Reservas / {folio} (personal: Inicio / Agenda / {folio}) | RESERVA {folio} | {servicio} · {fecha}, {HH:mm}–{HH:mm} |
Consecuencias del Administrador con pagos: "El horario se libera al momento. La app no devuelve dinero: gestiona el reembolso por tu cuenta y explícalo en la nota. El cliente la verá en su reserva y en el correo." Ayuda de la nota: "Por ejemplo: «Devolvemos S/ 225,00 por Yape en 48 h» o «Sin devolución: cancelación fuera de plazo»." Consecuencias del cliente (RN-20), en el panel de cancelar: "El horario se libera al momento y no se te cobra nada. No se puede deshacer: si quieres ese horario otra vez, tendrás que reservarlo de nuevo si sigue libre." Columnas: RESERVA · FECHA · ESTADO · TOTAL · PAGO.

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`. Tablas con `<caption>` y folio o cuota como `<th scope="row">`.
- Filtros: enlaces con `aria-current="true"` en el aplicado. El plazo restante se recalcula cada minuto sin región viva; el aviso de menos de 1 h aparece al cargar y no se anuncia solo.
- Región `role="status"` estable de la isla: anuncia la carga ("3 reservas próximas") y el resultado; al fallar la cancelación, el foco va al aviso.

## Pendientes

- **dev-backend:** qué pasa con un pago en validación de una reserva que el Administrador cancela (propuesta: queda en la lista de pagos y se puede rechazar con motivo "reserva cancelada"; aprobarlo no reabre la reserva).
