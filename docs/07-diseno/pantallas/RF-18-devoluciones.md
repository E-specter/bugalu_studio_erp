---
id: pantalla-rf-18-devoluciones
titulo: Pantalla — Cola de devoluciones (Administrador)
estado: aprobado
depende_de: [RF-18, ADR-015, pantalla-rf-05-pagos, pantalla-rf-18-creditos, diseno-brief, patron-tablas-y-tableros, patron-formularios, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-barra-acciones, comp-indicador-estado, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Devoluciones

| Campo | Valor |
|---|---|
| Requerimiento | [RF-18](../../03-requerimientos/RF-18.md): CA-07 (decidir y marcar realizada), CA-13 (devolución del estudio y su plazo), CA-16 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/pagos/devoluciones?estado=pendiente\|aprobada\|realizada\|rechazada` (sin `estado`: pendientes), `/app/pagos/devoluciones/revisar?id=`. URL: `estado`, `id`, `aviso` |
| Isla | `<bugalu-pagos vista="devoluciones\|devolucion">` (vistas nuevas de la isla de [pagos](RF-05-pagos.md)) |

**Decisión del brief: subruta de PAGOS, no destino nuevo.** "DEVOLUCIONES" pasa de 9 caracteres ([navegación táctil](../componentes/navegacion-tactil.md)) y es trabajo de cobros, poco frecuente. Se llega desde la lista de [pagos](RF-05-pagos.md#composición): la ranura `acciones` suma "Devoluciones" (Secundario como enlace) junto a "Editar datos para pagar", y si hay trabajo, un [aviso](../componentes/aviso.md) Información sobre la tabla: "Tienes 2 devoluciones por decidir y 1 por hacer." + "Ver devoluciones" (se pide `GET /devoluciones?estado=pendiente` y `?estado=aprobada` al cargar la lista; error → sin aviso). También desde el correo de CA-14.

## Recorrido

1. El Administrador abre DEVOLUCIONES: las pendientes, la más antigua arriba.
2. "Revisar devolución de {folio}": lee el motivo del cliente y el crédito.
3. Pendiente: decide total, parcial (con monto) o rechazo (con motivo) → vuelve con `?aviso=devolucion-decidida`.
4. Aprobada: devuelve el dinero fuera de la app y "Marcar como realizada" con una nota (medio y número de operación) → `?aviso=devolucion-realizada`. Las del estudio llegan ya aprobadas, con su plazo de 7 días hábiles.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Devoluciones | `GET /devoluciones?estado=` → `[Devolucion]` | Total "3 devoluciones pendientes". Pendientes y aprobadas por `solicitada_en` ascendente (aprobadas del estudio: por `limite`); realizadas y rechazadas, descendente |
| Reserva | `id_reserva` + folio | Folio en `fuente-familia-tecnica`, enlace al detalle (ver Preguntas) |
| Tipo | `tipo` | `nivel_1` "Crédito de cancelación" · `estudio` "Cancelación del estudio" |
| Cliente | `cliente.nombre` | Tal cual; `null` → "Sin nombre" |
| Monto | Saldo del crédito o lo pagado (ver Preguntas); `monto_aprobado` tras decidir | `S/ 100,00`; parcial: "S/ 60,00 de S/ 100,00" |
| Fechas | `solicitada_en`, `decidida_en`, `realizada_en` | Relativa < 7 días con absoluta en `title`; si no, `D MMM, HH:mm` |
| Plazo (estudio) | `limite` | [Plazo restante](../patrones/estructura-app.md#formato-de-datos) ("27 nov · faltan 3 d"); pasado: [etiqueta](../componentes/etiqueta-tecnica.md) Alerta FUERA DE PLAZO + "Venció el 27 nov" |
| Estado | `estado` | PENDIENTE (Aviso) · APROBADA (Aviso, aún falta hacerla) · REALIZADA (Éxito) · RECHAZADA (Alerta) |
| Motivos y nota | `motivo`, `motivo_decision`, `nota_realizada` | Tal cual |
| Decidir | `POST /devoluciones/{id}/decidir {decision, monto?, motivo?}` → 200 | Radio DECISIÓN; MONTO A DEVOLVER (S/) solo en parcial, de 0,01 al saldo; MOTIVO (Área, ≤ 500) |
| Marcar realizada | `POST /devoluciones/{id}/realizada {nota}` → 200 | NOTA (Área, obligatoria, ≤ 500) |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Lista | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción; acción Secundario como enlace "Volver a pagos" |
| Lista | Controles | [etiquetas](../componentes/etiqueta-tecnica.md) Filtro | PENDIENTES · APROBADAS · REALIZADAS · RECHAZADAS |
| Lista | Principal | [panel](../componentes/panel.md) `DEVOLUCIONES` + [tabla](../componentes/tabla.md) Directorio | RESERVA (folio y tipo debajo) · CLIENTE · MONTO · SOLICITADA (en APROBADAS: PLAZO; en las demás: DECIDIDA / REALIZADA) · "Revisar devolución de {folio}" (Secundario como enlace) |
| Revisar | Principal | panel `V1 SOLICITUD` | `<dl>`: CLIENTE, RESERVA (folio enlazado), TIPO, MONTO, SOLICITADA, MOTIVO DEL CLIENTE (`nivel_1`), PLAZO (`estudio`) |
| Revisar | Lateral | panel Lateral `V2 DECISIÓN` (pendiente) | `<fieldset>` DECISIÓN con [casillas](../componentes/casilla.md) Radio: "Devolver todo ({monto})" · "Devolver una parte" (muestra MONTO A DEVOLVER) · "Rechazar" → MOTIVO → consecuencias → Primario cuyo texto sigue a la opción: "Aprobar devolución total" · "Aprobar devolución parcial" · "Rechazar devolución". Una acción: sin barra |
| Revisar | Lateral | panel Lateral `V2 DEVOLVER` (aprobada) | Monto aprobado y, en las del estudio, el plazo → NOTA → consecuencias → Primario "Marcar como realizada" |
| Revisar | Lateral | [indicador](../componentes/indicador-estado.md) Barra (realizada o rechazada) | Correcto "REALIZADA" + `realizada_en` y la nota debajo · Problema "RECHAZADA" + `decidida_en` y el motivo |

Sin confirmación aparte, como "Aprobar pago" ([pagos](RF-05-pagos.md#composición)): la ficha es la revisión y el formulario con motivo o nota es la confirmación. Adaptabilidad: la de [pagos](RF-05-pagos.md#composición) (tarjetas en móvil, lateral después del principal).

## Estados

| Vista | Situación | Forma y texto |
|---|---|---|
| Lista | Vacío (pendientes) | "No hay devoluciones por decidir" + "Cuando un cliente pida la devolución de un crédito, aparecerá aquí." Sin acción |
| Lista | Vacío (otros filtros) | "Aún no hay devoluciones aprobadas." / "… realizadas." / "… rechazadas." + "Ver pendientes" (Secundario) |
| Ambas | Carga | Panel "Cargando…", `aria-busy` |
| Revisar | 404 o `id` no válido | Panel `[404] DEVOLUCIÓN NO ENCONTRADA` + aviso Información "No encontramos esta devolución." + "Volver a devoluciones" |
| Decidir | Validación local | Sin opción: "Elige qué decides." · Parcial: "Escribe un monto entre S/ 0,01 y {saldo}." · Rechazo sin motivo: "Escribe por qué la rechazas." · "El motivo admite hasta 500 caracteres." |
| Decidir | 422 `monto_invalido` · `motivo_requerido` | Los mismos textos bajo el campo |
| Realizada | Validación local / 422 | "Escribe el medio y el número de operación." · "La nota admite hasta 500 caracteres." |
| Envío | Enviando | Primario en Carga ("Aprobando…", "Rechazando…", "Guardando…"); campos deshabilitados |
| Envío | 409 `devolucion_decidida` · `devolucion_no_aprobada` | Aviso Información "Esta devolución ya se decidió, quizá desde otra sesión." / "Esta devolución no está aprobada: no se puede marcar como realizada." Ficha recargada |
| Ambas | 401 · 403 · 503 · red · no JSON · sin JS | Como en [pagos](RF-05-pagos.md#estados) (403: "Esta sección es solo para el Administrador."); al enviar, sin "Reintentar" |
| Lista | Éxito | `devolucion-decidida` "Decisión registrada. Avisamos al cliente por correo." · `devolucion-realizada` "Devolución marcada como hecha. Avisamos al cliente con tu nota." |

Claves `aviso` (lista cerrada): las dos de la tabla.

## Copy

| Elemento | Texto |
|---|---|
| Lista: ruta e índice | Inicio / Pagos / Devoluciones · `[A11] COBROS / DEVOLUCIONES` |
| Lista: título y descripción | DEVOLUCIONES · "Devoluciones que pidieron los clientes y las de cancelaciones del estudio. Decide cada una y márcala cuando hayas devuelto el dinero." |
| Revisar: ruta, título y descripción | Inicio / Pagos / Devoluciones / {folio} · REVISAR DEVOLUCIÓN · "{cliente} · {tipo} de la reserva {folio}" |
| Consecuencias de decidir | Total: "El crédito queda en S/ 0,00 y avisamos al cliente. Luego haces la devolución fuera de la app y la marcas como hecha." · Parcial: "Se descuenta {monto} del crédito; el resto sigue como crédito. Avisamos al cliente." · Rechazo: "El crédito sigue igual y el cliente verá tu motivo." Ninguna decisión se deshace |
| Consecuencias de realizada | "El cliente recibe tu nota por correo y la ve en Mis créditos. No se puede deshacer." |
| Ayudas | Motivo: "El cliente lo verá. Obligatorio si devuelves una parte o rechazas." · Nota: "Medio y número de operación. Por ejemplo: «Yape, operación 12345678»." |
| Columnas | RESERVA · CLIENTE · MONTO · SOLICITADA / PLAZO / DECIDIDA / REALIZADA |

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; tabla con `<caption>` y folio como `<th scope="row">`. Filtros con `aria-current="true"`.
- DECISIÓN es `<fieldset>` + `<legend>`; MONTO A DEVOLVER aparece justo después de su opción y esta lleva `aria-controls`. El cambio de texto del Primario no se anuncia: la opción marcada ya lo dice.
- FUERA DE PLAZO lo dice en texto. Región `role="status"` estable para la carga ("3 devoluciones pendientes") y cada resultado; al fallar un envío, el foco va al aviso.

## Preguntas para leader

Respuestas de leader (2026-11-17): 1, resuelta con las precisiones 3 de RF-18; 2, sí, el motivo es obligatorio en parcial y rechazo (10 a 500) y opcional en total (hasta 500, sin mínimo); 3, nota de 1 a 500; 4, no. Las consecuencias no mencionan el nuevo vencimiento porque `Devolucion` no trae el del crédito.

1. `Devolucion` no trae el monto pedido (saldo del crédito o lo pagado en las del estudio) ni el folio, y no hay `GET /devoluciones/{id}`. Propuesta: sumar `monto`, `folio` y el endpoint de lectura. Sin ellos, Revisar carga la lista y busca el `id`, y el monto sale de `GET /creditos?id_cliente=`.
2. ¿El motivo es obligatorio también en la devolución parcial? El copy lo deja opcional (solo el rechazo lo exige).
3. Largo de la nota de realizada y del motivo de decisión: el contrato no lo fija; se asume 1 a 500.
4. El contador de la navegación solo cuenta pagos por validar; ¿deben sumar las devoluciones pendientes? Propuesta: no; basta el aviso de la lista y el correo.
