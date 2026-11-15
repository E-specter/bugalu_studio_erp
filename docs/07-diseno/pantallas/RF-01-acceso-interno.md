---
id: pantalla-rf-01-acceso-interno
titulo: Pantalla — Acceso interno y solicitud de acceso
estado: borrador
depende_de: [RF-01, ADR-008, diseno-brief, pantalla-rf-01-acceso, patron-estructura-app, patron-formularios, patron-estados-sistema, comp-campo, comp-boton, comp-aviso, comp-etiqueta-tecnica]
---

# Acceso interno y solicitud de acceso

| Campo | Valor |
|---|---|
| Requerimiento | [RF-01](../../03-requerimientos/RF-01.md): CA-02 a CA-04, CA-07, CA-08 (lado de quien solicita), CA-12, CA-13 |
| Actores | Personal interno y Administrador (entrar); persona que pide entrar al equipo |
| Estructura | Acceso ([estructura de app](../patrones/estructura-app.md#acceso)), misma que el [acceso de artistas](RF-01-acceso.md); cambian textos e imagen |
| Ruta | `/acceso/interno` (iniciar), `/acceso/interno/registro` (solicitar acceso), `/acceso/interno/solicitud` (estado de la solicitud; URL: `nueva`, `aviso`) |
| Isla | `<bugalu-acceso modo="interno\|solicitar">`, `<bugalu-solicitud>` (nueva, estado propio) y `<bugalu-contrasena>` |
| Origen Figma | `112:61` login-interno, `112:193` registro-interno (volcado local) |

## Recorrido

1. Llega por la URL que le da el estudio o por el enlace "¿Eres del equipo? Acceso interno" del pie del [acceso de artistas](RF-01-acceso.md). **Nunca hay Google** (CA-04).
2. **Iniciar:** `signInWithPassword` y luego `GET /perfil`. Rol `personal` o `administrador` → `/app/`. Rol `cliente` → `/acceso/interno/solicitud`.
3. **Solicitar acceso:** "Solicitar acceso" lleva a `/acceso/interno/registro`. Nombre, teléfono, correo, especialidad, mensaje (opcional) y contraseña con medidor → `signUp` (metadatos `nombre`, `telefono`) → `POST /solicitudes-acceso` → `/acceso/interno/solicitud?aviso=solicitud-enviada`.
4. **Estado** (`GET /solicitudes-acceso/mia`): pendiente (espera), rechazada (ve el motivo y puede enviar otra), aprobada (va a `/app/`) o sin solicitud (formulario corto: especialidad y mensaje).
5. Desde el estado puede cerrar sesión (vuelve a `/acceso/interno?aviso=sesion-cerrada`).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Correo, contraseña, nombre, teléfono | Supabase Auth y metadatos, como en el [acceso de artistas](RF-01-acceso.md#datos) | Ídem; contraseña nueva con [medidor](../componentes/campo.md#medidor-de-robustez) |
| Rol (para decidir el destino) | `GET /perfil` → `Perfil.rol` | No se muestra |
| Especialidad | `POST /solicitudes-acceso` `{especialidad}` → `Solicitud.especialidad` | Texto libre corto, obligatorio |
| Mensaje | `{mensaje?}` → `Solicitud.mensaje` | [Campo](../componentes/campo.md) Área, opcional; tal cual |
| Estado | `Solicitud.estado` | [Etiqueta](../componentes/etiqueta-tecnica.md): pendiente → Aviso "PENDIENTE"; rechazada → Alerta "RECHAZADA" |
| Motivo | `Solicitud.motivo` | Tal cual, solo si rechazada |
| Enviada / revisada | `Solicitud.creada_en`, `revisada_en` | `D MMM AAAA` ([formato](../patrones/estructura-app.md#formato-de-datos)) |

## Composición

Mismas regiones que el [acceso de artistas](RF-01-acceso.md#composición): marca (`<header>`), visual (`<aside>`, [marco de registro](../componentes/marco-registro.md) Panel con la cita), formulario (`<main>`) y pie. Marca con dos [etiquetas](../componentes/etiqueta-tecnica.md) Neutra (decorativas, no son un estado del sistema).

- **Iniciar:** correo → contraseña → "¿Olvidaste tu contraseña?" (a `/acceso/recuperar?origen=interno`) → "Entrar a la sala" ([botón](../componentes/boton.md) Primario grande) → "¿Eres nuevo en el equipo? Solicitar acceso".
- **Solicitar acceso:** texto bajo el `<h1>` → nombre → teléfono → correo → especialidad → mensaje → contraseña con medidor → "Enviar solicitud" → "¿Ya tienes cuenta? Inicia sesión".
- **Estado de la solicitud:** `<h1>`, etiqueta de estado, `<dl>` (especialidad, mensaje, enviada; si rechazada, revisada y motivo), texto de qué sigue, acción principal y "Cerrar sesión" ([botón](../componentes/boton.md) Secundario). Sin solicitud o con `?nueva=1`: formulario corto (especialidad, mensaje) en lugar de la `<dl>`.

**Decisiones del brief frente a Figma:** "Código de invitación" (`112:274`) se sustituye por la solicitud con aprobación ([ADR-008](../../00-proyecto/decisiones/ADR-008-acceso-y-roles-v1.md)). "Equipo / rol técnico" (`112:265`) es la especialidad; el rol lo asigna el Administrador. Se quitan las afirmaciones que el sistema no cumple: "Bugalú Shield" (`112:191`), "hash criptográfico" (`124:150`) y "registro auditado" (`112:284`). Teléfono obligatorio, como en el registro de artistas.

## Estados

Formularios de iniciar y solicitar: los de la tabla del [acceso de artistas](RF-01-acceso.md#estados) (Supabase Auth). Además:

| Bloque | Situación | Forma y texto |
|---|---|---|
| Iniciar | `GET /perfil` 503, red caída o no JSON tras entrar | Aviso Error "Entraste, pero no pudimos cargar tu perfil. Inténtalo de nuevo." + "Reintentar" (repite solo `GET /perfil`) |
| Iniciar | `GET /perfil` 404 | Aviso Error "No encontramos tu perfil. Pide al estudio que lo cree." |
| Solicitar | Cuenta creada pero `POST` falla (503, red) | Aviso Error "Tu cuenta se creó, pero la solicitud no se envió." + "Reintentar envío" (repite solo el `POST`; los datos de cuenta quedan bloqueados) |
| Solicitar | `user_already_exists` | Error en correo: "Ya hay una cuenta con este correo. Inicia sesión aquí para enviar tu solicitud." (enlace a `/acceso/interno`) |
| Solicitar | 422 | Error bajo el campo: "Escribe tu especialidad, por ejemplo Ingeniería de mezcla." |
| Solicitar | 409 `conflicto` | Va al estado; si ya es personal, a `/app/` |
| Estado | Carga | Bloque con "Cargando…" y `aria-busy="true"`, mismo tamaño |
| Estado | Pendiente | Etiqueta PENDIENTE; "El Administrador aún no revisa tu solicitud. Cuando la apruebe, entrarás al panel con tu correo y contraseña." Principal: "Comprobar estado" |
| Estado | Rechazada | Etiqueta RECHAZADA; "MOTIVO" + motivo; "Si algo cambió, puedes enviar otra solicitud." Principal: "Enviar otra solicitud" (`?nueva=1`) |
| Estado | Aprobada | Va a `/app/` sin pantalla intermedia |
| Estado | Sin solicitud (404) | "Tu cuenta aún no tiene una solicitud de acceso al panel." + formulario corto. Principal: "Enviar solicitud" |
| Estado | 401 | Aviso "Tu sesión no es válida. Inicia sesión para ver tu solicitud." + "Ir al acceso interno" |
| Estado | 503, red, no JSON, 403 | Aviso Error con el texto del [perfil](RF-01-perfil.md#estados) según el caso + "Reintentar" |
| Estado | `?aviso=solicitud-enviada` | Aviso Éxito "Solicitud enviada. El Administrador la revisará; vuelve aquí para ver su estado." |
| Todas | Sin JS | `<noscript>`: aviso Información "El acceso necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: el estado solo muestra la solicitud propia (`/mia`). Quien aún no es personal no ve el panel interno (CA-07).

## Copy

| Elemento | Iniciar | Solicitar acceso | Estado |
|---|---|---|---|
| `<title>` y `<h1>` | Sala técnica · SALA TÉCNICA | Solicitar acceso · SOLICITAR ACCESO | Tu solicitud · TU SOLICITUD |
| Antetítulo | SISTEMA DE ACCESO INTERNO | INGRESO DE EQUIPO | ACCESO INTERNO |
| Marca | `[ACCESO_INTERNO]` "Panel de producción, ingeniería y administración de Bugalú Studio. Inicia sesión para gestionar sesiones, proyectos y versiones." | `[REGISTRO_TÉCNICO]` "Pide tu acceso al panel del estudio. El Administrador revisa cada solicitud." | Igual que iniciar |
| Etiquetas de marca | SALA DE CONTROL · V1.0 | REGISTRO: SOLO EQUIPO · V1.0 | Igual que iniciar |
| Acción principal | Entrar a la sala | Enviar solicitud | Según el estado (tabla de Estados) |
| Pie | BUGALÚ STUDIO · CONVERGE Y CREA | SISTEMA DE CONTROL INTERNO · BUGALÚ STUDIO | BUGALÚ STUDIO · CONVERGE Y CREA |

- Visual: cita "La rigurosidad acústica exige una interfaz sin adornos." — Manual del ingeniero de sonido, Bugalú (`112:162`).
- Texto bajo el `<h1>` de solicitar: "Creamos tu cuenta y enviamos tu solicitud al Administrador. Podrás entrar al panel cuando la apruebe."
- Etiquetas: NOMBRE COMPLETO, TELÉFONO, CORREO, ESPECIALIDAD, MENSAJE (opcional), CONTRASEÑA. Ayudas: especialidad "Tu área en el estudio; el Administrador la confirma." (ejemplo "p. ej. Ingeniería de mezcla"); mensaje "Cuéntale quién eres o quién te invitó." Carga: "Entrando…", "Enviando solicitud…", "Comprobando…".

## Accesibilidad

- Puntos de referencia, `<h1>`, orden de foco y validación como en el [acceso de artistas](RF-01-acceso.md#accesibilidad).
- `<bugalu-solicitud>` sigue el modelo de `<bugalu-perfil>`: una región `role="status"` estable anuncia una vez el estado ("Solicitud pendiente", "Solicitud rechazada"); tras "Comprobar estado" o "Reintentar", el foco va al `<h1>` (`tabindex="-1"`).
- La etiqueta de estado tiene texto propio; el motivo se lee como `<dd>` tras el `<dt>` "Motivo".

## Pendientes

- **dev-frontend:** como en el acceso de artistas, validar el teléfono antes de `signUp` (el disparador lo descarta en silencio si está mal formado).
- **leader:** la especialidad es texto libre hasta RF-07, pero RF-15 espera `asesoria` exacta para el profesional artístico ([actores](../../02-dominio/actores-roles.md)): lo resuelve el Administrador al aprobar ([solicitudes](RF-01-solicitudes.md)).
- **leader:** registrar `<bugalu-solicitud>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
