---
id: pantalla-rf-03-franjas
titulo: Pantalla — Franjas, cierres y parámetros de reserva (Administrador)
estado: borrador
depende_de: [RF-03, ADR-009, diseno-brief, patron-estructura-app, patron-formularios, patron-tablas-y-tableros, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-boton, comp-aviso, comp-etiqueta-tecnica]
---

# Franjas, cierres y parámetros

| Campo | Valor |
|---|---|
| Requerimiento | [RF-03](../../03-requerimientos/RF-03.md): CA-02, CA-03, CA-04, CA-07, CA-09 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/franjas?semana=AAAA-Www` y `/app/franjas/parametros`. URL: `semana` (por defecto, la actual), `aviso` |
| Isla | `<bugalu-franjas vista="semana\|parametros">` (nueva) |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)) |

## Recorrido

1. El Administrador entra por "FRANJAS" (`calendar-cog`), que solo se pinta para `administrador`. Ve la semana de `semana` y se mueve con "Semana anterior" / "Semana siguiente".
2. **Semana sin franjas:** el editor llega relleno con la plantilla sugerida (la última semana publicada, desplazada). La ajusta día a día y pulsa "Publicar franjas".
3. **Semana con franjas:** ve las publicadas; retira las que no tienen reservas o abre horas extra añadiendo franjas en el editor (que llega vacío) y publicándolas.
4. **Cierres:** registra un día entero u horas con motivo; si hay reservas vigentes dentro, se le listan para resolverlas antes.
5. "Parámetros de reserva" lleva a `/app/franjas/parametros`: plazos de pago y anticipación; al guardar se queda en la vista con el aviso.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Semana | `semana` (ISO, lunes a domingo, hora de Lima) | "SEMANA DEL 16 AL 22 NOV 2026" |
| Sala | `GET /salas` | Una: implícita. Varias: [campo](../componentes/campo.md) Selector SALA |
| Publicadas | `GET /disponibilidad?sala=&desde=&hasta=` (con sesión de Administrador) → `franjas[].{id, inicio, fin}` | Día (`MAR 18 NOV`), `HH:mm–HH:mm` |
| Reservas por franja | `ocupados[].detalle` dentro de la franja | "2 reservas" / "—" |
| Plantilla sugerida | `GET /franjas/sugerencia?sala=&semana=` → `[{inicio, fin}]` | Filas del editor |
| Publicar | `POST /franjas {id_sala, franjas: [{inicio, fin}]}` → 201 | Solo filas completas. HASTA 00:00 = medianoche |
| Retirar | `DELETE /franjas/{id}` → 204 | — |
| Cierres de la semana | `cierres[].{inicio, fin, motivo}` | Fecha, `HH:mm–HH:mm` o "Todo el día", motivo tal cual |
| Registrar cierre | `POST /cierres {id_sala, inicio, fin, motivo}` → 201 `Cierre` | FECHA (`date`), TODO EL DÍA ([casilla](../componentes/casilla.md), marcada), DESDE y HASTA (`time`, solo si se desmarca), MOTIVO (texto, obligatorio) |
| Quitar cierre | `DELETE /cierres/{id}` → 204 | Ver Pendientes |
| Reservas afectadas | Cuerpo del 409 `cierre_con_reservas` | `folio` · `D MMM, HH:mm` · cliente; enlace a su [detalle](RF-04-mis-reservas.md#detalle) |
| Parámetros | `GET /parametros` / `PATCH /parametros` | `dias_limite_pago`, `horas_limite_pago`, `anticipacion_minima_horas`, `anticipacion_maxima_semanas`: `type="number"`, `min="1"`, `step="1"`, obligatorios |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Ambas | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción; ranura `acciones`: "Parámetros de reserva" / "Volver a franjas" ([botón](../componentes/boton.md) Secundario como enlace) |
| Semana | Controles | La barra del periodo del [calendario](../componentes/calendario.md#anatomía) (mismo marcado y clases, alto `medida-control-tactil`, iconos `chevron-left` / `chevron-right`) | Título de la semana encima ([formato](RF-03-calendario.md#datos)); debajo "Semana anterior" · "Esta semana" · "Semana siguiente", en ese orden |
| Semana | Principal | [panel](../componentes/panel.md) `F1 PUBLICADAS` + [tabla](../componentes/tabla.md) Directorio | DÍA · HORARIO · RESERVAS · "Retirar franja" ([botón](../componentes/boton.md) Peligro) |
| Semana | Principal | panel `F2 PUBLICAR FRANJAS` | Un `<fieldset>` por día ("LUNES 16 NOV"); por franja, DESDE y HASTA ([campo](../componentes/campo.md) `time`, en fila) + "Quitar" (Secundario de solo icono `x`); "Añadir franja" (Secundario) al pie de cada día; cierra con Primario "Publicar franjas" |
| Semana | Lateral | panel Lateral `F3 CIERRES` | Tabla de cierres de la semana (en el lateral, siempre como tarjetas: [tabla](../componentes/tabla.md#adaptabilidad)) + formulario de cierre, separado de la tabla por `espacio-5`, con Secundario "Registrar cierre" |
| Parámetros | Principal | panel `P1 PLAZO PARA PAGAR` y `P2 ANTICIPACIÓN` | Dos campos cada uno; Primario "Guardar parámetros" al final (sin [barra](../componentes/barra-acciones.md#cuándo-se-usa)) |

Patrones: [formularios](../patrones/formularios.md), [tablas y tableros](../patrones/tablas-y-tableros.md). Adaptabilidad: < `punto-quiebre-escritorio`, F3 pasa debajo y las tablas a tarjetas.

**Decisión del brief:** retirar una franja y quitar un cierre no piden página de confirmación: solo se puede sin reservas y se deshace publicando o cerrando otra vez. Con reservas, "Retirar franja" se muestra deshabilitado (`aria-disabled`) con el motivo "Tiene reservas vigentes" ([permisos](../patrones/estados-sistema.md#permisos)).

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| F1 | Sin franjas | Vacío: "No hay franjas publicadas esta semana" + "Abajo tienes una propuesta: edítala y publícala." Sin acción (la primaria es la del editor) |
| F2 | Con plantilla | [Aviso](../componentes/aviso.md) Información "Te proponemos la última semana publicada. Cambia lo que haga falta antes de publicar." |
| F2 | Sugerencia vacía | Aviso Información "No hay una semana anterior que copiar. Añade las franjas de cada día." |
| F2 | Semana ya publicada | Editor sin filas; ayuda "Para abrir horas extra, añade franjas y publícalas." |
| F2 | Validación al enviar | Error bajo el campo: "Elige la hora de inicio." · "La hora de fin debe ser posterior a la de inicio." · "Usa horas en punto o y media." · "Se cruza con la franja de 10:00–14:00 del mismo día." Aviso resumen "Revisa 2 franjas" con enlaces |
| F2 | 409 `franja_solapada` | Aviso Error "Una de las franjas se cruza con otra ya publicada. Revisa las horas y vuelve a publicar." Filas conservadas |
| F2 | Éxito | Recarga F1; aviso Éxito "Franjas publicadas. Ya se ven en el calendario." |
| F1 | Éxito al retirar | Aviso Éxito "Franja retirada." y F1 recargada |
| F1 | 409 `franja_con_reservas` | Aviso Error "Esta franja tiene reservas vigentes. Cancélalas o espera a que terminen antes de retirarla." |
| F3 | Sin cierres | "No hay cierres esta semana." |
| F3 | 409 `cierre_con_reservas` | Aviso Error "No puedes cerrar ese horario: tiene 2 reservas vigentes. Resuélvelas antes de cerrarlo." + `<ul>` de las reservas, cada una enlazada a su detalle. Datos conservados |
| F3 | Validación | "Elige la fecha." · "Escribe el motivo; lo verán los clientes en el calendario." · horas como en F2 |
| F3 | Éxito | Aviso Éxito "Cierre registrado." / "Cierre quitado." |
| Parámetros | Validación (también 422) | "Escribe un número entero mayor que 0." bajo el campo |
| Parámetros | Éxito | Aviso Éxito "Parámetros guardados. La anticipación ya vale en el calendario; los plazos de pago, en las reservas nuevas." |
| Carga | — | Cada panel con "Cargando…", `aria-busy`; enviando: botón en Carga ("Publicando…", "Retirando…", "Registrando…", "Guardando…") y los demás envíos de la vista deshabilitados |
| Todas | 401 | Aviso "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=` con la vista) |
| Todas | 403 | En lugar de la vista: `[403] SIN PERMISO` "Esta sección es solo para el Administrador." + "Volver al inicio" |
| Todas | 404 (franja o cierre ya no existe) | Aviso Información "Esa franja ya no existe. Actualizamos la semana." y se recarga |
| Todas | 422 `rango_invalido` / `semana` inválida | Aviso Información "La semana del enlace no es válida. Te mostramos esta semana." |
| Todas | 503 · red caída · no JSON | "El servicio no responde. Inténtalo de nuevo en unos minutos." · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal. Inténtalo de nuevo." Al cargar con "Reintentar"; al enviar, sin él y con los datos conservados |
| Todas | Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Semana | Inicio / Franjas · `[A3] SALA / FRANJAS` | FRANJAS DE SALA | Publica cuándo se puede reservar la sala, semana a semana, y cierra días u horas. |
| Parámetros | Inicio / Franjas / Parámetros · `[A4] SALA / PARÁMETROS` | PARÁMETROS DE RESERVA | Cuánto tiempo tiene el cliente para pagar, con cuánta anticipación puede reservar y qué pasa si cancela o reprograma. |

