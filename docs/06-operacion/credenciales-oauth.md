---
id: operacion-credenciales-oauth
titulo: Credenciales OAuth de Google y Meta
estado: borrador
depende_de: [ADR-008, ADR-009, RF-01, operacion-montaje-local]
---

# Credenciales OAuth de Google y Meta

Acceso social de artistas y clientes ([RF-01](../03-requerimientos/RF-01.md) CA-04, [ADR-008](../00-proyecto/decisiones/ADR-008-acceso-y-roles-v1.md)). El personal entra siempre con correo y contraseña. Ningún secreto se escribe aquí ni se versiona.

## Antes de empezar

- La cuenta de Google del estudio ([ADR-011](../00-proyecto/decisiones/ADR-011-correo-gmail-del-estudio.md)) para Google Cloud.
- Una cuenta de Facebook registrada como desarrollador en Meta for Developers: el registro confirma un teléfono y un correo con códigos y pide aceptar las políticas de la plataforma.
- El stack local en marcha ([montaje-local](montaje-local.md)).

URL de retorno: es el callback de Supabase Auth, no el frontend. Regístrala exacta (esquema, host, puerto, sin barra final).

| Dónde | Callback | Orígenes del frontend |
|---|---|---|
| Local, Google | `http://127.0.0.1:45621/auth/v1/callback` (`redirect_uri` de `[auth.external.google]`) | `http://localhost:4321`, `http://127.0.0.1:4321` |
| Local, Meta | `http://localhost:45621/auth/v1/callback` (ver Meta, paso 4) | los mismos |
| Producción | `https://<host de Supabase>/auth/v1/callback`; en la nube, el panel lo muestra en Authentication → Sign In / Providers | el dominio público del frontend (pendiente, D-08) |

Google acepta `http` solo para `localhost` y `127.0.0.1`. Meta lo acepta solo para `localhost` y solo en modo desarrollo. Tras autenticar, Auth vuelve a `<origen>/app/` (`signInWithOAuth` en `frontend/src/servicios/sesion.js`): ese destino debe estar en `site_url` o `additional_redirect_urls` de `supabase/config.toml` (en la nube, Authentication → URL Configuration).

## Google

**1. Proyecto y pantalla de consentimiento.** La consola se ve en inglés o en español según la cuenta; aquí van los nombres en inglés.

1. Entra a `https://console.cloud.google.com` con la cuenta del estudio y crea un proyecto (p. ej. `bugalu-acceso`).
2. Abre **Google Auth Platform** (antes "OAuth consent screen", en APIs y servicios) y pulsa **Get started**.
3. App information: nombre visible sin marcas de Google ni de terceros, y la cuenta del estudio como correo de asistencia.
4. Audience: **External**. Internal solo admite cuentas de una organización de Workspace (error `org_internal`).
5. Contact information: la cuenta del estudio. Acepta la política de datos de usuario y crea.
6. **Data Access** → Add or remove scopes: `openid`, `.../auth/userinfo.email` y `.../auth/userinfo.profile`. Nada más: un ámbito sensible exige verificación.

**2. Usuarios de prueba o app publicada.**

- Estado **Testing**: hasta 100 usuarios de prueba (Audience → Test users → Add users). Con solo `openid`, `email` y `profile`, la ayuda de Google indica que no hace falta estar en la lista, no hay aviso de app no verificada y la autorización no caduca a los 7 días. Añade igual las cuentas del equipo.
- **Publish app** (estado In production): cualquier cuenta de Google. Ver los requisitos al final.

**3. Cliente OAuth.**

1. **Clients** → **Create client** → tipo **Web application**. Un cliente por entorno: `bugalu-local` y, después, `bugalu-produccion`.
2. Authorized JavaScript origins: los orígenes del frontend de la tabla.
3. Authorized redirect URIs: el callback de la tabla.
4. Create. Copia el ID de cliente y el secreto: el secreto completo solo se ve y se descarga al crearlo; después, solo sus cuatro últimos caracteres.
5. Los cambios de URI tardan de 5 minutos a unas horas en aplicarse.

