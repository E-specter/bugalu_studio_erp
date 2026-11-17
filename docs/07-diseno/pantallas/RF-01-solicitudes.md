---
id: pantalla-rf-01-solicitudes
titulo: Pantalla — Solicitudes de acceso y usuarios (Administrador)
estado: borrador
depende_de: [RF-01, ADR-008, diseno-brief, patron-estructura-app, patron-tablas-y-tableros, patron-formularios, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-boton, comp-aviso, comp-etiqueta-tecnica]
---

# Solicitudes de acceso y usuarios

| Campo | Valor |
|---|---|
| Requerimiento | [RF-01](../../03-requerimientos/RF-01.md): CA-08, CA-10, CA-13 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/solicitudes` (bandeja), `/app/solicitudes/revisar?id=`, `/app/usuarios?rol=`, `/app/usuarios/editar?id=`. URL: `id`, `rol`, `aviso` (la salida es estática: el id va en la consulta, no en la ruta) |
| Isla | `<bugalu-solicitudes vista="bandeja\|revisar\|usuarios\|usuario">` (nueva) |
| Origen Figma | Ninguno; vistas del brief con el [directorio](../patrones/tablas-y-tableros.md#directorio-tabla) de clientes (`161:842`) |

## Recorrido

1. El Administrador entra por "Accesos" (`user-plus`) o "Usuarios" (`users`) de la [navegación](../componentes/navegacion-lateral.md). Esos destinos solo se pintan cuando el perfil cargado es `administrador`; la API es la barrera real (403).
2. **Bandeja:** ve las pendientes, la más antigua arriba, y abre una con "Revisar".
3. **Revisar:** aprueba con rol (`personal` o `administrador`) y especialidad, o rechaza con motivo → vuelve a la bandeja con `?aviso=solicitud-aprobada` o `solicitud-rechazada`.
4. **Usuarios:** filtra por rol, abre una persona con "Cambiar rol", guarda rol y especialidad → vuelve con `?aviso=usuario-actualizado`. Si se quitó a sí mismo el rol de Administrador, va a `/app/`.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Pendientes | `GET /solicitudes-acceso?estado=pendiente` → `[Solicitud]` | Orden por `creada_en` ascendente; total "3 pendientes" |
| Persona | `Solicitud.nombre`, `correo` | Nombre en la celda principal, correo debajo (`color-texto-secundario`) |
| Especialidad solicitada, mensaje | `Solicitud.especialidad`, `mensaje` | Tal cual; el mensaje solo en Revisar |
| Enviada | `Solicitud.creada_en` | Relativa < 7 días con absoluta en `title`; si no, `D MMM AAAA` ([formato](../patrones/estructura-app.md#formato-de-datos)) |
| Solicitud a revisar | La de la lista con ese `id` (no hay lectura por id) | — |
| Aprobar | `POST /solicitudes-acceso/{id}/aprobar` `{rol, especialidad}` | Rol: [casilla](../componentes/casilla.md) Radio; especialidad: [campo](../componentes/campo.md) Texto prellenado con la solicitada |
| Rechazar | `POST /solicitudes-acceso/{id}/rechazar` `{motivo}` | Campo Área, obligatorio |
| Usuarios | `GET /usuarios?rol=` → `[Perfil]` | Nombre + correo; rol en [etiqueta](../componentes/etiqueta-tecnica.md) Neutra; especialidad o "—" |
| Usuario a editar | El de `GET /usuarios` con ese `id`; `GET /perfil` para saber si es uno mismo | `<dl>`: nombre, correo, teléfono, nombre artístico (si cliente) |
| Cambio | `PATCH /usuarios/{id}` `{rol, especialidad}` | Rol: Radio con tres opciones; especialidad: Texto |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Todas | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) (App) | Ruta, índice, título y descripción de la tabla Copy; sin acción |
| Todas | Avisos | [aviso](../componentes/aviso.md) | Resultado de la URL o de la acción |
| Bandeja | Principal | [panel](../componentes/panel.md) `PENDIENTES` + [tabla](../componentes/tabla.md) Directorio | Persona · Especialidad · Enviada · acción "Revisar" ([botón](../componentes/boton.md) Secundario como enlace) |
| Revisar | Principal | panel `S1 SOLICITUD` | `<dl>`: persona, correo, especialidad solicitada, mensaje, enviada |
| Revisar | Lateral | panel Lateral `S2 APROBAR` | `<fieldset>` Rol (Personal del estudio, marcado; Administrador) → especialidad → botón Primario "Aprobar acceso" |
| Revisar | Lateral | panel Lateral `S3 RECHAZAR` | Motivo → botón Peligro "Rechazar solicitud" |
| Usuarios | Controles | [etiquetas](../componentes/etiqueta-tecnica.md) Filtro | Todos · Clientes · Personal · Administradores (enlaces `?rol=`) |
| Usuarios | Principal | panel `CUENTAS` + tabla Directorio | Persona · Rol · Especialidad · "Cambiar rol" |
| Usuario | Principal | panel `U1 PERSONA` | `<dl>` de la persona |
| Usuario | Lateral | panel Lateral `U2 ROL Y ESPECIALIDAD` | Rol (Cliente, Personal del estudio, Administrador) → especialidad → [botón](../componentes/boton.md) Primario "Guardar rol y especialidad" (una sola acción: sin [barra de acciones](../componentes/barra-acciones.md#cuándo-se-usa)) |

Detalle de cada radio (`detalle` de la casilla): Cliente "Solo ve su portal de artista." · Personal "Entra al panel interno." · Administrador "Además, aprueba solicitudes, valida pagos y cambia roles."

Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md), [formularios](../patrones/formularios.md). Adaptabilidad: < `punto-quiebre-escritorio`, las tablas pasan a tarjetas (`<dl>`) y los paneles laterales van debajo del principal. Sin búsqueda ni paginación: el contrato no las ofrece y el equipo es pequeño.

**Decisión del brief:** aprobar y rechazar no llevan página de confirmación: ninguno es irreversible (la persona puede volver a solicitar; el rol se cambia en Usuarios) y el motivo obligatorio ya es un paso deliberado.

## Estados

| Vista | Vacío | Carga | Error | Éxito |
|---|---|---|---|---|
| Bandeja | Panel PENDIENTES: "No hay solicitudes pendientes" + "Cuando alguien del equipo pida acceso desde el registro interno, aparecerá aquí." Sin acción | Panel con "Cargando…", `aria-busy` | Aviso Error en el panel + "Reintentar" | `?aviso=solicitud-aprobada`: "Solicitud aprobada. La persona ya puede entrar al panel." · `solicitud-rechazada`: "Solicitud rechazada. La persona verá el motivo al entrar." |
| Revisar | El `id` no está en la lista: aviso Información "Esta solicitud ya no está pendiente. Puede que otra persona la haya revisado." + "Volver a solicitudes" | Ídem | Ver tabla de envío | Vuelve a la bandeja |
| Usuarios | Sin resultados del filtro: "No hay usuarios con ese rol." + "Quitar filtros" (Secundario) | Ídem | Ídem | `?aviso=usuario-actualizado`: "Rol actualizado." |
| Usuario | `id` desconocido: aviso Información "No encontramos este usuario." + "Volver a usuarios" | Ídem | Ver tabla de envío | Vuelve a Usuarios |

| Respuesta al cargar o enviar | Forma y texto |
|---|---|
| 401 | Aviso "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=` con la vista) |
| 403 `sin_permiso` | En lugar del bloque: `[403] SIN PERMISO` "Esta sección es solo para el Administrador." + "Volver al inicio" |
| 404 o 409 al aprobar o rechazar | Aviso Información de "ya no está pendiente" (arriba) |
| 409 `ultimo_administrador` | Aviso Error "No puedes quitar el último administrador. Da el rol de Administrador a otra persona antes de cambiar este." Datos conservados |
| 422 | Error bajo el campo si es nuestro ("Escribe la especialidad." · "Escribe el motivo del rechazo."); si no, aviso Error con el `mensaje` del servidor |
| 503 | Aviso Error "El servicio no responde. Inténtalo de nuevo en unos minutos." |
| Red caída | Aviso Error "Sin conexión. Revisa tu red e inténtalo de nuevo." |
| No JSON u otro | Aviso Error "Algo salió mal. Inténtalo de nuevo." |
| Enviando | Botón en Carga ("Aprobando…", "Rechazando…", "Guardando…"); el otro formulario de la vista, deshabilitado |
| Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Al cargar, los errores llevan "Reintentar"; al enviar, no: los datos se conservan y el botón sigue disponible. Editándose a sí mismo: aviso Aviso fijo sobre U2, "Estás cambiando tu propio rol. Si dejas de ser Administrador, perderás el acceso a esta sección."

