---
id: operacion-correo-gmail
titulo: Correo saliente con Gmail
estado: borrador
depende_de: [ADR-011, ADR-009, operacion-montaje-local]
---

# Correo saliente con Gmail

En producción, el correo sale de la cuenta de Google del estudio por SMTP ([ADR-011](../00-proyecto/decisiones/ADR-011-correo-gmail-del-estudio.md)). Lo usan el backend, para los avisos de la bandeja `notificacion`, y Supabase Auth, para restablecer la contraseña y enviar el enlace de verificación. Los dos usan el mismo remitente. En local todo va a Mailpit (`http://127.0.0.1:45624`) y nada sale de verdad ([montaje-local](montaje-local.md)).

## 1. Contraseña de aplicación

1. Entra a `https://myaccount.google.com` con la cuenta del estudio → **Seguridad** → **Verificación en dos pasos** y actívala con el teléfono o con una app de autenticación.
2. Abre `https://myaccount.google.com/apppasswords` (**Contraseñas de aplicación**).
3. Ponle un nombre que diga quién la usa (`bugalu-backend`, `bugalu-auth`) y pulsa **Crear**. Crea una por servicio: así puedes revocar una sin cortar la otra.
4. Copia los 16 caracteres, sin los espacios con que Google los agrupa, directamente al entorno del servicio. Google no vuelve a mostrarla.

Si la opción no aparece:

- La verificación en dos pasos no está activa o solo usa llaves de seguridad: añade otro segundo paso.
- La cuenta tiene la Protección Avanzada: no admite contraseñas de aplicación.
- Es una cuenta de trabajo o de un centro educativo: lo decide su administrador. ADR-011 usa una cuenta personal.
- Escribe "contraseñas de aplicación" en el buscador de la cuenta: no siempre aparece en Seguridad.

Si cambias la contraseña de la cuenta de Google, se revocan todas las contraseñas de aplicación. Crea otras y cárgalas en cada servicio.

## 2. Datos SMTP de Gmail

| Dato | Valor |
|---|---|
| Servidor | `smtp.gmail.com` |
| Puerto | `587` con STARTTLS (el 465 es SSL implícito; no se usa) |
| Usuario | La dirección completa de la cuenta del estudio |
| Contraseña | La contraseña de aplicación |
| Remitente | La misma cuenta. Otra dirección solo si está añadida y verificada en Gmail → Configuración → Cuentas e importación → "Enviar correo como" |