**4. Activar en local.**

1. `cp supabase/.env.example supabase/.env` (ignorado por git; el CLI lo lee al arrancar) y rellena los nombres que `config.toml` lee con `env(...)`:
   ```dotenv
   SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID=<id de cliente>
   SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET=<secreto>
   ```
   La doc de Supabase usa otro nombre de ejemplo para el secreto; aquí manda `config.toml`.
2. En `supabase/config.toml`, bloque `[auth.external.google]`: `enabled = true` (el repositorio lo deja en `false`).
3. `npx supabase stop` y `npx supabase start`.
4. En `frontend/.env`: `PUBLIC_ACCESO_PROVEEDORES=google` (`google,facebook` con los dos). Se lee al construir: reinicia `npm run dev`.

**5. Probar.** Abre `http://localhost:4321/acceso/` → **Continuar con Google** → elige la cuenta. Google vuelve al callback y Auth a `/app/`. El perfil muestra el nombre y el correo verificado (CA-06). `/acceso/interno/` no muestra el botón.

## Meta (Facebook)

**1. App.**

1. En `https://developers.facebook.com`: **My Apps** → **Create App**.
2. App details: nombre de la app y la cuenta del estudio como correo de contacto.
3. Use cases: **Authenticate and request data from users with Facebook Login**. Antes se elegía un tipo de app (Consumer) y se añadía el producto Facebook Login.
4. Business: "I don't want to connect a business portfolio yet" basta para empezar.
5. Requirements y Overview: revisa y pulsa **Go to dashboard**.

**2. Inicio de sesión con Facebook.**

1. Use cases → el de Facebook Login (Authentication and account creation) → **Customize**. En Permissions, `public_profile` y `email` deben estar en "Ready for testing"; si falta `email`, **Add**.
2. En **Settings** del inicio de sesión con Facebook (en paneles antiguos, Products → Facebook Login → Settings), escribe el callback en **Valid OAuth Redirect URIs** y guarda. Deja activos Client OAuth login, Web OAuth login, Enforce HTTPS y el modo estricto.
3. App settings → **Basic**: copia el **App ID** y, con **Show**, el **App Secret**.

**3. Modo desarrollo o modo activo.** Toda app nace en modo desarrollo: solo entran quienes tienen un rol en ella (administradores, desarrolladores, probadores). Añade probadores en **App roles → Roles**; cada uno acepta la invitación desde su cuenta. El modo activo (Live) admite a cualquiera; se cambia con el interruptor de modo del panel. `email` y `public_profile` no requieren revisión de la app. En modo activo `localhost` deja de valer: para seguir probando en local, usa una segunda app en modo desarrollo.

**4. Activar en local.**

1. En `supabase/.env`: `SUPABASE_AUTH_EXTERNAL_FACEBOOK_CLIENT_ID=<App ID>` y `SUPABASE_AUTH_EXTERNAL_FACEBOOK_SECRET=<App Secret>`.
2. En `[auth.external.facebook]`: `enabled = true` y `redirect_uri = "http://localhost:45621/auth/v1/callback"`. El valor del repositorio usa `127.0.0.1`, que Meta no exime de HTTPS.
3. Reinicia el stack y añade `facebook` a `PUBLIC_ACCESO_PROVEEDORES`.
4. Prueba con **Continuar con Facebook** y una cuenta con rol en la app. La cuenta debe tener correo: con `email_optional = false`, Auth rechaza a quien no lo comparte.

## Requisitos para pasar a producción

> **El estudio aún no tiene política de privacidad, términos de servicio ni instrucciones de eliminación de datos publicados.** Sin ellos, Google queda sin verificación de marca y Meta no puede pasar a modo activo. Redáctalos y publícalos en el dominio del estudio antes de abrir el acceso social al público.

**Google.**

