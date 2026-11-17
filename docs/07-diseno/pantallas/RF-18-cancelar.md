---
id: pantalla-rf-18-cancelar
titulo: Pantalla — Detalle de la reserva con cancelación por niveles (cliente)
estado: borrador
depende_de: [RF-18, ADR-015, legal-condiciones-de-contratacion, pantalla-rf-04-mis-reservas, diseno-brief, patron-formularios, patron-estados-sistema, comp-panel, comp-tabla, comp-boton, comp-barra-acciones, comp-aviso, comp-indicador-estado, comp-etiqueta-tecnica]
---

# Detalle de la reserva: cancelación por niveles

| Campo | Valor |
|---|---|
| Requerimiento | [RF-18](../../03-requerimientos/RF-18.md): CA-01, CA-02, CA-03, CA-11 (lo que ve el cliente), CA-16 |
| Actores | Artista/Cliente (dueño); Personal y Administrador ven los mismos bloques D4 y D5 |
| Estructura | App, portal; **amplía** el detalle de [mis reservas](RF-04-mis-reservas.md#detalle) |
| Ruta | `/app/reservas/detalle?id=` (URL: `id`, `aviso`). El panel de cancelar no tiene URL, como hoy |
| Isla | `<bugalu-reservas vista="detalle">` (existente) |

Sustituye la regla de RF-04 "con pagos, pídelo al estudio": el párrafo y el contacto del estudio salen del lateral; el 409 `tiene_pagos` desaparece. Reprogramar y la elección tras una cancelación del estudio: [reprogramar](RF-18-reprogramar.md). Acciones del Administrador: [acciones del Administrador](RF-18-acciones-administrador.md).

## Recorrido

1. El cliente abre su reserva `Pre-reservada` o `Confirmada` con inicio futuro. En el lateral ve "Reprogramar" (o por qué no puede) y "Solicitar cancelación".
2. "Solicitar cancelación" sustituye el botón por el panel `CANCELAR RESERVA {folio}`, que pide la vista previa y explica qué pasa con su pago según el nivel de ese momento.
3. "Confirmar cancelación" la cancela; "Volver a la reserva" cierra el panel sin cambiar nada. Si se cruzó un plazo mientras leía, el panel se repinta con el nivel nuevo y pide confirmar otra vez.
4. El detalle se recarga con `?aviso=reserva-cancelada` y el bloque D4 con lo retenido y el crédito; el crédito lo ve en [mis créditos](RF-18-creditos.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Vista previa | `GET /reservas/{id}/cancelacion` → `VistaCancelacion` | Se pide al abrir el panel y, con `Confirmada`, también al cargar el detalle (para saber si se puede reprogramar) |
| Nivel | `nivel` (1, 2, 3 o `null` sin pagos) | En palabras (Copy); nunca solo un número ni solo un color |
| Anticipación | `anticipacion_horas` | Como [plazo restante](../patrones/estructura-app.md#formato-de-datos) sin la absoluta: "Faltan 1 d 6 h para tu sesión." |
| Importes | `pagado`, `en_validacion`, `retenido`, `credito` | `S/ 100,00`; en validación solo si > 0 |
| Vencimiento del crédito | `credito_vence` | `D MMM AAAA` ("vence el 17 dic 2026"); solo si `credito` > 0 |
| Reprogramar | `puede_reprogramar`, `reprogramaciones_restantes` | Decide el botón y su explicación ([reprogramar](RF-18-reprogramar.md#entrada-desde-el-detalle)) |
| Plazos de la reserva | `parametros_aplicados.{horas_nivel_1, horas_nivel_2, porcentaje_penalizacion_nivel_2}` → `{h1}`, `{h2}`, `{p}` | "48 h", "24 h", "25 %". Sin ellos, el texto se escribe sin la cifra (ver Preguntas) |
| Cancelar | `POST /reservas/{id}/cancelar {nivel_esperado}` → 200 `Reserva` | `nivel_esperado` = el `nivel` mostrado; sin pagos, se omite |
| Cancelación hecha | `Reserva.cancelacion.{nivel, aviso_en, por, pagado, retenido, credito, nota, excepcion?}` | Bloque D4 |
| Reprogramaciones | `Reserva.reprogramaciones[]` | Bloque D5 |
| Cuotas | `cuotas[].{estado, pagado}` | Estado nuevo ANULADA; pagado parcial (crédito o captura) |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Lateral | [indicador](../componentes/indicador-estado.md) Barra (existente) | Estados nuevos en la tabla Estados |
| Lateral | [botón](../componentes/boton.md) Secundario como enlace "Reprogramar" + ayuda | Solo dueño y `Confirmada`; reglas en [reprogramar](RF-18-reprogramar.md#entrada-desde-el-detalle) |
| Lateral | botón Peligro "Solicitar cancelación" | Dueño, `Pre-reservada` o `Confirmada`, inicio futuro, **con o sin pagos**. Va el último |
| Lateral (al abrir) | [panel](../componentes/panel.md) Lateral `CANCELAR RESERVA {folio}` | Nivel (`<p>` con el nivel en `fuente-peso-titulo` y la anticipación) → `<dl>` PAGADO · EN VALIDACIÓN · SE RETIENE · PASA A CRÉDITO · EL CRÉDITO VENCE → consecuencias del nivel → enlace "Leer las condiciones de cancelación" (`/legal/condiciones-de-contratacion/`) → si `puede_reprogramar`, enlace "Reprogramar en lugar de cancelar" → [barra de acciones](../componentes/barra-acciones.md) Móvil: "Volver a la reserva" (Secundario) + Peligro "Confirmar cancelación", los dos a ancho completo y mismo alto (CA-16: igual de visibles) |
| Principal | panel `D3 CUOTAS` (existente) | ESTADO suma ANULADA ([etiqueta](../componentes/etiqueta-tecnica.md) Neutra) con "Se anuló al cancelar." / "Se anuló por la inasistencia." debajo. Con `0 < pagado < monto`: "Pagado S/ 50,00 · falta S/ 50,00" bajo la etiqueta PENDIENTE |
| Principal | panel `D4 CANCELACIÓN` (si hay `cancelacion`) | `<dl>`: AVISO (`aviso_en`, `D MMM, HH:mm`) · A PEDIDO DE ("Tuyo" / "Del estudio"; al personal: "Del cliente") · NIVEL (Copy; `null` → "Sin pagos") · PAGADO · RETENIDO · PASÓ A CRÉDITO (+ enlace "Ver mis créditos" para el dueño; 0 → "Nada") · NOTA DEL ESTUDIO (tal cual) · CASO EXCEPCIONAL ("Tratada como nivel 1 el 20 nov: {motivo}") |
| Principal | panel `D5 REPROGRAMACIONES` (si hay alguna) | [tabla](../componentes/tabla.md) Directorio: FECHA DEL CAMBIO (`en`) · ANTES (`anterior_inicio`) · AHORA (`nuevo_inicio`) · NIVEL ("Nivel 1" · "Nivel 2" · "Sin costo" si `null`) · PENALIZACIÓN · TOTAL ("S/ 200,00 → S/ 240,00"). Más reciente arriba; < `punto-quiebre-escritorio`, tarjetas |

Orden del principal: D1 · D2 · D3 · D4 · D5. Adaptabilidad: la de [mis reservas](RF-04-mis-reservas.md#composición) (lateral primero en móvil). El panel de cancelar sigue la [decisión de RF-04](RF-04-mis-reservas.md#cancelar): foco a su `<h2>`; "Volver a la reserva" lo cierra y devuelve el foco a "Solicitar cancelación". [Lista](RF-04-mis-reservas.md#lista): HISTORIAL suma `No asistió`; su PAGO es "—".

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Detalle | `No asistió` | Etiqueta Alerta NO ASISTIÓ en D1; Barra Problema "NO ASISTIÓ" + "No llegaste en los primeros {t} minutos. Se retuvo lo pagado ({pagado}); no hay crédito ni cobro adicional." |
| Detalle | `Cancelada` con `cancelacion.credito` > 0 | Barra Neutro "CANCELADA" + "{credito} pasaron a crédito. Úsalo en otra reserva." |
| Detalle | `Cancelada`, nivel 3 o retenido = pagado | Barra Neutro "CANCELADA" + "Se retuvo lo pagado ({retenido}), como indican las condiciones." |
| Panel | Carga | "Calculando qué pasa con tu pago…" con `aria-busy`; los botones del panel aún no se pintan |
| Panel | Enviando | "Confirmar cancelación" en Carga "Cancelando…"; "Volver a la reserva" deshabilitado |
| Panel | 409 `nivel_cambiado` | Se repinta con `detalles` (la vista nueva) y, arriba del panel, [aviso](../componentes/aviso.md) Aviso "Mientras lo revisabas pasó un plazo: ahora es {nivel en palabras}. Revisa qué pasa con tu pago y confirma de nuevo." Foco al aviso. `nivel_esperado` toma el nuevo valor |
| Panel | 409 `no_cancelable` (al abrir o al confirmar) | Como en [mis reservas](RF-04-mis-reservas.md#estados): panel cerrado, detalle recargado y aviso Información "Esta reserva ya no se puede cancelar: está {estado}." |
| Panel | Error al pedir la vista previa (503, red, no JSON) | Aviso Error dentro del panel con los textos de [mis reservas](RF-04-mis-reservas.md#estados) + "Reintentar"; "Volver a la reserva" sigue disponible. Nunca se ofrece confirmar sin vista previa |
| Panel | Error al confirmar | Textos de mis reservas, sin "Reintentar": el botón sigue disponible y la vista previa se conserva |
| Detalle | `?aviso=reserva-cancelada` | Aviso Éxito según la reserva recargada: sin pagos, el texto de RF-04; con crédito "Reserva cancelada. {credito} pasaron a crédito hasta el {vence}. Te enviamos el detalle por correo."; sin crédito "Reserva cancelada. Se retuvo lo pagado ({retenido}). Te enviamos el detalle por correo." |
| Todas | 401 · 403 · 404 · sin JS | Como en [mis reservas](RF-04-mis-reservas.md#estados) |

Permisos: "Solicitar cancelación" y "Reprogramar" son del dueño. El personal ve D4 y D5, sin acciones de cancelar. Lo del Administrador, en [acciones del Administrador](RF-18-acciones-administrador.md).

## Copy

| Elemento | Texto |
|---|---|
| Nivel (panel y D4) | Sin pagos: "Sin pagos: cancelas gratis." · "Nivel 1: avisas con más de {h1} h." · "Nivel 2: avisas entre {h2} y {h1} h antes." · "Nivel 3: avisas con {h2} h o menos." |
| Consecuencias, sin pagos | La de RF-04: "El horario se libera al momento y no se te cobra nada. No se puede deshacer: si quieres ese horario otra vez, tendrás que reservarlo de nuevo si sigue libre." |
| Consecuencias, nivel 1 | "Todo lo que pagaste pasa a crédito para otra reserva tuya. Si prefieres el dinero, puedes pedir la devolución desde Mis créditos. El horario se libera al momento y la cancelación no se puede deshacer." |
| Consecuencias, nivel 2 | "Se retiene una penalización del {p} % del total. El resto pasa a crédito para otra reserva tuya, sin devolución. El horario se libera al momento y la cancelación no se puede deshacer." |
| Consecuencias, nivel 3 | "Se retiene todo lo que pagaste y no hay crédito. El horario se libera al momento y la cancelación no se puede deshacer." |
| Pago en validación (si > 0) | Nivel 1 y 2: "Tienes {en_validacion} en validación. Si el estudio lo aprueba, se sumará a tu crédito." · Nivel 3: "… Si el estudio lo aprueba, también se retendrá." |
| Etiquetas del `<dl>` | PAGADO · EN VALIDACIÓN · SE RETIENE · PASA A CRÉDITO · EL CRÉDITO VENCE |
| Acciones | "Solicitar cancelación" · "Confirmar cancelación" · "Volver a la reserva" · "Leer las condiciones de cancelación" · "Reprogramar en lugar de cancelar" · "Ver mis créditos" |
| Títulos | `CANCELAR RESERVA {folio}` · `D4 CANCELACIÓN` · `D5 REPROGRAMACIONES` |

## Accesibilidad

- El panel es `<section aria-labelledby>` con `<h2>`; el nivel va en texto antes del `<dl>`, así el lector lo oye primero. Etiquetas NO ASISTIÓ y ANULADA dicen el estado en texto.
- Orden de foco en el panel: enlace a las condiciones → "Reprogramar en lugar de cancelar" → "Volver a la reserva" → "Confirmar cancelación".
- La región `role="status"` de la isla anuncia "Vista previa lista: nivel 2, se retienen S/ 50,00." y el resultado; el 409 lleva el foco al aviso. D5 es `<table>` con `<caption>` y FECHA DEL CAMBIO como `<th scope="row">`.

## Preguntas para leader

1. `Reserva` no expone `parametros_aplicados`: sin `horas_nivel_1`, `horas_nivel_2`, `porcentaje_penalizacion_nivel_2` y `minutos_tolerancia_inasistencia` el texto no puede decir "48 h", "25 %" ni "15 minutos". Propuesta: exponerlos de solo lectura en `Reserva` (o en `VistaCancelacion`). Sin ellos: "Nivel 1: avisas con tiempo." · "Nivel 2: avisas con poco tiempo." · "Nivel 3: avisas a última hora." y sin cifra de penalización.
2. `cancelacion.por` (`cliente` | `estudio`) dice a pedido de quién, no quién la registró. ¿Se muestra el autor al Administrador? El contrato no lo trae; propuesta: no mostrarlo en v1.
3. Las [condiciones](../../08-legal/condiciones-de-contratacion.md#cancelar-o-reprogramar) dicen "Nivel 3: menos de 24 horas"; RF-18 dice "24 h o menos". El copy sigue a RF-18; el texto legal debería decir lo mismo.
4. ¿La página pública de las condiciones tiene ancla por sección (`#cancelar-o-reprogramar`)? Si la tiene, el enlace del panel la usa.
