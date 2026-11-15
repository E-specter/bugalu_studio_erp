---
id: pantalla-rf-01-restablecer
titulo: Pantalla — Restablecer contraseña
estado: borrador
depende_de: [RF-01, ADR-008, diseno-brief, pantalla-rf-01-acceso, patron-estructura-app, patron-formularios, patron-estados-sistema, comp-campo, comp-boton, comp-aviso]
---

# Restablecer contraseña

| Campo | Valor |
|---|---|
| Requerimiento | [RF-01](../../03-requerimientos/RF-01.md): CA-02, CA-05, CA-13 |
| Actores | Cualquier usuario con cuenta (artista, personal, Administrador) |
| Estructura | Acceso ([estructura de app](../patrones/estructura-app.md#acceso)) |
| Ruta | `/acceso/recuperar` (pedir enlace) y `/acceso/nueva-contrasena` (fijarla). URL: `origen=interno` (marca e inicio de sesión de vuelta) |
| Isla | `<bugalu-acceso modo="recuperar\|restablecer">` y `<bugalu-contrasena medidor>` |
| Origen Figma | Solo los enlaces "Recuperar clave" (`112:376`) y "¿Olvidó su contraseña?" (`112:184`); las dos vistas son del brief |

## Recorrido

1. Llega desde "¿Olvidaste tu contraseña?" del [acceso de artistas](RF-01-acceso.md) o del [acceso interno](RF-01-acceso-interno.md) (`?origen=interno`).
2. Escribe su correo → `resetPasswordForEmail` con `redirectTo` a `/acceso/nueva-contrasena` (conserva `origen`). La respuesta es **la misma exista o no el correo** (CA-05). En local, el correo se ve en Mailpit.
3. Abre el enlace del correo: supabase-js abre la sesión de recuperación y la vista pide la nueva contraseña con [medidor](../componentes/campo.md#medidor-de-robustez).
4. Guarda → `updateUser({ password })` → `/app/perfil?aviso=contrasena-cambiada` ([perfil](RF-01-perfil.md)). La sesión queda abierta.
5. Si el enlace caducó o ya se usó, pide otro desde la misma vista.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Correo | Supabase Auth (`resetPasswordForEmail`) | `type="email"`, `autocomplete="email"`, obligatorio |
| Nueva contraseña | Supabase Auth (`updateUser`) | `type="password"`, `autocomplete="new-password"`, [medidor](../componentes/campo.md#medidor-de-robustez) (CA-02) |
| Validez del enlace | Evento `PASSWORD_RECOVERY` de supabase-js, o `error_code` en el fragmento de la URL | No se muestra; decide el estado |

## Composición

Mismas regiones que el [acceso de artistas](RF-01-acceso.md#composición); con `origen=interno`, la marca y el pie son los del [acceso interno](RF-01-acceso-interno.md#copy).

| Vista | Formulario (`<main>`) |
|---|---|
| Pedir enlace | [Etiqueta](../componentes/etiqueta-tecnica.md) Invertida (antetítulo), `<h1>`, texto, [campo](../componentes/campo.md) correo, [botón](../componentes/boton.md) Primario grande "Enviar enlace", enlace "Volver a iniciar sesión" |
| Nueva contraseña | Antetítulo, `<h1>`, texto, campo Contraseña con medidor, botón Primario grande "Guardar contraseña", enlace "Volver a iniciar sesión" |

Tras enviar el enlace, el formulario se sustituye por el [aviso](../componentes/aviso.md) de resultado y el enlace "¿No llegó? Pedir otro enlace", que vuelve a mostrar el formulario con el correo prellenado.

## Estados

Errores comunes de Supabase Auth (429, 5xx, red caída, respuesta desconocida): [acceso de artistas](RF-01-acceso.md#estados). Además:

| Vista | Situación | Forma y texto |
|---|---|---|
| Pedir enlace | Enviando | Botón en Carga "Enviando enlace…" |
| Pedir enlace | Respuesta correcta **o** cualquier error que dependa del correo (`user_not_found`, `email_address_invalid` del servicio…) | Aviso Éxito: "Si hay una cuenta con ese correo, te enviamos un enlace para crear una contraseña nueva. Revisa también la carpeta de spam." Nunca otro texto: no se revela si el correo existe |
| Pedir enlace | Formato de correo inválido (en el navegador) | Error bajo el campo: "Escribe un correo válido, como nombre@dominio.com." |
| Pedir enlace | 429, 5xx, red caída | Aviso Error de la tabla común; el correo se conserva (no dependen del correo, no revelan nada) |
| Nueva contraseña | Comprobando el enlace | Bloque con "Comprobando el enlace…" y `aria-busy="true"`, mismo tamaño que el formulario |
| Nueva contraseña | Enlace caducado, usado o sin sesión de recuperación (`otp_expired`, llegada directa) | Aviso Error "El enlace caducó o ya se usó." + principal "Pedir otro enlace" (a `/acceso/recuperar`, con `origen`). El aviso sustituye al texto "Elige una contraseña nueva…" y al formulario: bajo el `<h1>` solo quedan el aviso y el enlace "Volver a iniciar sesión" |
| Nueva contraseña | Guardando | Botón en Carga "Guardando contraseña…" |
| Nueva contraseña | `same_password` | Error bajo el campo: "Elige una contraseña distinta de la anterior." |
| Nueva contraseña | `weak_password` o nivel Débil | Error del [medidor](../componentes/campo.md#medidor-de-robustez): qué condición falta |
| Nueva contraseña | Sesión caducada al guardar (401) | Como enlace caducado |
| Nueva contraseña | Éxito | Va al perfil; allí, aviso Éxito `contrasena-cambiada`: "Contraseña actualizada. Usa la nueva la próxima vez que inicies sesión." |
| Ambas | Sin JS | `<noscript>`: aviso Información "Recuperar la contraseña necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: vistas públicas; la nueva contraseña solo se puede fijar con la sesión de recuperación del enlace.

## Copy

| Elemento | Pedir enlace | Nueva contraseña |
|---|---|---|
| `<title>` y `<h1>` | Recuperar contraseña · RECUPERAR CONTRASEÑA | Nueva contraseña · NUEVA CONTRASEÑA |
| Antetítulo | RECUPERACIÓN DE ACCESO | RECUPERACIÓN DE ACCESO |
| Texto | "Escribe el correo de tu cuenta y te enviaremos un enlace para crear una contraseña nueva." | "Elige una contraseña nueva para tu cuenta." |
| Campo | // CORREO | // NUEVA CONTRASEÑA (ayuda del [medidor](../componentes/campo.md#medidor-de-robustez)) |
| Acción principal | Enviar enlace | Guardar contraseña |
| Enlace | Volver a iniciar sesión (a `/acceso` o `/acceso/interno`) | Volver a iniciar sesión |

Errores de campo vacío: "Escribe tu correo." · "Escribe una contraseña."

## Accesibilidad

- Puntos de referencia, `<h1>` y orden de foco como en el [acceso de artistas](RF-01-acceso.md#accesibilidad).
- Al sustituir el formulario por el aviso Éxito, el foco va al aviso (`tabindex="-1"`, sin rol vivo) para no caer en `<body>`. Al volver a pedir el enlace, el foco va al campo correo.
- "Comprobando el enlace…" no mueve el foco; si el enlace no vale, el aviso ocupa el lugar del formulario y se lee en orden.
- El medidor anuncia solo el nivel ([ficha](../componentes/campo.md#medidor-de-robustez)).

## Pendientes

- **dev-backend:** confirmar que la URL `/acceso/nueva-contrasena` está en las redirecciones permitidas de Supabase Auth (`supabase/config.toml`).