**Límite diario.** Una cuenta personal de Gmail queda bloqueada para enviar si un correo va a más de 500 destinatarios o si envía más de 500 correos en un día. Vuelve a enviar en 1 a 24 horas ([Gmail, límites de envío](https://support.google.com/mail/answer/22839)). El cupo lo comparten el backend, Auth y lo que el estudio envíe a mano desde Gmail. Si el volumen se acerca, ADR-011 prevé pasar a Google Workspace o a un proveedor transaccional cambiando solo la configuración.

## 3. Backend

Variables de `backend/.env` en el servidor:

| Variable | Producción | Local |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | `127.0.0.1` (Mailpit) |
| `SMTP_PUERTO` | `587` | `45625` |
| `SMTP_USUARIO` | La cuenta del estudio | Vacía |
| `SMTP_CLAVE` | Contraseña de aplicación `bugalu-backend` | Vacía |
| `SMTP_STARTTLS` | `true` | Vacía |
| `CORREO_REMITENTE` | La cuenta del estudio | El valor de `.env.example` |

- Con `SMTP_USUARIO`, el backend exige `SMTP_CLAVE` y `SMTP_STARTTLS=true` y rechaza la configuración si faltan: nunca envía la clave sin cifrar.
- Con las tres vacías, envía a Mailpit sin credenciales.
- La clave nunca se versiona ni va a `.env.example`.
- La tarea periódica envía cada `INTERVALO_ENVIO_CORREOS` segundos. Para enviar una vez a mano, desde `backend/`: `uv run python -m bugalu.herramientas.enviar_correos`.

## 4. Supabase Auth en producción

Plantillas que usa Bugalú hoy: `recovery` (restablecer contraseña, RF-01 CA-05) y `magic_link` (verificar el correo, CA-06). No hay correo de confirmación al registrarse (`enable_confirmations = false`).

**Supabase en la nube (panel):**

1. Authentication → Emails → **SMTP Settings**: activa el SMTP propio. Correo del remitente: la cuenta. Nombre del remitente: `Bugalú Studio`. Host: `smtp.gmail.com`. Puerto: `587`. Usuario: la cuenta. Contraseña: la de aplicación `bugalu-auth`.
2. Authentication → **Rate Limits**: con SMTP propio, Auth permite 30 correos por hora por defecto. Ajústalo al volumen esperado, sin pasar el cupo diario de Gmail.
3. Authentication → Emails → **Templates**: asunto y texto en español de las dos plantillas.

Sin SMTP propio, el servicio de correo de Supabase solo entrega a los miembros del equipo del proyecto y 2 correos por hora: no sirve para producción.

**Auth con `config.toml` (CLI o instalación propia):**

```toml
[auth.email.smtp]
enabled = true
host = "smtp.gmail.com"
port = 587
user = "<cuenta del estudio>"
pass = "env(SUPABASE_AUTH_SMTP_PASS)"
admin_email = "<cuenta del estudio>"
sender_name = "Bugalú Studio"
```

- La contraseña va en el `.env` de ese entorno (en el CLI, `supabase/.env`), nunca en `config.toml`. `SUPABASE_AUTH_SMTP_PASS` es un nombre propuesto: si lo adoptas, añádelo vacío a `supabase/.env.example`.
- **No actives este bloque en local:** Auth enviaría correos reales en lugar de usar Mailpit.
- `[auth.rate_limit] email_sent` (correos por hora) solo cuenta con SMTP activo. El repositorio lo deja en `2`; en producción súbelo, p. ej. a `30` como el panel.
- Plantillas: `[auth.email.template.recovery]` y `[auth.email.template.magic_link]`, cada uno con `subject` y `content_path` (HTML en `supabase/templates/`).
- `site_url` y `additional_redirect_urls` deben apuntar al dominio de producción: los enlaces de los correos se construyen con ellos.

Tras cambiar `config.toml`, reinicia Auth (`npx supabase stop` y `npx supabase start` con el CLI).

## 5. Prueba de extremo a extremo

1. Carga las variables y reinicia la API y Auth.
2. **Auth:** con una cuenta de prueba que sea tuya, usa "¿Olvidaste tu contraseña?" y, desde el perfil, "Verificar mi correo". Deben llegar los dos enlaces y abrir el dominio de producción, no `localhost`.
3. **Backend:** haz una reserva de prueba con esa cuenta. Debe llegar `reserva_creada` con el folio. Si no esperas a la tarea periódica, lanza `enviar_correos`.
4. En el Gmail del estudio, **Enviados** guarda una copia de cada correo enviado por SMTP. Comprueba el remitente, el asunto y los enlaces.

## Si no llega

- **Spam o Promociones** del destinatario. Márcalo como "no es spam".
- **`535 5.7.8` (usuario o contraseña no aceptados):** contraseña de aplicación revocada (por un cambio de contraseña de la cuenta o porque se borró), copiada con espacios, o usuario distinto de la cuenta. Crea otra.
- **`550 5.4.5` (límite diario alcanzado):** espera de 1 a 24 horas y revisa qué está enviando tanto.
- **Auth responde 429 `over_email_send_rate_limit`:** se alcanzó `email_sent` o el límite del panel.
- **Avisos del backend:** un envío fallido suma `intentos` y guarda el tipo de error. Tras 5 intentos no se reintenta. Consúltalo con la conexión de administración: `select id, intentos, error from public.notificacion where enviada_en is null;`. El registro de la API muestra `envio de correos fallido` si falla la tarea entera.

## Calendario

La conexión con Google Calendar y Meet (RF-19), sus implicancias y el procedimiento propuesto están en [calendario-google](calendario-google.md). Ojo: cambiar la contraseña de la cuenta revoca las contraseñas de aplicación del SMTP.

Fuentes: [Google, contraseñas de aplicación](https://support.google.com/accounts/answer/185833) · [Gmail, límites de envío](https://support.google.com/mail/answer/22839) · [Gmail, IMAP y SMTP](https://developers.google.com/workspace/gmail/imap/imap-smtp) · [Gmail, enviar correo como](https://support.google.com/mail/answer/22370) · [Supabase, SMTP propio](https://supabase.com/docs/guides/auth/auth-smtp) · [Supabase, config del CLI](https://supabase.com/docs/guides/local-development/cli/config) (consultadas el 2026-11-16).