Permisos: solo `administrador`. Personal y clientes no ven los destinos; si abren la URL, ven el 403.

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Bandeja | Inicio / Accesos · `[A1] EQUIPO / ACCESOS` | SOLICITUDES DE ACCESO | Personas que piden entrar al panel del estudio. Revisa cada una y asígnale rol y especialidad. |
| Revisar | Inicio / Accesos / {nombre} | REVISAR SOLICITUD | Decide si {nombre} entra al panel y con qué rol. |
| Usuarios | Inicio / Usuarios · `[A2] EQUIPO / USUARIOS` | USUARIOS | Todas las cuentas del estudio. Cambia el rol o la especialidad de cualquiera. |
| Usuario | Inicio / Usuarios / {nombre} | CAMBIAR ROL | El rol decide qué ve {nombre} en el sistema. |

Destino de navegación: **ACCESOS** (`user-plus`), no "Solicitudes" (11 caracteres, más que el tope de la [navegación táctil](../componentes/navegacion-tactil.md#anatomía)) ni "Solicitud" (en singular parece una solicitud propia, no la bandeja). La ruta del encabezado usa la misma palabra; el título dice qué se solicita. Decisión de la revisión visual de RF-01.

Etiquetas: ROL · ESPECIALIDAD · MOTIVO DEL RECHAZO. Ayudas: especialidad "Puedes corregirla. Para quien da asesorías, escribe asesoria." (provisional hasta RF-07); motivo "La persona lo verá al entrar. Di qué falta o por qué."; especialidad en U2 "Déjala vacía si es cliente." Acciones de fila con objeto: "Revisar solicitud de {nombre}", "Cambiar rol de {nombre}" (el nombre en texto oculto si no cabe). Columnas: PERSONA · ESPECIALIDAD · ENVIADA · ROL.

## Accesibilidad

- `<h1>` del encabezado; cada panel es `<section>` con `<h2>`. Tablas con `<caption>`, `<th scope="col">` y la persona como `<th scope="row">`.
- Filtros: enlaces con `aria-current="true"` en el aplicado ([etiqueta](../componentes/etiqueta-tecnica.md#estados)). Rol: `<fieldset>` + `<legend>` "Rol".
- Una región `role="status"` estable de la isla anuncia una vez cada carga ("3 solicitudes pendientes") y cada resultado; al fallar un envío, el foco va al aviso; tras "Reintentar", al título del panel.
- Orden de foco en Revisar: S1 no tiene controles → rol → especialidad → "Aprobar acceso" → motivo → "Rechazar solicitud".

## Pendientes

- **leader:** el contador de pendientes en la navegación ([navegación lateral](../componentes/navegacion-lateral.md), etiqueta Alerta) queda fuera: pediría una llamada en cada vista. Registrar `<bugalu-solicitudes>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
- **leader:** la especialidad `asesoria` es texto libre hasta que RF-07 cierre la lista.
- **Ampliada por RF-17:** documento, filtro de documentos repetidos y textos aceptados de la persona ([textos legales](RF-17-textos-legales.md#administrador-documentos-repetidos)).
- **Ampliada por RF-18:** panel `U4 CRÉDITOS` en la persona con rol Cliente ([créditos](RF-18-creditos.md#ficha-del-cliente-administrador)).
