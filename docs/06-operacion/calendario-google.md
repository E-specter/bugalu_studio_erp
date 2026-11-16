---
id: operacion-calendario-google
titulo: Calendario de Google y Meet con la cuenta personal del estudio
estado: borrador
depende_de: [RF-19, RF-15, RF-04, ADR-007, ADR-011, ADR-014, operacion-correo-gmail]
---

# Calendario de Google y Meet con la cuenta personal del estudio

Investigación para [RF-19](../03-requerimientos/RF-19.md) (2026-11-16). Lo que se busca: las reservas de sala ([RF-04](../03-requerimientos/RF-04.md)) y las asesorías ([RF-15](../03-requerimientos/RF-15.md)) confirmadas se crean como eventos en el calendario de la cuenta de Google del estudio ([ADR-011](../00-proyecto/decisiones/ADR-011-correo-gmail-del-estudio.md)), las asesorías virtuales llevan enlace de Meet y cada correo de confirmación adjunta un `.ics`. La cuenta es personal (Gmail), no Google Workspace. **Nada está decidido todavía:** no hay ADR ni código, y el procedimiento del final es una propuesta.

## 1. ¿Sirve una cuenta de servicio?

Sirve para eventos sin invitados, pero no para lo que pide RF-19.

- Se le puede compartir el calendario del estudio con el permiso de hacer cambios en eventos. Crea eventos sin pantalla de consentimiento y sin verificación.
- **No puede añadir invitados.** La referencia de `Events` dice: "Service accounts need to use domain-wide delegation of authority to populate the attendee list". La delegación de dominio solo existe en Workspace.
- **Meet:** ninguna página oficial dice que funcione. Hay informes de la comunidad de que falla (`Invalid conference type value`). Y aunque se creara, solo el organizador aprueba a quien pide unirse, así que sin invitados en el evento el profesional y el cliente se quedarían esperando (sección 2).
- Google desaconseja que una cuenta de servicio sea dueña de los datos de calendario, porque la propiedad no se puede transferir. Además, su clave JSON es un secreto que no caduca.

## 2. OAuth con la cuenta del estudio

El estudio da su consentimiento una vez y el backend guarda el **token de actualización**. Con él pide tokens de acceso de corta duración.

**Ámbito.** Google pide elegir el más estrecho posible.

| Ámbito (`https://www.googleapis.com/auth/…`) | Qué permite | Uso |
|---|---|---|
| `calendar.app.created` | Crear calendarios secundarios y gestionar solo sus eventos | Preferido: un calendario propio de la plataforma dentro de la cuenta, sin tocar el principal |
| `calendar.events.owned` | Crear, cambiar y borrar eventos en los calendarios de la cuenta | Alternativa, si Meet no funciona en el secundario |
| `calendar.events` | Ver y editar eventos de todos los calendarios a los que accede | Más de lo necesario |

**¿Es sensible?** Google pone "leer eventos de Google Calendar" como ejemplo de ámbito sensible. Un ámbito sensible exige verificación si la app es pública, pero no la evaluación de seguridad que piden los restringidos. La página de ámbitos de Calendar no clasifica cada ámbito: la consola lo muestra al añadirlo. El plan sirve en los dos casos.

| | Testing | In production sin verificar |
|---|---|---|
| Quién autoriza | Hasta 100 usuarios de prueba | Cualquier cuenta de Google |
| Token de actualización | **Caduca a los 7 días** con cualquier ámbito que no sea nombre, correo o perfil | El estado no lo hace caducar |
| Pantalla | Aviso de app en pruebas | "Google no ha verificado esta app": se sigue con **Advanced → Go to … (unsafe)** |
| Tope | 100 usuarios de prueba | 100 usuarios nuevos en toda la vida del proyecto; no se reinicia |

Testing no sirve, porque obligaría a dar el consentimiento cada semana. In production sin verificar sí sirve: el único usuario es el estudio, y Google exime de verificar el **uso personal** (menos de 100 usuarios, que pasan el aviso). Aun así, la app debe cumplir la política de datos de usuario de las API de Google.

**Meet.** En `events.insert` o `events.patch`, con el parámetro `conferenceDataVersion=1`:

```json
"conferenceData": {"createRequest": {"requestId": "<único por evento>", "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
```

