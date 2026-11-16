---
id: pantalla-rf-05-pagos
titulo: Pantalla — Pagos por validar y datos para pagar (Administrador)
estado: borrador
depende_de: [RF-05, ADR-010, RN-04, RN-18, RN-22, diseno-brief, patron-estructura-app, patron-tablas-y-tableros, patron-formularios, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-archivo, comp-barra-acciones, comp-indicador-estado, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Pagos

| Campo | Valor |
|---|---|
| Requerimiento | [RF-05](../../03-requerimientos/RF-05.md): CA-05, CA-06, CA-08, CA-09 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/pagos/?estado=aprobado\|rechazado` (sin `estado`: por validar), `/app/pagos/revisar?id=`, `/app/pagos/datos`. URL: `estado`, `id`, `aviso` |
| Isla | `<bugalu-pagos vista="lista\|revisar\|datos">` (nueva) |
| Origen Figma | Ninguno; [directorio](../patrones/tablas-y-tableros.md#directorio-tabla) (`161:842`) |

## Recorrido

1. El Administrador entra por PAGOS (`receipt`), con el contador de pagos por validar ([navegación lateral](../componentes/navegacion-lateral.md)). Ve los pendientes, el más antiguo arriba.
2. "Revisar pago de {folio}": mira la captura junto a monto, método y operación, y la cuota que paga.
3. Aprueba → vuelve con `?aviso=pago-aprobado` o `reserva-confirmada`. O rechaza con motivo → `?aviso=pago-rechazado`.
4. "Editar datos para pagar" (desde la lista) → cambia texto y activo de cada método → vuelve con `?aviso=datos-actualizados`.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Pagos | `GET /pagos?estado=` → `[Pago]` | Total "3 pagos por validar" / "12 pagos aprobados" |
| Reserva y cuota | `reserva.folio`, `cuota.hito` | Folio en `fuente-familia-tecnica` (celda principal) con la cuota debajo ("Al reservar") |
| Cliente | `cliente.nombre` | Tal cual; `null` → "Sin nombre" (solo cambia a `color-texto-secundario`; mismo tamaño que un nombre) |
| Método | `metodo` | Transferencia · Yape · Plin · Tarjeta |
| Monto | `monto`, `monto_coincide`, `cuota.monto` | `S/ 225,00` a la derecha; si no coincide, debajo [etiqueta](../componentes/etiqueta-tecnica.md) Alerta NO COINCIDE |
| Operación | `numero_operacion` | `fuente-familia-tecnica`, también en V2 |
| Registrado / validado | `registrado_en`, `validado_en` | Relativa < 7 días con absoluta en `title`; si no, `D MMM, HH:mm` |
| Estado del pago | `estado` | EN VALIDACIÓN (Aviso) · APROBADO (Éxito) · RECHAZADO (Alerta) + `motivo_rechazo` |
| Pago a revisar | `GET /pagos/{id}` | — |
| Captura | `GET /pagos/{id}/captura` → `{url, expira_en}` | Imagen: `<img>` al ancho del panel, alto natural. PDF: [archivo](../componentes/archivo.md) Lectura (`file`) con nombre `comprobante.pdf` y metadato "PDF" → enlace "Abrir comprobante.pdf (pestaña nueva)" |
| Reserva del pago | `reserva.{folio, inicio, estado}` | Folio enlazado a `/app/reservas/detalle?id=`; `D MMM AAAA, HH:mm`; etiqueta de estado de reserva |
| Aprobar / rechazar | `POST /pagos/{id}/aprobar` · `POST /pagos/{id}/rechazar {motivo}` → 200 `Pago` | Motivo: [campo](../componentes/campo.md) Área, 1–300 caracteres (`maxlength="300"`) |
| Datos para pagar | `GET /instrucciones-pago` (al Administrador, los cuatro) · `PUT /instrucciones-pago [{metodo, texto, activo}]` | Por método: Área DATOS PARA PAGAR + [casilla](../componentes/casilla.md) ACTIVO |
| Contacto del estudio | `GET /contacto-estudio` · `PUT /contacto-estudio {texto}` ([RF-05](../../03-requerimientos/RF-05.md)) | Área MENSAJE DE CONTACTO, ≤ 500 (`maxlength="500"`); el cliente lo ve tal cual al cancelar con pagos y sin métodos activos |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Todas | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) (App) | Ruta, índice, título, descripción (Copy). Lista: acción [botón](../componentes/boton.md) Secundario como enlace "Editar datos para pagar" |
| Lista | Controles | [etiquetas](../componentes/etiqueta-tecnica.md) Filtro | POR VALIDAR · APROBADOS · RECHAZADOS (enlaces `?estado=`) |
| Lista | Principal | [panel](../componentes/panel.md) `PAGOS` + [tabla](../componentes/tabla.md) Directorio | RESERVA (folio, cuota debajo) · CLIENTE · MÉTODO · MONTO · OPERACIÓN · REGISTRADO (en aprobados y rechazados: VALIDADO) · "Revisar pago de {folio}" (Secundario como enlace) |
| Revisar | Principal | panel `V1 COMPROBANTE` | Captura y, bajo ella, enlace "Abrir en una pestaña nueva" (`external-link`) |
| Revisar | Principal | panel `V2 PAGO` | `<dl>`: MÉTODO, MONTO (+ NO COINCIDE y "La cuota es de S/ 225,00."), NÚMERO DE OPERACIÓN, REGISTRADO, CLIENTE |
| Revisar | Lateral | panel Lateral `V3 RESERVA` | `<dl>`: RESERVA (folio enlazado), SESIÓN, ESTADO, CUOTA (hito e importe) |
| Revisar | Lateral | panel Lateral `V4 DECISIÓN` | Párrafo de consecuencias → [barra de acciones](../componentes/barra-acciones.md) Decisión: Peligro "Rechazar pago" + Primario "Aprobar pago" |
| Datos | Principal | `<form>` · panel `D1 DATOS PARA PAGAR` | Ayuda de los cuatro métodos una sola vez, bajo el título del panel. Un `<fieldset>` por método (TRANSFERENCIA BANCARIA, YAPE, PLIN, TARJETA) y uno más, CONTACTO DEL ESTUDIO, con Área MENSAJE DE CONTACTO. La `<legend>` manda sobre la etiqueta del campo: `fuente-familia-titulo`, `fuente-peso-titulo`, `fuente-tamano-base`; entre grupos, regla `borde-grosor-fino` y `espacio-5`. Método: Área + casilla "Activo: los clientes pueden pagar así" → Primario "Guardar datos para pagar" (una acción: sin barra) |

**Rechazar** sigue la decisión de cancelar en [mis reservas](RF-04-mis-reservas.md#cancelar): V4 se sustituye por `RECHAZAR PAGO DE {folio}` con MOTIVO DEL RECHAZO (Área), "Motivos frecuentes" (tres [botones](../componentes/boton.md) Secundario que escriben el texto en el área y le pasan el foco: "El monto no coincide" · "Operación no encontrada" · "Captura ilegible"), consecuencias y la barra: "Volver" (Secundario) + Peligro "Rechazar pago" (sin Primario: la única salida adelante es rechazar). El motivo obligatorio es la confirmación ([formularios](../patrones/formularios.md#prevención-de-errores)).

**Aprobar va en un clic** (decisión del brief): la ficha ya es la revisión (captura y datos a la vista), el botón está en la ficha de ese pago y el párrafo de V4 dice antes qué pasa y que no se deshace. Una página de confirmación por cada pago diario solo añade un clic.

**Captura caducada:** la URL dura pocos minutos. Al pasar `expira_en`, o si la imagen no carga, V1 muestra "La vista de la captura caducó." + Secundario "Cargar captura de nuevo" (pide otra URL) y oculta "Abrir en una pestaña nueva".

Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md), [formularios](../patrones/formularios.md). Adaptabilidad: < `punto-quiebre-escritorio`, la tabla pasa a tarjetas y los laterales van **después** del principal (primero se mira la captura, luego se decide). La barra de V4 usa la variante Móvil a cualquier ancho: en un panel Lateral dos botones grandes no caben en fila ([barra de acciones](../componentes/barra-acciones.md#variantes)). Los folios no se parten (`white-space: nowrap`) en títulos y descripciones. Sin búsqueda ni paginación: el contrato no las ofrece.

## Estados

| Vista | Vacío | Carga | Error al cargar | Éxito |
|---|---|---|---|---|
| Lista | Por validar: "No hay pagos por validar" + "Cuando un cliente registre un pago, aparecerá aquí." Sin acción. Aprobados / rechazados: "Aún no hay pagos aprobados." / "… rechazados." + "Ver pagos por validar" (Secundario) | Panel "Cargando…", `aria-busy` | Aviso Error en el panel + "Reintentar" | `pago-aprobado` "Pago aprobado. La cuota quedó pagada y avisamos al cliente." · `reserva-confirmada` "Pago aprobado. La reserva quedó confirmada y avisamos al cliente." · `pago-rechazado` "Pago rechazado. Avisamos al cliente con el motivo." · `datos-actualizados` "Datos para pagar guardados. Los clientes ya ven los nuevos." |
| Revisar | — | Ídem | 404: panel `[404] PAGO NO ENCONTRADO` con aviso Información "No encontramos este pago." + "Volver a pagos" (como el 404 de [mis reservas](RF-04-mis-reservas.md#estados) y de [registrar pago](RF-05-registrar-pago.md#estados)); vale también para un `id` que no es UUID. Captura 503: en V1, aviso Error "No pudimos cargar la captura." + "Reintentar"; la decisión sigue disponible (puede comprobar la operación en el banco) | Vuelve a la lista |
| Revisar, ya validado | V4 se sustituye por [indicador](../componentes/indicador-estado.md) Barra: Correcto "APROBADO" + `validado_en` · Problema "RECHAZADO" + `validado_en` y el motivo debajo | — | — | — |
| Datos | — | Ídem | Ídem | Vuelve a la lista |

| Al enviar | Forma y texto |
|---|---|
| Enviando | Botón en Carga ("Aprobando…", "Rechazando…", "Guardando…"); los demás controles de la vista deshabilitados |
| 409 `pago_ya_validado` | Aviso Información "Este pago ya se validó, quizá desde otra sesión." y la ficha se recarga con el resultado (V4 pasa a indicador) |
| 422 en rechazar | Bajo el campo: "Escribe el motivo del rechazo." · "El motivo admite hasta 300 caracteres." |
| 422 en datos | Bajo el campo de `detalles.campo` si lo trae; si no, aviso Error con el `mensaje`. Datos conservados |
| 401 · 403 · 503 · red · no JSON · sin JS | Como en [solicitudes](RF-01-solicitudes.md#estados) (403: "Esta sección es solo para el Administrador."). Al enviar, sin "Reintentar": el botón sigue disponible |

Aviso fijo en Datos si ningún método queda activo: Aviso "Ningún método está activo: los clientes no podrán registrar pagos." Claves `aviso` (lista cerrada): las cuatro de la tabla; se elige `reserva-confirmada` si la respuesta trae `reserva.estado = confirmada` y la cuota era `al_reservar`. Tras aprobar o rechazar, la isla avisa a la navegación para bajar el contador (evento `bugalu:pagos-por-validar`).

Permisos: solo `administrador`; personal y clientes no ven PAGOS y, por URL, ven el 403.

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Lista | Inicio / Pagos · `[A6] COBROS / PAGOS` | PAGOS | Pagos que registraron los clientes. Revisa la captura y aprueba o rechaza cada uno. |
| Revisar | Inicio / Pagos / {folio} | REVISAR PAGO | {cliente} · {cuota} de la reserva {folio} |
| Datos | Inicio / Pagos / Datos para pagar · `[A7] COBROS / DATOS PARA PAGAR` | DATOS PARA PAGAR | Lo que ven los clientes al pagar y en el correo de su reserva. |

Consecuencias en V4: "Al aprobar, la cuota queda pagada{, la reserva se confirma} y avisamos al cliente. No se puede deshacer." (el inciso solo si es `al_reservar` de una `Pre-reservada`). Al rechazar: "La cuota sigue pendiente y el cliente verá el motivo. Si la reserva está pre-reservada, vuelve a tener al menos 1 hora para pagar." Ayudas: motivo "El cliente lo verá en su reserva y en el correo. Di qué corregir."; datos (una vez, en D1) "Banco, cuenta, CCI, número de Yape o Plin y titular. Se muestra tal cual escribas."; contacto "Dónde escribirte cuando el cliente no puede pagar o cancelar por su cuenta. Hasta 500 caracteres." (error: "El contacto admite hasta 500 caracteres."). Éxito de `datos-actualizados`: también cubre el contacto Columnas: RESERVA · CLIENTE · MÉTODO · MONTO · OPERACIÓN · REGISTRADO / VALIDADO. Captura: `alt="Captura del comprobante de {cliente}, {método}, {monto}"`.

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; tablas con `<caption>` y el folio como `<th scope="row">`; NO COINCIDE dice el hecho en texto, no solo color.
- Filtros: enlaces con `aria-current="true"`. Datos: cada método es `<fieldset>` + `<legend>`.
- Orden de foco en Revisar: "Abrir en una pestaña nueva" → folio de V3 → "Rechazar pago" → "Aprobar pago". Al abrir el rechazo, el foco va a su título; "Volver" lo devuelve a "Rechazar pago".
- Región `role="status"` estable: anuncia la carga ("3 pagos por validar") y cada resultado; al fallar un envío, el foco va al aviso.
- El enlace a la pestaña nueva lo dice en su texto.

## Pendientes

- **dev-backend:** orden de aprobados y rechazados (propuesta: `validado_en` descendente) y forma del 422 de `PUT /instrucciones-pago` (método activo sin texto, largo máximo del texto).
- **dev-backend:** `GET /pagos/{id}/captura` no dice si es imagen o PDF; propuesta: añadir `tipo` (`imagen` | `pdf`). Sin él, la isla lo deduce de la extensión de la ruta firmada.