Etiquetas y ayudas ([RN-17](../../02-dominio/reglas-negocio.md), [RN-18](../../02-dominio/reglas-negocio.md)): DÍAS ANTES DEL INICIO "Si reserva con más de estos días, puede pagar hasta este número de días antes de la sesión." · HORAS DESDE LA SOLICITUD "Si reserva con menos días, tiene estas horas para pagar." · ANTICIPACIÓN MÍNIMA (HORAS) "Lo más tarde que se puede reservar antes del inicio." · ANTICIPACIÓN MÁXIMA (SEMANAS) "Lo más lejos que se puede reservar." · MOTIVO "p. ej. Feriado o Mantenimiento. Lo verán los clientes." P3 ([ADR-015](../../00-proyecto/decisiones/ADR-015-cancelacion-conservacion-y-correcciones.md), revisión visual TAREA-RF20-6): ADELANTO PARA CONFIRMAR (%) "Parte del total que se paga para confirmar la reserva." · LÍMITE DEL NIVEL 1 (HORAS) "Con más horas de aviso, la cancelación o reprogramación no tiene cargo." · LÍMITE DEL NIVEL 2 (HORAS) "Entre este límite y el del nivel 1 se aplica la penalización. Debe ser menor que el nivel 1." · PENALIZACIÓN DEL NIVEL 2 (%) "Parte del valor de la reserva que se retiene en el nivel 2." · TOLERANCIA DE INASISTENCIA (MIN) "Minutos de espera antes de contar una inasistencia." · VIGENCIA DEL CRÉDITO (DÍAS) "Cuánto dura el crédito que deja una reserva cancelada o reprogramada." · REPROGRAMACIONES DEL NIVEL 1 "Cuántas veces se puede reprogramar sin cargo." · REPROGRAMACIONES DEL NIVEL 2 "Cuántas veces se puede reprogramar con penalización." Acciones con objeto en el nombre accesible: "Retirar franja del martes 18 de 10:00 a 14:00", "Quitar franja de 10:00 a 14:00 del lunes", "Añadir franja al lunes", "Quitar cierre del 25 dic".

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; cada día del editor, `<fieldset>` + `<legend>` con el día completo; cada fila de franja es un grupo con las etiquetas DESDE y HASTA visibles.
- Orden de foco: encabezado → periodo → F1 → F2 (día a día) → "Publicar franjas" → F3. Al añadir una franja, el foco va a su DESDE; al quitarla, a "Añadir franja" de ese día.
- Región `role="status"` estable de la isla: anuncia la carga ("6 franjas publicadas esta semana") y cada resultado; al fallar un envío, el foco va al aviso.

## Pendientes

- **leader / dev-backend:** `Disponibilidad.cierres` no trae `id`, y sin él no se puede llamar a `DELETE /cierres/{id}`; proponemos añadirlo. Nombre de los campos de las reservas en el cuerpo del 409 `cierre_con_reservas` (propuesta: `detalles.reservas[].{id, folio, inicio, cliente}`).
- **leader:** destino FRANJAS (`calendar-cog`); registrar `<bugalu-franjas>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
- **Ampliada por RF-20:** panel `P3 CANCELACIÓN Y ADELANTO` y revisión con confirmación escrita de los parámetros sensibles ([cambios sensibles](RF-20-cambios-sensibles.md#integración-sin-rehacer-las-pantallas)).
