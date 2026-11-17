---
id: pantalla-rf-18-creditos
titulo: Pantalla — Mis créditos, pedir devolución y pagar con crédito
estado: borrador
depende_de: [RF-18, ADR-015, pantalla-rf-04-mis-reservas, pantalla-rf-05-registrar-pago, pantalla-rf-01-solicitudes, diseno-brief, patron-tablas-y-tableros, patron-formularios, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-barra-acciones, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Mis créditos y pago con crédito

| Campo | Valor |
|---|---|
| Requerimiento | [RF-18](../../03-requerimientos/RF-18.md): CA-05, CA-06, CA-07 (lado cliente), CA-16 |
| Actores | Artista/Cliente (los suyos); Administrador los ve en la ficha del cliente |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/reservas/creditos?ver=vigentes\|historial` (URL: `ver`, `aviso`); el pago, en `/app/reservas/pagar` (existente) |
| Isla | `<bugalu-creditos>` (nueva); `<bugalu-pago>` (existente, ampliada) |

**Decisión del brief: subruta de RESERVAS, no destino nuevo.** El crédito nace de una reserva y se gasta en otra; un destino que casi siempre estaría vacío ocuparía una de las cinco plazas de la [navegación táctil](../componentes/navegacion-tactil.md). Se llega por: "Mis créditos" (Secundario como enlace) en la ranura `acciones` del encabezado de [mis reservas](RF-04-mis-reservas.md#lista), junto a "Reservar sala"; "Ver mis créditos" de D4 ([cancelar](RF-18-cancelar.md#composición)); el pago; y el correo de aviso de vencimiento.

## Recorrido

1. El cliente abre "Mis créditos": ve cuánto tiene disponible y cada crédito con su saldo, vencimiento, tipo y reserva de origen.
2. En un crédito de nivel 1 o de caso excepcional vigente, "Pedir devolución de {folio}" abre el panel lateral; escribe el motivo y confirma.
3. Al pagar una cuota, en [registrar pago](RF-05-registrar-pago.md), aplica su crédito a todo o parte de la cuota.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Créditos | `GET /creditos` → `[Credito]` | VIGENTES: `vigente`, por `vence` ascendente. HISTORIAL: `agotado` y `vencido`, descendente |
| Disponible | Suma de `saldo` de los `vigente` sin `devolucion.estado = pendiente` | Importe; la isla suma en céntimos enteros, solo para mostrar (la API valida al aplicar) |
| Origen | `origen.{id_reserva, folio}` | Folio en `fuente-familia-tecnica`, enlace a `/app/reservas/detalle?id=` |
| Tipo | `tipo` | `nivel_1` "Cancelación (nivel 1)" · `nivel_2` "Cancelación (nivel 2)" · `reprogramacion` "Diferencia al reprogramar" · `excepcion` "Caso excepcional" |
| Saldo | `saldo`, `monto` | "S/ 60,00" y, si difiere, debajo "de S/ 100,00" |
| Vence | `vence` | [Plazo restante](../patrones/estructura-app.md#formato-de-datos) en VIGENTES ("17 dic 2026 · faltan 12 d"); fecha sola en HISTORIAL |
| Estado | `estado`, `devolucion?` | VIGENTE (Éxito) · AGOTADO (Neutra) · VENCIDO (Alerta); faltan ≤ 7 días: además VENCE PRONTO (Aviso). Devolución, en texto bajo el estado (Estados) |
| Pedir devolución | `POST /creditos/{id}/devolucion {motivo}` → 201 `Devolucion` | [Campo](../componentes/campo.md) Área, 10–500 caracteres (`minlength`, `maxlength`) |
| Aplicar crédito | `POST /cuotas/{id}/credito {monto}` → 200 `Reserva` | Campo importe; sin `id_credito`: la API usa el que vence antes |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción; sin acción |
| Controles | [etiquetas](../componentes/etiqueta-tecnica.md) Filtro | VIGENTES · HISTORIAL |
| Principal | [panel](../componentes/panel.md) Destacado `DISPONIBLE` (solo en VIGENTES) | "S/ 150,00 para usar en tus reservas" en `fuente-familia-titulo` + "Lo eliges al pagar una cuota." |
| Principal | panel `CRÉDITOS` + [tabla](../componentes/tabla.md) Directorio | ORIGEN (folio y tipo debajo) · SALDO · VENCE · ESTADO · acción "Pedir devolución de {folio}" (Secundario) solo si `tipo` es `nivel_1` o `excepcion`, `vigente` y sin devolución pendiente o decidida. < `punto-quiebre-escritorio`, tarjetas |
| Lateral | panel Lateral `CÓMO FUNCIONA` | Texto fijo (Copy) + enlace "Leer las condiciones" (`/legal/condiciones-de-contratacion/`) |
| Lateral (al pedir) | panel Lateral `PEDIR DEVOLUCIÓN · {folio}` | `<dl>` SALDO → Área MOTIVO → consecuencias → [barra de acciones](../componentes/barra-acciones.md) Móvil "Volver" + Primario "Enviar solicitud" |

Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md), [formularios](../patrones/formularios.md). El panel de devolución sigue la [decisión de cancelar](RF-04-mis-reservas.md#cancelar): sustituye a CÓMO FUNCIONA, foco a su `<h2>`; "Volver" lo cierra y devuelve el foco al botón de la fila. Adaptabilidad: < `punto-quiebre-escritorio`, el lateral va después de la tabla.

## Pago con crédito

Amplía [registrar pago](RF-05-registrar-pago.md#composición). Se pide `GET /creditos` junto con la reserva; si el disponible es 0, nada cambia.

| Región | Contenido |
|---|---|
| Principal, antes de P1 | Panel `P0 CRÉDITO`: [casilla](../componentes/casilla.md) "Usar mi crédito (S/ 150,00 disponible)". Marcada: MONTO DEL CRÉDITO (S/) (importe, prellenado con el menor entre el disponible y lo que falta de la cuota; ayuda "Hasta S/ 100,00. Se aplica al momento, sin validación, y no se puede deshacer.") + Secundario "Aplicar crédito". Sin JS en el resto: igual que la página |
| Tras aplicar, cuota cubierta | Redirige al detalle con `?aviso=pagado-con-credito`: Éxito "Pagaste la cuota con tu crédito." + si era el adelanto de una `Pre-reservada`: "Tu reserva quedó confirmada." |
| Tras aplicar, falta algo | La página se recarga: lateral suma PAGADO CON CRÉDITO y FALTA PAGAR; P0 desaparece si ya no hay disponible; MONTO PAGADO de P2 se prellena con lo que falta; aviso Éxito "Aplicaste S/ 50,00 de crédito. Paga los S/ 50,00 que faltan con tu comprobante." |

Lo que falta se paga con captura como hoy. "Registrar pago" sigue siendo el único Primario.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lista | Sin créditos | Vacío: "No tienes créditos" + "Si cancelas o reprogramas una reserva con pagos, lo que pase a crédito aparecerá aquí." + Secundario "Ver mis reservas" |
| Lista | Filtro sin resultados | "No tienes créditos vigentes." / "Aún no hay créditos en tu historial." + "Ver historial" / "Ver vigentes" |
| Fila | Devolución | `pendiente` "Devolución pedida el 18 nov. Mientras la revisamos, este crédito no se usa ni vence." · `aprobada` "Devolución aprobada: {monto_aprobado}. Te la enviamos fuera de la app." (+ si parcial: "El resto sigue como crédito.") · `rechazada` "Devolución rechazada: «{motivo_decision}»." · `realizada` "Devolución hecha el 20 nov: {nota_realizada}." |
| Lista, P0 | Carga | "Cargando…", `aria-busy` |
| Panel | Validación local | "Escribe el motivo, de 10 a 500 caracteres." |
| Panel | Enviando | "Enviando…"; "Volver" deshabilitado |
| Panel | 409 `devolucion_pendiente` · `credito_no_vigente` · `devolucion_no_permitida` | Panel cerrado, lista recargada y aviso Información "Ya pediste la devolución de este crédito." · "Este crédito ya no está vigente." · "Este crédito no admite devolución." |
| Panel | Éxito 201 | Panel cerrado; aviso Éxito "Solicitud enviada. El estudio la revisa y te avisa por correo." La fila muestra la devolución pendiente |
| P0 | 422 `monto_invalido` / local | Bajo el campo: "Escribe un monto mayor que 0 y de hasta {máximo}." |
| P0 | 409 `credito_insuficiente` | "Tu crédito cambió: ahora tienes {disponible}. Revisa el monto." Se recargan los créditos |
| P0 | 409 `cuota_pagada` · `no_pagable` | El aviso de "Cuota no pagable" de [registrar pago](RF-05-registrar-pago.md#estados) |
| Todo | 401 · 503 · red · no JSON · sin JS | Como en [mis reservas](RF-04-mis-reservas.md#estados); al enviar, sin "Reintentar" |

Permisos: el cliente solo ve los suyos (la API filtra).

## Ficha del cliente (Administrador)

En [usuarios](RF-01-solicitudes.md#composición), la persona con rol Cliente suma, tras `U3 TEXTOS ACEPTADOS`, el panel `U4 CRÉDITOS`: `GET /creditos?id_cliente=` → tabla Compacta ORIGEN (folio enlazado) · TIPO · SALDO · VENCE · ESTADO, con la devolución en texto como arriba. Solo lectura. Vacío: "Sin créditos." Error: aviso Error en el panel + "Reintentar".

## Copy

| Elemento | Texto |
|---|---|
| Ruta e índice · título | Inicio / Reservas / Créditos · `[P3] SALA / CRÉDITOS` · MIS CRÉDITOS |
| Descripción | "Lo que te queda a favor por cancelar o reprogramar. Úsalo al pagar una cuota antes de que venza." |
| Cómo funciona | "Cada crédito vence 30 días después de generarse y te avisamos 7 días antes. Solo tú lo usas, en cualquier reserva tuya. Los créditos de nivel 1 y de caso excepcional admiten devolución; los de nivel 2 y los de reprogramación, no." |
| Consecuencias de la devolución | "El estudio decide si te devuelve todo, una parte o nada, y te dice por qué. Mientras decide, este crédito no se usa ni vence. El dinero se devuelve fuera de la app." |
| Ayuda del motivo | "Cuéntanos por qué prefieres el dinero. Entre 10 y 500 caracteres." |
| Columnas | ORIGEN · SALDO · VENCE · ESTADO |

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; tabla con `<caption>` y ORIGEN como `<th scope="row">`. Filtros con `aria-current="true"`.
- VENCE PRONTO, VENCIDO y la devolución dicen el estado en texto. La acción de fila lleva el folio en su nombre accesible.
- Región `role="status"` estable: anuncia la carga ("2 créditos vigentes, S/ 150,00 disponible") y cada resultado; al fallar un envío, el foco va al aviso.
- En P0, el campo aparece al marcar la casilla y la casilla tiene `aria-controls` hacia él.

## Preguntas para leader

1. `GET /creditos` no trae el disponible: ¿se acepta sumarlo en la isla (en céntimos, solo para mostrar) o se añade `disponible` a la respuesta?
2. "30 días" y "7 días" del texto fijo salen de `dias_vigencia_credito`, que no llega al cliente. Si el Administrador lo cambia, el texto queda viejo; propuesta: exponerlo en `GET /creditos` o quitar las cifras.