- Es asíncrono: `createRequest.status.statusCode` empieza en `pending` y pasa a `success`. El enlace queda en `hangoutLink` y en `conferenceData.entryPoints`.
- `eventHangout` (Hangouts para cuentas personales) está obsoleto y ya no crea conferencias, así que `hangoutsMeet` es el único tipo de Google. Ninguna página dice expresamente que funcione con una cuenta personal: compruébalo con el evento de prueba del paso 8.
- Cada evento lleva su propio `createRequest`. Google desaconseja reutilizar el `conferenceData` de otro evento, por privacidad.
- **Meet gratuito:** hasta 100 participantes y 60 minutos por reunión. Las llamadas individuales no tienen límite. Una asesoría de 90 min con tres personas se corta a los 60.
- **Entrada:** solo el organizador (la cuenta del estudio) aprueba a quien pide unirse. Los invitados del evento entran directamente si usan esa cuenta de Google. Por eso el profesional y el cliente van en `attendees`. Quien no tenga cuenta de Google se quedará esperando, salvo que alguien entre con la cuenta del estudio.

## 3. Producción con el servidor local sin dominio

- La API solo necesita conexiones HTTPS salientes del servidor a Google. No hacen falta dominio ni puerto abierto ([ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md)).
- El consentimiento se da una vez con un cliente OAuth **Desktop app** (flujo de app instalada, con PKCE) que redirige a `http://127.0.0.1:<puerto>`. No hacen falta dominio ni URI pública. El copiar y pegar del código (OOB) ya no existe.
- La verificación pide dominio verificado en Search Console, página principal pública, política de privacidad en ese dominio, justificar cada ámbito y un vídeo, y tarda hasta 10 días. Solo haría falta para abrir la conexión a terceros, por ejemplo si cada profesional conectara su propio calendario. No en la v1.
- Usa un proyecto de Google Cloud distinto del de acceso social ([credenciales-oauth](credenciales-oauth.md)), para que la verificación de marca de ese proyecto no cargue con un ámbito sensible sin verificar.
- Los textos legales ([ADR-012](../00-proyecto/decisiones/ADR-012-textos-legales-y-consentimientos.md)) deben decir que los datos de la cita pasan a Google Calendar y Meet. El evento lleva solo lo necesario: folio, servicio y nombre de pila; nunca teléfono ni pagos.

## 4. Archivo `.ics`

