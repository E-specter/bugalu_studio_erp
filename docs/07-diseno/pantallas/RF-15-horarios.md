---
id: pantalla-rf-15-horarios
titulo: Pantalla — Horarios del profesional ("Mis horarios", etapa A)
estado: borrador
depende_de: [RF-15, RF-03, pantalla-rf-03-franjas, pantalla-rf-15-ficha, diseno-brief, patron-estructura-app, patron-formularios, patron-tablas-y-tableros, patron-estados-sistema, comp-calendario, comp-tabla, comp-panel, comp-campo, comp-boton, comp-aviso]
---

# Horarios del profesional

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-05 (publicar, sugerencia, excepciones, 409), CA-16, CA-17 (Mis horarios; el Administrador, por el profesional) |
| Actores | Profesional artístico (los suyos); Administrador (los de cualquiera) |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | Profesional: `/app/horarios/?semana=AAAA-Www`. Administrador: `/app/asesorias/horarios?id=&semana=`. URL: `semana` (por defecto, la actual), `id` |
| Isla | `<bugalu-profesional vista="horarios">` (la de la [ficha](RF-15-ficha.md)) |

**Decisión del brief:** es el editor de [franjas](RF-03-franjas.md) con otro dueño: mismo recorrido, misma barra de semana, misma tabla de publicados y el mismo editor por día. Quien sabe publicar franjas sabe publicar horarios, y `dev-frontend` reutiliza el marcado. No hay cierres: una excepción es retirar un bloque o publicar uno extra (CA-05).

## Recorrido

