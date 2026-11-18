---
id: pantalla-rf-15-administracion
titulo: Pantalla — Profesionales, especialidades y precios de asesoría (Administrador, etapa A)
estado: borrador
depende_de: [RF-15, RF-01, RF-20, pantalla-rf-01-solicitudes, pantalla-rf-15-ficha, pantalla-rf-15-horarios, pantalla-rf-20-cambios-sensibles, diseno-brief, patron-estructura-app, patron-formularios, patron-tablas-y-tableros, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-avatar, comp-etiqueta-tecnica, comp-boton, comp-aviso]
---

# Profesionales y especialidades (Administrador)

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-01 (asignar rol), CA-02, CA-03 (activo), CA-04 (precios con barreras), CA-05 (horarios por el profesional), CA-17 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/asesorias/` (profesionales), `/app/asesorias/especialidades?editar=`, `/app/asesorias/profesional?id=` (ficha), `/app/asesorias/horarios?id=&semana=` ([horarios](RF-15-horarios.md)). URL: `id`, `editar`, `aviso` |
| Isla | `<bugalu-profesionales vista="lista\|especialidades">` (nueva); ficha y horarios, `<bugalu-profesional>` con `id` ([ficha](RF-15-ficha.md)) |

## Recorrido

1. Entra por ASESORÍAS (`messages-square`), solo para `administrador`. Ve la lista de profesionales.
2. **Sumar un profesional:** "Asignar rol de profesional" lleva a [usuarios](RF-01-solicitudes.md) (`/app/usuarios`); elige la cuenta, marca "Profesional artístico" y guarda. Vuelve aquí con `?aviso=profesional-asignado`: su ficha nació inactiva.
3. **Ficha de un profesional:** "Editar ficha de {nombre}" → activa, fija precios y corrige lo que haga falta → "Guardar ficha". Con precios cambiados pasa antes por la revisión de [cambios sensibles](RF-20-cambios-sensibles.md#flujo-con-barreras).
4. **Horarios:** "Horarios de {nombre}" → [horarios](RF-15-horarios.md) en su ruta de Administrador.
5. **Especialidades:** "Especialidades" (en el encabezado) → crea, renombra, desactiva o reactiva.

## Profesionales

| Dato | Origen | Formato |
|---|---|---|
| Lista | `GET /profesionales` con token (incluye inactivos) → `[ProfesionalResumen]` + `activo`, `publicado` (ver Pendientes) | Por nombre |
| Profesional | `nombre`, `nombre_artistico` | [Avatar](../componentes/avatar.md) Medio con iniciales (sin foto: panel interno) + nombre; artístico debajo, `color-texto-secundario` |
| Especialidades | `especialidades[].nombre` | Separadas por comas, o "Ninguna" |
| 30 MIN · 1 H | `duraciones` | `S/ 80,00` o "—" (no la ofrece) |
| Estado | `activo`, `publicado` | [Etiqueta](../componentes/etiqueta-tecnica.md) Éxito PUBLICADO · Aviso SIN PUBLICAR (activo, le falta especialidad o precio) · Neutra INACTIVO |

Composición: [encabezado](../componentes/encabezado-pantalla.md) App (ranura `acciones`: "Especialidades" y "Asignar rol de profesional", [botones](../componentes/boton.md) Secundario como enlace) → [panel](../componentes/panel.md) `PROFESIONALES` + [tabla](../componentes/tabla.md) Directorio: PROFESIONAL · ESPECIALIDADES · 30 MIN · 1 H · ESTADO · "Editar ficha de {nombre}" y "Horarios de {nombre}" (Secundario como enlace). Sin búsqueda ni filtros: el equipo es pequeño. < `punto-quiebre-escritorio`, tarjetas.

## Asignar el rol (amplía usuarios de RF-01)

En [usuarios](RF-01-solicitudes.md#composición), sin pantalla nueva:

- Filtros: se suma "Profesionales" (`?rol=profesional`) tras "Personal".
- U2 suma la casilla Radio **Profesional artístico**, detalle "Da asesorías y publica sus horarios. Entra con correo y contraseña." Con ella marcada, ESPECIALIDAD se oculta (las de asesoría van en su ficha) y se envía `PATCH /usuarios/{id} {rol: "profesional"}`.
- Éxito al asignar: redirige a `/app/asesorias/?aviso=profesional-asignado`. Quitar el rol: vuelve a Usuarios como hoy.
- 409 `profesional_con_asesorias`: aviso Error "{Nombre} tiene asesorías pendientes o confirmadas. Cancélalas o espera a que terminen antes de quitarle el rol." Datos conservados.

## Ficha de un profesional

La [ficha](RF-15-ficha.md) con `?id=`, con estos cambios:

- Ruta Inicio / Asesorías / {nombre}; título FICHA DE {NOMBRE}; descripción "Activa a {nombre}, fija sus precios y revisa lo que muestra en el directorio." `acciones`: "Horarios de {nombre}".
- Antes de F1, panel `A1 ESTADO Y PRECIOS` (en el mismo `<form>`): ACTIVO ([casilla](../componentes/casilla.md), detalle "Se publica cuando además tiene una especialidad y un precio.") → PRECIO 30 MIN (S/) y PRECIO 1 H (S/) ([campo](../componentes/campo.md) importe, en fila, opcionales; vacío = no ofrece esa duración). Ayuda según `GET /impuestos`: "Lo que paga el cliente, con IGV ({p} %) incluido." o "Sin IGV: el IGV ({p} %) se suma al total."
- F5 PUBLICACIÓN no repite ACTIVO ni PRECIOS (ya son campos); NOMBRE remite a "Cámbialo en Usuarios".
- **Guardar:** sin precios cambiados, un `PATCH` como el del profesional más `activo`. Con precios cambiados, el [flujo con barreras](RF-20-cambios-sensibles.md#flujo-con-barreras): "Calculando impacto…", revisión C1 QUÉ CAMBIA (PRECIO 30 MIN · PRECIO 1 H, importe o "No ofrece"), C2 IMPACTO y C3 CONFIRMAR; al confirmar, el resto va por el `PATCH`. Red de seguridad: un 428 `confirmacion_requerida` abre la misma revisión con `detalles.campos`.
- Avisos fijos en A1: "Los precios valen para las asesorías nuevas; las ya agendadas guardan el suyo." Éxito: "Ficha de {nombre} guardada." y, con precios, "Ver en el registro de cambios".
- Validación: "Escribe un importe mayor que 0, con hasta dos decimales, como 80,00." Activar sin especialidad o sin precio no es error: queda SIN PUBLICAR y el aviso de la ficha dice qué falta.

## Especialidades

| Dato | Origen | Formato |
|---|---|---|
| Catálogo | `GET /especialidades-asesoria?todas=true` → `[Especialidad]` | Por nombre; `activa` en etiqueta Éxito ACTIVA o Neutra INACTIVA |
| Crear | `POST /especialidades-asesoria {nombre}` → 201 | NOMBRE (Texto, `minlength="2"`, `maxlength="60"`) |
| Renombrar · desactivar · activar | `PATCH /especialidades-asesoria/{id} {nombre}` · `{activa: false}` · `{activa: true}` → 200 | — |

Composición: encabezado (`acciones`: "Volver a profesionales") → panel `E1 ESPECIALIDADES` + tabla Directorio: ESPECIALIDAD · ESTADO · "Renombrar {x}" (Secundario como enlace a `?editar={id}`) y "Desactivar {x}" (Secundario) o "Activar {x}" → panel Lateral `E2 NUEVA ESPECIALIDAD` (NOMBRE + Primario "Crear especialidad"). Con `?editar=`, E2 pasa a `E2 RENOMBRAR {X}`: NOMBRE con el actual + Primario "Guardar nombre" + enlace "Cancelar" (quita `editar`). Desactivar no pide confirmación: no borra nada y se deshace con "Activar".

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lista | Vacío | "Aún no hay profesionales" + "Para sumar uno, dale el rol Profesional artístico a su cuenta en Usuarios." + Primario "Asignar rol de profesional" (sin fila de controles) |
| E1 | Vacío | "Aún no hay especialidades" + "Crea la primera: por ejemplo, Producción o Composición." La primaria es la de E2 |
| E2 | Validación (y 422) | "Escribe el nombre." · "Usa de 2 a 60 caracteres." |
| E2 | 409 `especialidad_duplicada` | Error bajo NOMBRE: "Ya existe una especialidad con ese nombre (sin contar mayúsculas ni tildes)." |
| E1 | 404 o `editar` desconocido | Aviso Información "Esa especialidad ya no existe. Actualizamos la lista." |
| Éxito | `?aviso=` / en la vista | `profesional-asignado` "Rol asignado. Completa su ficha y fija sus precios para publicarlo." · "Especialidad creada." · "Nombre guardado." · "{x} desactivada: ya no se muestra en perfiles ni filtros." · "{x} activada." |
| Ficha | 404 | Aviso Información "No encontramos a este profesional." + "Volver a profesionales" |
| Ficha | Revisión de precios | Los estados de [cambios sensibles](RF-20-cambios-sensibles.md#estados-de-la-revisión) |
| Carga | — | Paneles con "Cargando…", `aria-busy`; enviando: botón en Carga ("Creando…", "Guardando…", "Desactivando…") y los demás envíos deshabilitados |
| Todas | 401 · 403 · 503 · red · no JSON · sin JS | Los de [tarifas](RF-02-tarifas.md#estados) ("Esta sección es solo para el Administrador.") |

Claves `aviso` (lista cerrada): `profesional-asignado`. Permisos: solo `administrador`; otros roles ven el 403 de la vista.

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Lista | Inicio / Asesorías · `[A13] ASESORÍAS / PROFESIONALES` | PROFESIONALES | Quién da asesorías, qué cobra y si ya se ve en el directorio. |
| Especialidades | Inicio / Asesorías / Especialidades · `[A14] ASESORÍAS / ESPECIALIDADES` | ESPECIALIDADES | Las que pueden elegir los profesionales y filtrar los artistas. No se borran: se desactivan. |

Acciones de fila con objeto en el nombre accesible: "Editar ficha de {nombre}", "Horarios de {nombre}", "Renombrar Producción", "Desactivar Producción".

## Accesibilidad

- `<h1>` del encabezado; paneles `<section>` con `<h2>`; tablas con `<caption>` y el nombre como `<th scope="row">`. ACTIVO y los precios, en un `<fieldset>` con `<legend>` "Estado y precios".
- Al abrir `?editar=`, el foco va al NOMBRE de E2; al guardar o cancelar, a "Renombrar {x}" de esa fila. La revisión de precios mueve el foco como en [cambios sensibles](RF-20-cambios-sensibles.md#accesibilidad).
- Región `role="status"` estable de cada isla para la carga ("5 profesionales") y los resultados; al fallar un envío, el foco va al aviso.

## Pendientes

- **leader / dev-backend:** `ProfesionalResumen` no trae `activo` ni `publicado`; para la lista proponemos sumarlos cuando quien pide es el Administrador.
- **leader / dev-backend:** `POST /cambios-sensibles/previsualizar` no admite precios de asesoría: proponemos `recurso: "profesional"` con `id_recurso`, `cambios: {precios}`, ejemplos de 30 min y 1 h con su IGV y `operaciones_vigentes` = sus asesorías vivas; también como filtro del registro de cambios.
- **leader / dev-backend:** decisión 8 (Administrador como profesional): no hay cómo nace su ficha (el rol no cambia). Proponemos que nazca al guardar su primera ficha o un `POST /profesionales` del Administrador.
- **leader:** destino ASESORÍAS (`messages-square`, concepto nuevo) para `administrador`, al menú de la cabecera en móvil; anotar "Ampliada por RF-15" en [usuarios](RF-01-solicitudes.md#pendientes). Una cuenta creada con Google que pasa a `profesional` necesita contraseña (CA-01): entra con "Restablecer contraseña".