- **Mínimos** (RFC 5545 y 5546): en `VCALENDAR`, `VERSION:2.0`, `PRODID` y `METHOD`. En `VEVENT`, `UID`, `DTSTAMP` (en UTC, el momento en que se genera), `DTSTART`, `DTEND`, `SUMMARY`, `ORGANIZER` (la cuenta del estudio), `ATTENDEE` (el cliente; obligatorio con REQUEST) y `SEQUENCE`. El lugar va en `LOCATION`. El enlace de Meet va en `DESCRIPTION`, porque no todos los clientes muestran `CONFERENCE` (RFC 7986).
- **UID estable:** un UUID por reserva o asesoría, guardado en su fila. RFC 7986 recomienda UUID y desaconseja incluir nombres de host, así que no necesita dominio. Si se usa también como `iCalUID` del evento de Google, el calendario del cliente no debería duplicarlo (por probar). Google admite `iCalUID` o `id` al crear el evento, pero no los dos.
- **Hora:** `DTSTART:20261120T150000Z` (en UTC) evita `VTIMEZONE`. Con `TZID=America/Lima`, RFC 5545 obliga a incluir su `VTIMEZONE` (Perú tiene UTC−5 fijo, sin horario de verano). En la API: `{"dateTime": "2026-11-20T10:00:00-05:00", "timeZone": "America/Lima"}`.
- **REQUEST o PUBLISH:** REQUEST es una invitación, con botones para responder (la respuesta llega al Gmail del estudio), y se puede actualizar o cancelar por correo con el mismo `UID`. PUBLISH solo informa, y los clientes de correo tratan sus actualizaciones de forma irregular. **Propuesta: REQUEST.**
- **Cambios:** en cada reprogramación ([RF-18](../03-requerimientos/RF-18.md)), mismo `UID`, `SEQUENCE` +1 y `DTSTAMP` nuevo. Para cancelar: `METHOD:CANCEL`, `STATUS:CANCELLED` y `SEQUENCE` +1.
- **En el correo** (RFC 6047): una parte `text/calendar; method=REQUEST; charset=UTF-8` (el `method` debe coincidir con `METHOD`) y el mismo contenido como adjunto `.ics`. Líneas con CRLF, de 75 octetos como máximo, y `,`, `;`, `\` y los saltos de línea escapados.
- **¿Basta sin la API?** Para el cliente sí, porque pone la cita en su calendario. Pero no llena la agenda del estudio ni crea el Meet: sin la API, el profesional tendría que crear el enlace a mano.
- Gmail, Outlook y Apple no documentan cómo tratan estas invitaciones. Prueba el alta, el cambio y la cancelación en los tres.

## 5. Recomendación para la v1

**`.ics` siempre, más la API con OAuth de la cuenta del estudio, en In production sin verificar.**

- El `.ics` se genera con la biblioteca estándar. La API se llama con `httpx`, que el backend ya usa (`oauth2.googleapis.com/token` y `www.googleapis.com/calendar/v3`): no hacen falta dependencias nuevas.
- El evento se crea desde una bandeja con reintentos, como los correos. Si Google falla, la confirmación no se bloquea y el `.ics` sale igual. En una asesoría virtual, el correo espera el enlace de Meet o lo envía en un segundo aviso.
- La reserva de sala es un evento sin invitados. La asesoría lleva al profesional y al cliente en `attendees`. Con `sendUpdates=none`, Google no envía su propia invitación (el correo del ERP ya lleva el `.ics`), pero Google advierte que `none` puede hacer que el evento no se sincronice o se pierda en algunos calendarios. El ADR elige entre `none` y `all` (que manda dos correos).
- Mantenimiento: un proyecto de Google Cloud, un token, una comprobación diaria y volver a dar el consentimiento (unos 5 min) si se revoca. Es gratis por debajo de 1 000 000 de peticiones diarias por proyecto. Google anuncia que cobrará el exceso de cuota, con 90 días de aviso.

| Riesgo | Efecto y mitigación |
|---|---|
| Token revocado: el estudio quita el acceso, o se pasa de 100 tokens por cliente y cae el más antiguo | `invalid_grant` al renovar, y los eventos dejan de crearse. Avisa al Administrador y repite el paso 7 |
| Cambio de contraseña | Solo revoca los tokens con ámbitos de Gmail, así que el de Calendar sigue. Sí revoca las contraseñas de aplicación SMTP ([correo-gmail](correo-gmail.md)) |
| Seis meses sin usar el token | Caduca. La comprobación diaria lo mantiene vivo y detecta las revocaciones |
| Acceso por tiempo limitado | Si al dar el consentimiento se elige un plazo, el acceso caduca. Elige sin plazo |
| Cuotas | 600 peticiones por minuto por usuario y 10 000 por proyecto. Con 403 o 429 `rateLimitExceeded`, reintenta con espera exponencial. El estudio queda muy por debajo |
| Meet gratuito | Se corta a los 60 min con tres o más personas. Quien no tenga cuenta de Google depende del organizador para entrar |

**Guardar el token.** Va en `backend/.env` del servidor, como `SMTP_CLAVE`. Nunca en git, ni con valor en `.env.example` (ahí va vacío), ni en registros ni en errores. No va a la base de datos: leerlo desde una tarea de sistema exigiría un adaptador con rol de servicio ([ADR-007](../00-proyecto/decisiones/ADR-007-acceso-postgres-directo.md)). Nombres propuestos: `GOOGLE_CALENDARIO_CLIENTE_ID`, `GOOGLE_CALENDARIO_SECRETO`, `GOOGLE_CALENDARIO_TOKEN` y `GOOGLE_CALENDARIO_ID`. Google considera público el secreto de un cliente Desktop: lo que de verdad hay que proteger es el token, que abre el calendario. El archivo solo lo lee el usuario del servicio, y el token de acceso vive solo en memoria. Para revocarlo: Cuenta de Google → Seguridad → conexiones con apps de terceros, o `POST https://oauth2.googleapis.com/revoke`.

**Si se pasa a Google Workspace:** cuenta y calendario nuevos. Hay dos opciones:

- OAuth con público **Internal**: sin verificación, sin aviso y sin la caducidad de 7 días.
- Una cuenta de servicio con delegación de todo el dominio que actúe como la cuenta del estudio: añade invitados y crea Meet sin token de usuario.

Los planes de pago de Workspace permiten reuniones de grupo de hasta 24 h. Como el ERP es la fuente de verdad, un script vuelve a crear los eventos futuros. El `.ics` no cambia.

## 6. Procedimiento (propuesto, pendiente de aprobación)

