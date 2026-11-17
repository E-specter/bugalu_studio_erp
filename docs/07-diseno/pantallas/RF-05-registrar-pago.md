---
id: pantalla-rf-05-registrar-pago
titulo: Pantalla — Registrar pago de una cuota (cliente)
estado: borrador
depende_de: [RF-05, ADR-010, RN-04, RN-18, RN-22, estados-reserva, diseno-brief, patron-estructura-app, patron-formularios, patron-estados-sistema, comp-panel, comp-campo, comp-casilla, comp-carga-archivos, comp-archivo, comp-barra-acciones, comp-resumen-persistente, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Registrar pago

| Campo | Valor |
|---|---|
| Requerimiento | [RF-05](../../03-requerimientos/RF-05.md): CA-01, CA-02, CA-03, CA-04, CA-08 (lado cliente), CA-09 |
| Actores | Artista/Cliente, dueño de la reserva |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/reservas/pagar?id={reserva}&cuota={cuota}`. URL: `id`, `cuota` (no hay lectura de una cuota suelta: sale de `Reserva.cuotas[]`) |
| Isla | `<bugalu-pago>` (nueva) con [`<bugalu-carga-archivos variante="captura">`](../componentes/carga-archivos.md) dentro |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)) |

**Decisión del brief: ruta propia, no panel en el detalle.** Cancelar vive en el detalle porque confirma datos que ya están a la vista (dos párrafos y un botón). Registrar un pago pide datos nuevos y un archivo de hasta 5 MB, y en medio el cliente sale a pagar en la app de su banco, Yape o Plin: una página propia sobrevive a ese cambio de app (si el móvil la recarga, la URL conserva reserva y cuota), deja sitio a los datos para pagar y sigue el [formulario](../patrones/formularios.md) completo. RESERVAS sigue como destino actual (subruta).

## Recorrido

1. El cliente abre su reserva en [mis reservas](RF-04-mis-reservas.md#detalle) y pulsa "Registrar pago" (solo si la cuota es `pagable`).
2. Ve qué paga (reserva, cuota e importe) y elige un método activo; debajo aparecen sus datos para pagar.
3. Paga fuera de la app y vuelve con el voucher o la captura.
4. Revisa el monto (viene con el de la cuota), escribe el número de operación, adjunta la captura y pulsa "Registrar pago".
5. Vuelve al detalle con `?aviso=pago-registrado`; la cuota queda EN VALIDACIÓN y la reserva deja de caducar (RN-18).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Reserva | `GET /reservas/{id}` → `folio`, `servicio.nombre`, `inicio`, `fin`, `estado`, `vence_pago` | Folio en `fuente-familia-tecnica`; `D MMM AAAA` + `HH:mm–HH:mm`; plazo restante si `Pre-reservada` ([formato](../patrones/estructura-app.md#formato-de-datos)) |
| Cuota | `cuotas[]` con `id = cuota` → `hito`, `monto`, `estado`, `pagable`, `pagos[]` | "Al reservar · 50 %" / "Al terminar la sesión · 50 %" (como en mis reservas); importe `S/ 225,00` |
| Último rechazo | Último de `pagos[]` si es `rechazado` y la cuota sigue `pendiente` | `D MMM, HH:mm` + `motivo_rechazo` tal cual |
| Métodos | `GET /instrucciones-pago` → `[InstruccionPago]` (al cliente solo llegan los activos) | Orden fijo: Transferencia bancaria · Yape · Plin · Tarjeta |
| Datos para pagar | `InstruccionPago.texto` del método elegido | Tal cual, saltos de línea respetados (`white-space: pre-line`), `color-texto-principal` (son datos) |
| Monto pagado | Campo; prellenado con `cuota.monto` | [Campo](../componentes/campo.md) importe ("225,00"); se envía `"225.00"`; > 0 y dos decimales |
| Número de operación | Campo | Texto, `autocomplete="off"`, `spellcheck="false"`, `fuente-familia-tecnica`; de 4 a 40 letras, cifras o guiones ([RF-05](../../03-requerimientos/RF-05.md)) |
| Captura | Archivo | JPG, PNG o PDF, ≤ 5 MB; imagen → miniatura; PDF → nombre ([archivo](../componentes/archivo.md) Adjunto) |
| Envío | `POST /pagos` `multipart/form-data`: `id_cuota`, `metodo`, `monto`, `numero_operacion`, `captura` → 201 `Pago` | — |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) (App) | Ruta, título y descripción (Copy); sin acción |
| Avisos | [aviso](../componentes/aviso.md) | Resumen de errores y errores de envío |
| Lateral | [panel](../componentes/panel.md) Lateral `CUOTA A PAGAR`, compuesto como [resumen persistente](../componentes/resumen-persistente.md) Ficha | [Etiqueta](../componentes/etiqueta-tecnica.md) Aviso PENDIENTE → `<dl>`: RESERVA (folio), SERVICIO, FECHA, CUOTA, y si `Pre-reservada` PAGA ANTES DE ("18 nov, 14:30 · faltan 2 d 3 h") → total al pie IMPORTE DE LA CUOTA. Si hubo rechazo, debajo, aviso Aviso "Rechazamos tu pago del 16 nov, 10:20: «{motivo}». Corrígelo y regístralo de nuevo." |
| Principal | `<form>` · panel `P1 MÉTODO DE PAGO` | `<fieldset>` MÉTODO DE PAGO con [casillas](../componentes/casilla.md) Radio (solo los activos; Tarjeta con detalle "En el POS del estudio o con el enlace del banco"). Debajo, `<h3>` DATOS PARA PAGAR CON {MÉTODO} + texto. Sin método elegido: "Elige un método para ver los datos." (`color-texto-secundario`). Con un solo método activo, viene marcado |
| Principal | panel `P2 COMPROBANTE` | MONTO PAGADO (S/) y NÚMERO DE OPERACIÓN en fila (hermanos; una columna < `punto-quiebre-tableta`, [formularios](../patrones/formularios.md) regla 2; ayudas de una línea para que las dos entradas queden alineadas) → [carga de archivos](../componentes/carga-archivos.md) Captura de pago, CAPTURA DEL COMPROBANTE |
| Pie del formulario | [barra de acciones](../componentes/barra-acciones.md) Formulario | "Volver a la reserva" (Secundario, enlace al detalle) + Primario "Registrar pago" |

Patrones: [formularios](../patrones/formularios.md), [estados del sistema](../patrones/estados-sistema.md). Adaptabilidad: < `punto-quiebre-escritorio`, el lateral va **antes** del principal (qué pagas y cuánto, igual que en el detalle) y la barra pasa a su variante Móvil.

**Monto distinto:** al salir del campo, si no coincide con la cuota, la ayuda cambia a "No coincide con la cuota (S/ 225,00). Puedes registrarlo igual: el estudio lo revisará." No es error (`aria-invalid` no cambia): RN-04 admite pagar otro monto.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Todo | Carga | Paneles con "Cargando…", `aria-busy`; se piden reserva e instrucciones a la vez |
| Todo | `cuota` no está en la reserva / falta `id` o `cuota` | En lugar del bloque: `[404] CUOTA NO ENCONTRADA` "No encontramos esta cuota en tu reserva." + "Volver a mis reservas" |
| Todo | Cuota no pagable al cargar | Sin formulario; aviso Información + "Volver a la reserva": `pagada` "Esta cuota ya está pagada." · `en_validacion` "Ya registraste un pago para esta cuota. Te avisaremos por correo cuando el estudio lo revise." · reserva `Cancelada` "Esta reserva está cancelada: ya no admite pagos." · `al_terminar` sin confirmar "El resto se paga cuando tu reserva esté confirmada." |
| P1 | Sin métodos activos (`[]`) | Vacío: "Por ahora no hay métodos de pago disponibles" + "Escríbele al estudio para pagar esta cuota." + el contacto del estudio (`GET /contacto-estudio`, tal cual; vacío → sin línea) + "Volver a la reserva" (Secundario). Sin formulario |
| Todo | Error al cargar (503, red, no JSON) | Aviso Error con los textos de [mis reservas](RF-04-mis-reservas.md#estados) + "Reintentar" (foco al título del primer panel) |
| Todo | 401 / 403 / sin JS | Como en [mis reservas](RF-04-mis-reservas.md#estados) (`?volver=` con la URL actual; 403 "Esta reserva no es tuya.") |
| Envío | Validación local | Bajo cada campo y aviso Error resumen arriba con enlaces ("Revisa 2 campos"); foco al aviso. Textos en Copy |
| Envío | Enviando | Primario en Carga "Registrando pago…"; "Volver a la reserva", los campos y "Quitar" de la captura deshabilitados. A los 10 s, bajo la barra: "Subiendo la captura. Con conexión lenta puede tardar un poco." |
| Envío | 409 `operacion_duplicada` | Error bajo NÚMERO DE OPERACIÓN: "Ese número ya está registrado con {método}. Revisa el número del voucher." |
| Envío | 409 `pago_en_validacion` · `cuota_pagada` · `cuota_no_pagable` | El formulario se sustituye por el aviso de "Cuota no pagable" que corresponda (se recarga la reserva) |
| Envío | 413 `archivo_muy_grande` / 422 `formato_no_admitido` | Error bajo CAPTURA (mismos textos que la validación local). Si el archivo local pesa ≤ 5 MB (el servidor cuenta distinto): "La captura es demasiado pesada para subirla. Sube una más ligera, de hasta 5 MB." |
| Envío | 422 `metodo_no_disponible` | Aviso Error "{Método} ya no está disponible. Elige otro método." Se recargan los métodos; el resto de datos se conserva |
| Envío | 422 `datos_invalidos` + `detalles.campo` | Error bajo ese campo (`monto`, `numero_operacion`, `captura`, `metodo`) + resumen; sin `campo`, aviso Error con el `mensaje` |
| Envío | 503 · red · no JSON | Aviso Error "No pudimos registrar el pago: el servicio no responde. Tus datos siguen aquí; inténtalo en unos minutos." · "Sin conexión. Tus datos siguen aquí; revisa tu red y vuelve a intentarlo." · "Algo salió mal. Tus datos siguen aquí; inténtalo de nuevo." Sin "Reintentar": el Primario sigue disponible |
| Envío | 401 | Aviso de sesión + "Ir al acceso" (`?volver=`). Al volver hay que adjuntar la captura otra vez: el navegador no conserva archivos |
| Éxito | 201 | Redirige a `/app/reservas/detalle?id=&aviso=pago-registrado` |

Permisos: solo el dueño; la API es la barrera (403). Un Administrador no registra pagos en nombre del cliente (v1).

## Copy

| Elemento | Texto |
|---|---|
| Ruta | Inicio / Reservas / {folio} / Pagar |
| Título · descripción | REGISTRAR PAGO · "Paga la cuota con el método que prefieras y sube la captura del comprobante. El estudio la revisa y te avisa por correo." |
| Métodos | Transferencia bancaria · Yape · Plin · Tarjeta |
| Etiquetas | MÉTODO DE PAGO · MONTO PAGADO (S/) · NÚMERO DE OPERACIÓN · CAPTURA DEL COMPROBANTE |
| Ayudas | Monto: "El que pagaste de verdad, con céntimos (225,00)." · Operación: "Está en la constancia de tu app o en el voucher." · Captura: "JPG, PNG o PDF, hasta 5 MB. Que se lean el monto, la fecha y el número de operación." |
| Errores locales | "Elige cómo pagaste." · "Escribe el monto que pagaste, mayor que 0 (por ejemplo, 225,00)." · "Escribe el número de operación." · "Escribe de 4 a 40 letras, cifras o guiones." · "Adjunta la captura del comprobante." · "La captura pesa {n} MB. Sube una de hasta 5 MB." · "Sube la captura en JPG, PNG o PDF." |
| Acciones | "Registrar pago" · "Volver a la reserva" · captura: "Seleccionar archivo", "Quitar {nombre}" |
| Aviso `pago-registrado` (en el detalle) | Éxito "Pago registrado. Queda pendiente de validación." + "Te avisaremos por correo cuando el estudio lo revise." |

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; DATOS PARA PAGAR es `<h3>` dentro de P1. El lateral es `<aside aria-labelledby>`.
- Orden de foco: (móvil: lateral sin controles) → métodos → monto → operación → seleccionar captura → quitar → "Volver a la reserva" → "Registrar pago".
- Los datos para pagar están en una región `aria-live="polite"`: al cambiar de método se anuncian una vez.
- Región `role="status"` estable de la isla para carga y resultado; al fallar el envío, el foco va al aviso. La ayuda de monto distinto entra por `aria-describedby` (no interrumpe).
- Miniatura: `alt="Vista previa de la captura {nombre}"`.

## Pendientes

- Ninguno. El contacto del estudio y los límites de `numero_operacion` los fija [RF-05](../../03-requerimientos/RF-05.md) (revisión visual de pagos, 2026-11-16).
- **Ampliada por RF-17 y RF-20:** resumen legal de lectura antes de "Registrar pago" ([aceptaciones](RF-17-registro-y-aceptaciones.md#composición)) y "Incluye IGV" en el lateral ([cambios sensibles](RF-20-cambios-sensibles.md#desglose-de-igv)).
- **Ampliada por RF-18:** panel `P0 CRÉDITO` con "Usar mi crédito" antes de P1 ([pago con crédito](RF-18-creditos.md#pago-con-crédito)).