- Publicar la app con solo `openid`, `email` y `profile` no exige verificar ámbitos. Pero sin **verificación de marca** (Branding y Verification Center) la pantalla muestra el dominio del callback (`<proyecto>.supabase.co`) en lugar del nombre y el logo.
- La verificación de marca pide: página principal pública que describa la app (no solo un acceso); política de privacidad en el mismo dominio, que explique el uso de los datos de Google; enlace a los términos; dominios autorizados verificados en Google Search Console por un propietario o editor del proyecto; logo cuadrado de 120 × 120 px, de 1 MB como máximo, sin marcas de Google. Tarda de minutos a 2-3 días hábiles.
- Supabase recomienda un dominio propio para Auth (p. ej. `auth.<dominio>`), que además es el que vería la persona.
- El cliente de producción no lleva orígenes de `localhost`.

**Meta.**

- App settings → Basic: URL de la política de privacidad (obligatoria), URL de los términos y dominio de la app. Completa lo que el panel marque como pendiente.
- Eliminación de datos: Meta exige ofrecer una forma de pedir el borrado. Hay dos opciones: una URL con instrucciones, o un callback HTTPS que borre los datos y responda `url` y `confirmation_code`. El backend no tiene ese callback, así que la opción viable es la URL de instrucciones.
- Con solo `email` y `public_profile` no suele hacer falta una revisión detallada; si Meta la pide, tarda de 1 a 5 días hábiles. Algunas funciones piden verificar el negocio.

## Errores frecuentes

| Error | Causa y arreglo |
|---|---|
| `redirect_uri_mismatch` (Google) | La URI de Clients no coincide con el callback: `http`/`https`, `127.0.0.1`/`localhost`, puerto o barra final. Corrígela y espera unos minutos |
| "URL bloqueada" (Meta) | Falta el callback en Valid OAuth Redirect URIs o están desactivados Client/Web OAuth login. En local, `localhost`, no `127.0.0.1` |
| "App not active" o "App not set up" (Meta) | Modo desarrollo y la persona no tiene rol: añádela como probador o pasa a modo activo |
| `access_denied` o "app no verificada" (Google) | Estado Testing con algún ámbito extra: deja solo los tres básicos o añade la cuenta como usuario de prueba |
| `provider is not enabled` | `enabled = false` o no reiniciaste el stack tras cambiar `config.toml` |
| `invalid_client` | ID o secreto erróneos o sin cargar: revisa `supabase/.env` y reinicia |
| Vuelve sin sesión o a otra URL | El destino no está en `site_url` ni en `additional_redirect_urls` |
| No aparece el botón | El proveedor no está en `PUBLIC_ACCESO_PROVEEDORES` o no reconstruiste el frontend |
| Error al obtener el correo | Cuenta de Facebook sin correo, o permiso `email` sin añadir |

## Rotar o revocar un secreto

- **Google:** Clients → el cliente → **Add secret** (dos como máximo). Pon el nuevo en `supabase/.env` o en el panel, reinicia y prueba un acceso. Después **Disable** y borra el antiguo (no se puede deshacer). Si se filtró, desactívalo ya. Borrar el cliente corta todo el acceso con Google.
- **Meta:** App settings → Basic → App Secret → **Reset**. Trata el anterior como inválido desde ese momento: actualiza `supabase/.env` o el panel y reinicia a la vez.
- Nunca pegues un secreto en un commit, issue, chat o captura. Si llega al repositorio, rótalo: borrarlo del historial no basta.

Fuentes: [Supabase, Google](https://supabase.com/docs/guides/auth/social-login/auth-google) · [Supabase, Facebook](https://supabase.com/docs/guides/auth/social-login/auth-facebook) · [Google, público de la app](https://support.google.com/cloud/answer/15549945) · [Google, clientes OAuth](https://support.google.com/cloud/answer/15549257) · [Google, verificación de marca](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification) · [Meta, crear app](https://developers.facebook.com/docs/development/create-an-app/) · [Meta, modos de la app](https://developers.facebook.com/docs/development/build-and-test/app-modes/) · [Meta, eliminación de datos](https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback/) · [Meta, HTTPS obligatorio](https://developers.facebook.com/blog/post/2018/06/08/enforce-https-facebook-login/) (consultadas el 2026-11-16).