1. El profesional entra por HORARIOS (`calendar-cog`); el Administrador, por "Horarios de {nombre}" en la [lista de profesionales](RF-15-administracion.md#profesionales) o en su ficha. Ve la semana de `semana` y se mueve con la barra del periodo.
2. **Semana sin bloques:** el editor llega relleno con la sugerencia (la última semana publicada, desplazada). La ajusta y pulsa "Publicar horarios".
3. **Semana con bloques:** ve los publicados; retira los que no tienen asesorías o publica bloques extra en el editor, que llega vacío.
4. Para acortar o mover un bloque, lo retira y publica el nuevo.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Profesional | `GET /perfil` (propio) o `GET /profesionales/{id}` (Administrador) | Nombre en la ruta del Administrador |
| Semana | `semana` (ISO, lunes a domingo, hora de Lima) | "SEMANA DEL 16 AL 22 NOV 2026" ([formato](RF-03-calendario.md#datos)) |
| Publicados | `GET /profesionales/{id}/disponibilidad?desde=&hasta=` → `horarios[].{id, inicio, fin}` (el `id`, ver Pendientes) | Día `MAR 18 NOV`, `HH:mm–HH:mm` |
| Asesorías por bloque | `ocupados[]` que caen dentro del bloque | "2 asesorías" / "—" |
| Sugerencia | `GET /profesionales/{id}/horarios/sugerencia?semana=` → `[{inicio, fin}]` | Filas del editor; se descartan las que ya empezaron |
| Publicar | `POST /profesionales/{id}/horarios {horarios: [{inicio, fin}]}` (1 a 200) → 201 `[Horario]` | Solo filas completas; HASTA 00:00 = medianoche; ISO 8601 con `-05:00` |
| Retirar | `DELETE /profesionales/{id}/horarios/{id_horario}` → 204 | — |
| Asesorías que impiden retirar | `detalles.asesorias` del 409 `horario_con_asesorias` | `folio` · `D MMM, HH:mm` |
| Publicación del perfil | `Profesional.publicado` | Aviso si es `false` (Estados) |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción; Administrador: "Volver a la ficha de {nombre}" ([botón](../componentes/boton.md) Secundario como enlace) en `acciones` |
| Controles | La barra del periodo del [calendario](../componentes/calendario.md#anatomía), como en [franjas](RF-03-franjas.md#composición) | Título de la semana; "Semana anterior" · "Esta semana" · "Semana siguiente" |
| Principal | [panel](../componentes/panel.md) `H1 PUBLICADOS` + [tabla](../componentes/tabla.md) Directorio | DÍA · HORARIO · ASESORÍAS · "Retirar bloque" ([botón](../componentes/boton.md) Peligro). Bloque que ya empezó: sin botón y "Pasado" en ASESORÍAS |
| Principal | panel `H2 PUBLICAR HORARIOS` | Un `<fieldset>` por día desde hoy ("MARTES 18 NOV"); por bloque, DESDE y HASTA ([campo](../componentes/campo.md) `time`, `step="1800"`, en fila) + "Quitar" (Secundario de solo icono `x`); "Añadir bloque" al pie de cada día; cierra con Primario "Publicar horarios" |

Una sola columna (sin lateral): no hay cierres. Patrones: [formularios](../patrones/formularios.md) (filas repetibles), [tablas y tableros](../patrones/tablas-y-tableros.md). Adaptabilidad: < `punto-quiebre-escritorio`, la tabla pasa a tarjetas.

Retirar no pide confirmación (decisión de [franjas](RF-03-franjas.md#composición)): solo se puede sin asesorías y se deshace publicando otra vez. Con asesorías dentro, "Retirar bloque" va con `aria-disabled="true"` y el motivo visible "Tiene asesorías agendadas" ([permisos](../patrones/estados-sistema.md#permisos)).

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Vista | Perfil sin publicar | [Aviso](../componentes/aviso.md) Información "Tu perfil aún no es público: los artistas no verán estos horarios hasta que lo sea." + "Ver qué falta" (a la [ficha](RF-15-ficha.md)). Administrador: "El perfil de {nombre} aún no es público…" |
| H1 | Sin bloques | Vacío: "No hay horarios publicados esta semana" + "Abajo tienes una propuesta: edítala y publícala." Sin acción |
| H2 | Con sugerencia | Aviso Información "Te proponemos tu última semana publicada. Cambia lo que haga falta antes de publicar." |
| H2 | Sugerencia vacía | Aviso Información "No hay una semana anterior que copiar. Añade los bloques de cada día." |
| H2 | Semana ya publicada | Editor sin filas; ayuda "Para sumar horas, añade bloques y publícalos." |
| H2 | Semana pasada | Sin editor; texto "Esta semana ya pasó." |
| H2 | Validación al enviar | Bajo el campo: "Elige la hora de inicio." · "La hora de fin debe ser posterior a la de inicio." · "Usa horas en punto o y media." · "Esa hora ya pasó. Elige una hora futura." · "Se cruza con el bloque de 10:00–12:00 del mismo día." Aviso resumen "Revisa {n} bloques" con enlaces |
| H2 | 409 `horario_solapado` | Aviso Error "Uno de los bloques se cruza con otro ya publicado. Revisa las horas y vuelve a publicar." Filas conservadas |
| H2 | 422 | Error bajo el campo si es de una fila; si no, aviso Error con el `mensaje` del servidor. Filas conservadas |
| H2 | Éxito | Recarga H1; aviso Éxito "Horarios publicados. Ya se ven en tu perfil." (sin publicar: "Horarios publicados.") |
| H1 | Éxito al retirar | Aviso Éxito "Bloque retirado." y H1 recargado |
| H1 | 409 `horario_con_asesorias` | Aviso Error "Este bloque tiene asesorías agendadas. Pide al Administrador que las cancele o reprograme antes de retirarlo." (Administrador: "…Cancélalas o reprográmalas antes de retirarlo.") + `<ul>` de las asesorías (folio y fecha), cada una enlazada a su [detalle](RF-15-gestion.md) (etapa B). Administrador, etapa B: "Este bloque tiene asesorías agendadas. Cancélalas por el estudio antes de retirarlo: cada cliente elegirá reprogramar o la devolución." |
| Carga | — | Paneles con "Cargando…", `aria-busy`; enviando: botón en Carga ("Publicando…", "Retirando…") y los demás envíos deshabilitados |
| Todas | 401 | Aviso "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=` con la vista) |
| Todas | 403 | En lugar de la vista: `[403] SIN PERMISO` "Esta sección es para los profesionales de asesoría." (ruta del Administrador: "…solo para el Administrador.") + "Volver al inicio" |
| Todas | 404 | Profesional: el de la [ficha](RF-15-ficha.md#estados). Administrador: aviso Información "No encontramos a este profesional." + "Volver a profesionales". Bloque que ya no existe: "Ese bloque ya no existe. Actualizamos la semana." y recarga |
| Todas | `semana` inválida o 422 `rango_invalido` | Aviso Información "La semana del enlace no es válida. Te mostramos esta semana." |
| Todas | 503 · red caída · no JSON | Los textos de [franjas](RF-03-franjas.md#estados): "Reintentar" al cargar; al enviar, sin él y con los datos conservados |
| Todas | Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: el profesional solo llega a los suyos (no hay selector de profesional ni `?id=` en su ruta); la API responde 404 o 403 a lo ajeno (CA-16). Nunca ve de quién son las asesorías: solo cuántas hay.

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Profesional | Inicio / Horarios · `[E2] ASESORÍAS / HORARIOS` | MIS HORARIOS | Publica cuándo pueden agendar contigo, semana a semana. Los clientes eligen dentro de estos bloques. |
| Administrador | Inicio / Asesorías / {nombre} / Horarios | HORARIOS DE {NOMBRE} | Publica o retira los horarios de {nombre}, semana a semana. |

Ayuda de H2: "Bloques en horas en punto o y media, de al menos 30 minutos y sin cruzarse. Horario de Lima." Acciones con objeto en el nombre accesible: "Retirar bloque del martes 18 de 10:00 a 12:00", "Quitar bloque de 10:00 a 12:00 del lunes", "Añadir bloque al lunes".

## Accesibilidad

- Las de [franjas](RF-03-franjas.md#accesibilidad): `<h1>` del encabezado, paneles `<section>` con `<h2>`, cada día `<fieldset>` + `<legend>` con el día completo, DESDE y HASTA con etiqueta visible.
- Orden de foco: encabezado → periodo → H1 → H2 (día a día) → "Publicar horarios". Al añadir, el foco va al DESDE nuevo; al quitar, a "Añadir bloque" de ese día.
- Región `role="status"` estable: "4 bloques publicados esta semana" y cada resultado; al fallar un envío, el foco va al aviso.

## Pendientes

- **Ampliada por RF-15 B:** el 409 `horario_con_asesorias` enlaza cada asesoría a su detalle y cambia el texto del Administrador (arriba).

- **leader / dev-backend:** `DisponibilidadProfesional.horarios[]` no trae `id` y sin él no hay `DELETE`; proponemos añadirlo (como `franjas[].id`). Y que el propio profesional y el Administrador reciban la disponibilidad aunque el perfil no esté publicado (hoy da 404 al público).
- **leader / dev-backend:** forma de `detalles.asesorias` del 409: proponemos `[{id, folio, inicio}]`.
- **leader:** destino HORARIOS (`calendar-cog`, el de FRANJAS) para `profesional`.
