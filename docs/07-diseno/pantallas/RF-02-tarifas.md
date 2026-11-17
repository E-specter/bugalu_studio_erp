---
id: pantalla-rf-02-tarifas
titulo: Pantalla — Tarifas, especialistas, recargos y feriados (Administrador)
estado: borrador
depende_de: [RF-02, ADR-009, diseno-brief, patron-estructura-app, patron-formularios, patron-tablas-y-tableros, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-boton, comp-aviso, comp-etiqueta-tecnica]
---

# Tarifas

| Campo | Valor |
|---|---|
| Requerimiento | [RF-02](../../03-requerimientos/RF-02.md): CA-01 a CA-04 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/tarifas`, `/app/tarifas/servicio?id=`, `/app/tarifas/especialista?id=`, `/app/tarifas/recargos?anio=`. URL: `id`, `anio` (por defecto, el actual), `aviso` |
| Isla | `<bugalu-tarifas vista="lista\|servicio\|especialista\|recargos">` (nueva) |
| Origen Figma | Ninguno; tablas del [directorio](../patrones/tablas-y-tableros.md#directorio-tabla) (`161:842`) |

## Recorrido

1. El Administrador entra por "TARIFAS" (`tag`), que solo se pinta para `administrador`. Ve servicios y especialistas con sus tarifas.
2. "Editar {servicio}": cambia la tarifa por hora, los especialistas por defecto y si está activo → vuelve con `?aviso=servicio-actualizado`.
3. "Editar {especialista}": cambia monto fijo, monto variable, unidad y si está activo → vuelve con `?aviso=especialista-actualizado`.
4. "Recargos y feriados": ajusta los porcentajes de noche, fin de semana y feriado y la lista de feriados del año.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Servicios | `GET /servicios` → `[Servicio]` | `nombre`; `categoria` en [etiqueta](../componentes/etiqueta-tecnica.md) Neutra (GRABACIÓN, ENSAYO, LIVE, POSPRODUCCIÓN); `ocupa_sala` "Sí" / "No (va por proyecto)"; `tarifa_hora` y `monto_fijo` `S/ 120,00`; `activo` en etiqueta Éxito ACTIVO / Neutra INACTIVO |
| Por defecto | `especialistas_por_defecto` → nombres de `GET /especialistas` | Separados por comas, o "—" |
| Editar servicio | La de la lista con ese `id` → `PATCH /servicios/{id} {tarifa_hora?, monto_fijo?, activo?, especialistas_por_defecto?}` | TARIFA POR HORA (S/) y MONTO FIJO (S/) ([campo](../componentes/campo.md) importe); ESPECIALISTAS POR DEFECTO ([casillas](../componentes/casilla.md)); ACTIVO (casilla). Categoría y sala, solo lectura |
| Especialistas | `GET /especialistas` → `[Especialista]` | `nombre`; `monto_fijo` y `monto_variable` `S/ 25,00`; `unidad` "por hora" / "por media hora"; `activo` como arriba |
| Editar especialista | `PATCH /especialistas/{id} {monto_fijo?, monto_variable?, unidad?, activo?}` | MONTO FIJO (S/) y MONTO VARIABLE (S/) (importe, en fila); UNIDAD (casilla Radio: Por hora · Por media hora); ACTIVO |
| Recargos | `GET /recargos` / `PUT /recargos` → `{noche: {porcentaje, desde, hasta}, fin_de_semana: {porcentaje}, feriado: {porcentaje}}` | Porcentaje: `type="number"`, `min="0"`, `step="0.01"`, sufijo "%" en la etiqueta; el valor se pinta como número (`25`, `12.5`), nunca con ceros de relleno ("25.00"); DESDE y HASTA de noche: `time`, hora de Lima |
| Feriados | `GET /feriados?anio=` → `[Feriado]` | `D MMM AAAA` + `nombre`, por fecha |
| Añadir / quitar feriado | `POST /feriados {fecha, nombre}` → 201; `DELETE /feriados/{fecha}` → 204 | FECHA (`date`) y NOMBRE (texto), obligatorios |

Importes: el campo acepta `125,5` o `125.50`; la isla envía texto decimal con punto y dos decimales (`"125.50"`) y rechaza negativos ([convenciones](../../01-arquitectura/convenciones.md#api)).

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Todas | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título y descripción; en Lista, "Recargos y feriados" ([botón](../componentes/boton.md) Secundario como enlace) en la ranura `acciones` |
| Lista | Principal | [panel](../componentes/panel.md) `T1 SERVICIOS` + [tabla](../componentes/tabla.md) Directorio | SERVICIO · CATEGORÍA · OCUPA SALA · TARIFA POR HORA · MONTO FIJO · POR DEFECTO · ESTADO · "Editar {servicio}" |
| Lista | Principal | panel `T2 ESPECIALISTAS` + tabla Directorio | ESPECIALISTA · FIJO · VARIABLE · UNIDAD · ESTADO · "Editar {especialista}" |
| Servicio | Principal + lateral | panel `S1 SERVICIO` (`<dl>`: nombre, categoría, ocupa sala) + panel Lateral `S2 TARIFA` | Campos y Primario "Guardar servicio" |
| Especialista | Principal + lateral | panel `E1 ESPECIALISTA` (`<dl>`: nombre) + panel Lateral `E2 TARIFA` | Campos y Primario "Guardar especialista" |
| Recargos | Principal | panel `R1 RECARGOS POR HORARIO` | NOCHE (% + DESDE + HASTA en fila), FIN DE SEMANA (%), FERIADO (%); Primario "Guardar recargos" |
| Recargos | Lateral | panel Lateral `R2 FERIADOS {anio}` | Enlaces "{anio − 1}" / "{anio + 1}"; tabla (siempre tarjetas en el lateral: [tabla](../componentes/tabla.md#adaptabilidad)) FECHA · NOMBRE · "Quitar feriado" (Secundario); formulario FECHA + NOMBRE + Secundario "Añadir feriado" |

Patrones: [formularios](../patrones/formularios.md), [tablas y tableros](../patrones/tablas-y-tableros.md). Una sola acción por formulario: sin [barra de acciones](../componentes/barra-acciones.md#cuándo-se-usa). Adaptabilidad: < `punto-quiebre-escritorio`, tablas a tarjetas y laterales debajo. Sin crear ni borrar servicios ni especialistas: el contrato solo los edita (desactivar es el borrado).

**Decisión del brief:** guardar tarifas no pide confirmación (se corrige editando otra vez), pero el panel de tarifa avisa a quién afecta (Copy); quitar un feriado tampoco (se vuelve a añadir).

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| T1, T2 | Vacío | "Aún no hay servicios cargados." / "Aún no hay especialistas cargados." + "Se cargan con la base de datos inicial; avisa al equipo técnico." Sin acción |
| R2 | Sin feriados en el año | "No hay feriados en {anio}." El formulario sigue disponible |
| Servicio, especialista | `id` desconocido o 404 | Aviso Información "No encontramos este servicio." / "… este especialista." + "Volver a tarifas" |
| Formularios | Validación (al salir y al enviar; 422 por campo) | "Escribe un importe de 0 o más, con hasta dos decimales, como 120,50." · "Escribe un porcentaje de 0 o más." · "Elige la hora." · "Elige la fecha." · "Escribe el nombre del feriado." Aviso resumen con enlaces |
| R2 | 409 al añadir | Error en FECHA "Ya hay un feriado en esa fecha." |
| Éxito | `?aviso=` en Lista / en la vista | `servicio-actualizado` "Servicio actualizado. El precio nuevo se aplica a las simulaciones y reservas desde ahora." · `especialista-actualizado` "Especialista actualizado. …" (igual) · en Recargos: "Recargos guardados." / "Feriado añadido." / "Feriado quitado." |
| Carga | — | Panel con "Cargando…", `aria-busy`; enviando: botón en Carga ("Guardando…", "Añadiendo…", "Quitando…") y los otros envíos de la vista deshabilitados |
| Todas | 401 | Aviso "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=` con la vista) |
| Todas | 403 | En lugar de la vista: `[403] SIN PERMISO` "Esta sección es solo para el Administrador." + "Volver al inicio" |
| Todas | 503 · red caída · no JSON | "El servicio no responde. Inténtalo de nuevo en unos minutos." · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal. Inténtalo de nuevo." Al cargar con "Reintentar"; al enviar, sin él y con los datos conservados |
| Todas | Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Claves `aviso` (lista cerrada): `servicio-actualizado`, `especialista-actualizado`. Permisos: solo `administrador`; las lecturas son públicas, pero las vistas no se muestran a otros roles (403 de la API al guardar).

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Lista | Inicio / Tarifas · `[A5] CATÁLOGO / TARIFAS` | TARIFAS | Lo que cuesta cada servicio y cada especialista. Con esto se calcula el precio de las reservas. |
| Servicio | Inicio / Tarifas / {servicio} | EDITAR SERVICIO | Tarifa por hora y quién va incluido en {servicio}. |
| Especialista | Inicio / Tarifas / {especialista} | EDITAR ESPECIALISTA | Cuánto suma {especialista} a cada reserva. |
| Recargos | Inicio / Tarifas / Recargos | RECARGOS Y FERIADOS | Porcentaje extra por horario y días feriados del año. |