Se hace con la cuenta del estudio. Los nombres de la consola van en inglés.

1. En `https://console.cloud.google.com`, crea un proyecto nuevo (p. ej. `bugalu-calendario`).
2. APIs & Services → Library → **Google Calendar API** → Enable.
3. **Google Auth Platform** → Get started. Nombre de la app sin marcas de Google. La cuenta del estudio como correo de asistencia y de contacto. Audience: **External** (Internal exige Workspace).
4. **Data Access** → Add or remove scopes → `.../auth/calendar.app.created` y guarda. Anota si la consola lo marca como sensible.
5. **Audience** → **Publish app** y confirma (In production). No lo envíes a verificación.
6. **Clients** → Create client → **Desktop app** (`bugalu-calendario-servidor`). Descarga el JSON y guárdalo fuera del repositorio.
7. **Consentimiento,** con una herramienta del backend que está por escribir. Úsala en un equipo con navegador y con solo la cuenta del estudio abierta. La herramienta abre la autorización con PKCE y redirección a `127.0.0.1`. En el aviso de app no verificada, sigue con **Advanced → Go to … (unsafe)** y permite el acceso al calendario. La herramienta canjea el código, crea el calendario secundario y muestra una sola vez el token y el ID del calendario. Si el servidor no tiene navegador, hazlo en otro equipo y lleva los valores por un canal seguro, nunca por correo ni chat.
8. Carga los valores en `backend/.env` y crea un evento de prueba con Meet. Debe aparecer en Google Calendar con su enlace. Después bórralo. Si Meet falla en el calendario secundario, repite desde el paso 4 con `calendar.events.owned` y el calendario `primary`.
9. Comprueba que la app aparece en Cuenta de Google → Seguridad → conexiones con apps de terceros.

## Sin confirmar

- Si `calendar.app.created` y `calendar.events.owned` son sensibles: la página de Calendar no los clasifica.
- Si `hangoutsMeet` funciona en una cuenta personal y en un calendario secundario: no hay frase oficial explícita. Con una cuenta de servicio, solo hay informes de la comunidad.
- La configuración de acceso de Meet por defecto en cuentas personales, si un invitado sin cuenta de Google puede entrar sin el organizador, y qué cuenta fija el límite de 60 min (se presume que la del organizador).
- Si Gmail, Outlook y Apple fusionan el `.ics` con la invitación de Google cuando comparten `UID`, y cómo tratan PUBLISH.
- Si los límites de uso de Calendar (artículo para administradores de Workspace) se aplican a cuentas personales, y qué muestra la consola al publicar con un ámbito sensible.

Fuentes: [Calendar, ámbitos](https://developers.google.com/workspace/calendar/api/auth) · [Calendar, crear eventos y conferencias](https://developers.google.com/workspace/calendar/api/guides/create-events) · [Calendar, recurso Events](https://developers.google.com/workspace/calendar/api/v3/reference/events) · [Calendar, events.insert](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert) · [Calendar, calendarios y eventos](https://developers.google.com/workspace/calendar/api/concepts/events-calendars) · [Calendar, cuotas](https://developers.google.com/workspace/calendar/api/guides/quota) · [Calendar, errores](https://developers.google.com/workspace/calendar/api/guides/errors) · [Calendar, límites de uso](https://knowledge.workspace.google.com/admin/calendar/avoid-calendar-use-limits) · [OAuth 2.0, caducidad de tokens](https://developers.google.com/identity/protocols/oauth2#expiration) · [OAuth, apps instaladas](https://developers.google.com/identity/protocols/oauth2/native-app) · [OAuth, servidores web](https://developers.google.com/identity/protocols/oauth2/web-server) · [Google, público de la app](https://support.google.com/cloud/answer/15549945) · [Google, apps no verificadas](https://support.google.com/cloud/answer/7454865) · [Google, excepciones a la verificación](https://support.google.com/cloud/answer/13464323) · [Google, verificación de ámbitos sensibles](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification) · [Meet, acceso a reuniones](https://support.google.com/a/users/answer/11989526) · [Meet, producto y plan gratuito](https://workspace.google.com/products/meet/) · [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545) · [RFC 5546](https://www.rfc-editor.org/rfc/rfc5546) · [RFC 6047](https://www.rfc-editor.org/rfc/rfc6047) · [RFC 7986](https://www.rfc-editor.org/rfc/rfc7986) (consultadas el 2026-11-16).