Ayudas (supuestos de [ADR-009](../../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)): TARIFA POR HORA sin ayuda (la etiqueta basta). MONTO FIJO (servicio y especialista) "Se cobra una vez por reserva." · MONTO VARIABLE "Se cobra por cada hora o media hora de la reserva, según la unidad." · ESPECIALISTAS POR DEFECTO "Van incluidos y el cliente no puede quitarlos." · ACTIVO (servicio) "Si lo desactivas, deja de ofrecerse al reservar." · Recargo "Se aplica a la parte variable de cada media hora que cae en ese horario, nunca al monto fijo." · NOCHE, DESDE / HASTA "Puede pasar la medianoche: de 22:00 a 06:00." Aviso Información fijo en S2 y E2: "Los cambios valen para las simulaciones y reservas nuevas; las ya hechas guardan su precio."

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; tablas con `<caption>` y el nombre como `<th scope="row">`. Acciones de fila con objeto: "Editar Grabación de voces", "Quitar feriado del 25 dic".
- Recargos: un `<fieldset>` por tipo (NOCHE, FIN DE SEMANA, FERIADO) con su `<legend>`; UNIDAD y ESPECIALISTAS POR DEFECTO, `<fieldset>` con `<legend>`.
- Región `role="status"` estable de la isla para la carga y los resultados; al fallar un envío, el foco va al aviso.

## Pendientes

- **Usuario (vía leader):** confirmar los supuestos de ADR-009 que reflejan las ayudas: unidad por especialista, monto fijo una vez por reserva, recargo solo sobre la parte variable.
- **leader:** destino TARIFAS (`tag`); registrar `<bugalu-tarifas>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
- **Ampliada por RF-20:** los cambios de importes, unidad y recargos pasan por la revisión con confirmación escrita, y Lista suma "Impuestos" ([cambios sensibles](RF-20-cambios-sensibles.md#integración-sin-rehacer-las-pantallas)).
