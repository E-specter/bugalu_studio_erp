---
id: operacion-montaje-local
titulo: Montaje del entorno local
estado: borrador
depende_de: [operacion-entornos]
---

# Montaje del entorno local

## Requisitos

- Docker Desktop en marcha y Node.js (para `npx supabase`).
- Python 3.14 y [`uv`](https://docs.astral.sh/uv/) (`requires-python >= 3.14`).
- Node.js 22.23 o superior (Astro 7) y `npm` para el frontend.
- Claude Code con los MCP de [herramientas-mcp](herramientas-mcp.md).

## Backend

Desde la raíz del repositorio:

```bash
npx supabase start          # stack propio de Bugalú (project_id "bugalu", puertos 456xx)
npx supabase db reset       # aplica las migraciones de supabase/migrations
npx supabase status         # URLs y claves del stack local
cd backend
cp .env.example .env        # y completa los valores con `npx supabase status`
uv sync
uv run python -m bugalu     # API en http://127.0.0.1:8000 (docs en /docs)
```

Variables de `backend/.env` (`.env` está ignorado por git):

| Variable | Origen |
|---|---|
| `URL_BASE_DATOS` | Obligatoria, sin valor por defecto: la API no arranca si falta. Conecta como `bugalu_api` (rol sin superusuario ni `bypassrls`, creado por la migración `rol_conexion_api`; su contraseña de desarrollo `bugalu_api_dev` la fija `supabase/seed.sql`, solo local): `postgresql://bugalu_api:bugalu_api_dev@127.0.0.1:45622/postgres` |
| `URL_BASE_DATOS_ADMIN` | Solo pruebas: `DB_URL` de `npx supabase status` (superusuario `postgres`). Las fixtures la usan para borrar usuarios y subir roles; la API nunca |
| `TIMEOUT_POOL_SEGUNDOS` | Opcional (5): espera por una conexión del pool; si vence, 503 `base_de_datos_no_disponible` |
| `URL_SUPABASE` | Obligatoria. `API_URL` (puerto 45621); de ahí sale el JWKS con el que se verifican los JWT (espera máxima 5 s; si falla o no es JSON, 503 `autenticacion_no_disponible`) |
| `CLAVE_PUBLICABLE_SUPABASE` | `PUBLISHABLE_KEY`; **obligatoria**: la API la envía como `apikey` a Storage junto al token del usuario (RF-05) y las pruebas la usan para el alta de usuarios |
| `CLAVE_SERVICIO_SUPABASE_PRUEBAS` | Solo pruebas: `SERVICE_ROLE_KEY` local. Las pruebas de pagos la leen directamente del entorno (o de `backend/.env`) y borran con ella, por la API de Storage, los objetos que crean; `Configuracion` y `src/` no la conocen, ni existe en producción |
| `EXIGIR_INTEGRACION` | Solo pruebas, opcional. `EXIGIR_INTEGRACION=1` (CI) convierte el salto de las pruebas de integración, cuando no hay stack o `.env`, en fallo. Sin ella se saltan con el motivo. Las pruebas unitarias no dependen de `backend/.env` |
| `ORIGENES_PERMITIDOS` | Orígenes del frontend, separados por comas (`http://localhost:4321`). Vacío = sin CORS: el navegador bloquea las llamadas del frontend |
| `SMTP_HOST` / `SMTP_PUERTO` | Servidor de correo de la bandeja `notificacion`. En local, Mailpit: `127.0.0.1` y `45625` (`[local_smtp] smtp_port` en `supabase/config.toml`); los correos se ven en `http://127.0.0.1:45624`. Sin STARTTLS ni credenciales (el proveedor real sigue en D-07) |
| `CORREO_REMITENTE` | Remitente de los avisos de reserva |
| `INTERVALO_ENVIO_CORREOS` | Segundos entre envíos de la tarea periódica de la API (por defecto 30; `0` la desactiva, como en las pruebas). Para enviar una vez a mano: `uv run python -m bugalu.herramientas.enviar_correos` |

**Auth (RF-01, `supabase/config.toml`):** contraseña de 8+ caracteres con minúscula, mayúscula, número y símbolo. Tras cambiar `config.toml`: `npx supabase stop` y `npx supabase start`. Las pruebas de integración y cualquier alta usan contraseñas que lo cumplan (p. ej. `Clave-Segura-123`).

**Verificación del correo (CA-06):** el CLI local no permite iniciar sesión con el correo sin confirmar, así que `enable_confirmations = false` (Supabase confirma al registrar) y la verificación se lleva en `usuario.correo_verificado_en`: el perfil pide un enlace de un solo uso (llega a Mailpit, `http://127.0.0.1:45624`) y el backend la registra. Ver [ADR-008](../00-proyecto/decisiones/ADR-008-acceso-y-roles-v1.md).

**Google (desactivado por defecto):** crea un cliente OAuth en Google Cloud Console con `http://127.0.0.1:45621/auth/v1/callback` como URI de redirección, copia `supabase/.env.example` a `supabase/.env` (ignorado por git; el CLI lo lee al arrancar) con `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID` y `SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET`, pon `enabled = true` en `[auth.external.google]` y reinicia el stack.

**Primer administrador (CA-11):** con el usuario ya registrado y `URL_BASE_DATOS_ADMIN` en `backend/.env`, desde `backend/`: `uv run python -m bugalu.herramientas.crear_administrador <correo>`. Es idempotente; si el correo no existe, falla con un mensaje claro.

PostgREST (`/rest/v1`) no expone `public` (`[api] schemas = ["graphql_public"]` en `supabase/config.toml`; la lista vacía vuelve al valor por defecto, que incluye `public`): `GET /rest/v1/usuario` da 404 `PGRST205` y `POST /rest/v1/rpc/es_administrador` da 404 `PGRST202`. Los datos solo se leen por el backend (ADR-007). Tras cambiar `config.toml`: `npx supabase stop` y `npx supabase start`. Auth redirige al frontend (`site_url` `http://localhost:4321`, más `http://127.0.0.1:4321`).

Comprueba que responde con `curl -i http://127.0.0.1:8000/api/v1/perfil`: sin token devuelve 401.

**Arranque con `python -m bugalu`, no con `fastapi dev`:** en Windows, uvicorn usa por defecto un bucle de eventos (`ProactorEventLoop`) con el que `psycopg` asíncrono no funciona. `bugalu/__main__.py` arranca uvicorn con la fábrica `bugalu.main:crear_app` (no hay `app` de módulo: importar `bugalu.main` no exige `.env`), con un bucle compatible (`compartido/bucle.py`) y recarga automática.

## Frontend

Astro estático con `npm`, desde `frontend/`:

```bash
cd frontend
npm install
cp .env.example .env        # y completa la clave publicable (abajo)
npm run dev                 # http://localhost:4321
```

Variables de `frontend/.env` (ignorado por git; solo `PUBLIC_*`, llegan al navegador):

| Variable | Origen |
|---|---|
| `PUBLIC_URL_API` | Backend de desarrollo, `http://127.0.0.1:8000` |
| `PUBLIC_URL_SUPABASE` | `API_URL` de `npx supabase status` (puerto 45621): la sesión se lee de ahí |
| `PUBLIC_CLAVE_PUBLICABLE_SUPABASE` | `PUBLISHABLE_KEY` de `npx supabase status`. Nunca pongas la clave secreta ni la de servicio |

Para que el navegador pueda llamar al backend, añade `ORIGENES_PERMITIDOS=http://localhost:4321` a `backend/.env` y reinicia la API. Sin sesión, `http://localhost:4321/app/perfil` muestra el estado "Tu sesión no es válida" (la pantalla de acceso llega con RF-01).

Calidad y pruebas:

```bash
npm run check               # tokens, literales visuales y astro check
npm run build               # salida estática en dist/
npm run test:e2e            # Playwright + axe; construye el sitio y simula la API con page.route
```

`test:e2e` no necesita backend ni Supabase (usa valores ficticios) y deja capturas en `frontend/pruebas/capturas/`. La primera vez, instala el navegador con `npx playwright install chromium`. `/catalogo` existe en `npm run dev` y en el build de pruebas (`PUBLIC_CATALOGO=1`, en `dist-pruebas/`, lo activa `test:e2e`); nunca en `npm run build`.

**Recorrido real de RF-01 (sin `page.route`):** `npm run test:e2e:real` (aparte de `test:e2e`, que lo ignora). Necesita el stack de Supabase local con Mailpit, `backend/.env` (con `URL_BASE_DATOS_ADMIN`) y `frontend/.env`, y `uv` instalado. La config `playwright.real.config.js` levanta el backend en el puerto 8010 (`uvicorn`, sin tocar el 8000) y `astro dev` en `localhost:4321` (el único origen al que Auth redirige) con `PUBLIC_URL_API` apuntando al 8010; el puerto 4321 debe estar libre. `frontend/pruebas/real/rf01.real.spec.js` registra tres usuarios `rf01-*@prueba.bugalu.pe`, lee Mailpit por su API, promueve a uno con `crear_administrador` y, al terminar (pase o falle), `limpiar.py` los borra con `URL_BASE_DATOS_ADMIN` y comprueba que no quedan huérfanos. Sin stack, se salta; con `EXIGIR_INTEGRACION` definida, falla. Las capturas quedan en `frontend/pruebas/capturas/real-rf01-*.png`.

**Recorrido real de reservas (sin `page.route`):** el mismo `npm run test:e2e:real` ejecuta también `frontend/pruebas/real/reservas.real.spec.js` (RF-02 CA-05, RF-03, RF-04). Necesita lo mismo que RF-01 más la bandeja de correos: la config real arranca el backend con `INTERVALO_ENVIO_CORREOS=2` (SMTP por defecto `127.0.0.1:45625`, el de Mailpit) para que `reserva_creada` y `reserva_caducada` lleguen a Mailpit en segundos; si lo lanzas a mano, usa esa variable o `uv run python -m bugalu.herramientas.enviar_correos`. Las fechas se calculan desde ahora en Lima (martes y miércoles de la semana siguiente, dentro de la ventana de 2 h a 8 semanas), así que no depende del día en que se corra. Seis pasos en serie: (1) un Administrador (promovido con `crear_administrador`) publica franjas en `/app/franjas/` desde la plantilla editable; (2) un visitante elige horario, servicio y un especialista adicional en `/reservar/`, el total de la simulación coincide con `POST /simulaciones`, se registra desde el acceso y confirma; (3) el correo llega a Mailpit con folio y fecha límite; (4) `/app/reservas/`, tramo OCUPADO para otro cliente sin datos del primero y agenda del Administrador; (5) cancelación desde el detalle y tramo libre; (6) caducidad: `frontend/pruebas/real/caducar.py <folio>` pone `vence_pago` en el pasado y corre `caducar_reservas()` con `URL_BASE_DATOS_ADMIN`. Requiere el catálogo del seed (sala, "Grabación de voces", "Productor o arreglista") y que la semana siguiente no tenga franjas publicadas. Al terminar (pase o falle), `limpiar.py` borra usuarios `res-*@prueba.bugalu.pe`, reservas (con cuotas y especialistas), avisos, franjas y cierres que crearon y comprueba que no quedan huérfanos. Capturas: `frontend/pruebas/capturas/real-reservas-*.png`.

**Requisito de despliegue (pagos):** el servidor o proxy de producción debe limitar el tamaño del cuerpo de `POST /api/v1/pagos` (p. ej. 5,1 MB). `LimitePagos` solo rechaza por `Content-Length`; sin esa cabecera (chunked) Starlette vuelca el multipart a disco antes del 413.

**Recorrido real de pagos (sin `page.route`):** el mismo `npm run test:e2e:real` ejecuta `frontend/pruebas/real/pagos.real.spec.js` (RF-05 CA-01..09, RF-06 CA-01..05). Necesita lo de reservas más `CLAVE_SERVICIO_SUPABASE_PRUEBAS` (entorno o `backend/.env`; sin ella se salta, o falla con `EXIGIR_INTEGRACION`) y los métodos de pago activos del seed (Yape, contacto del estudio). Seis pasos en serie, con usuarios `pag-*@prueba.bugalu.pe`: (1) el Administrador publica franjas y el cliente reserva; (2) el cliente registra el pago de `al_reservar` con un PNG real y ve "Pago en validación" y "Pago por validar"; llega `pago_registrado` al Administrador; (3) el Administrador ve el contador de PAGOS, la captura cargada desde la URL firmada de Storage y rechaza con motivo; llega `pago_rechazado` y el detalle muestra el motivo; (4) el cliente registra otro pago con un PDF y ve el aviso y el contacto del estudio en lugar de Cancelar; el Administrador lo aprueba, la reserva queda Confirmada y llega `pago_aprobado` con "confirmada"; (5) el Administrador cancela con nota obligatoria; el cliente ve la nota y llega `reserva_cancelada_estudio`; (6) `frontend/pruebas/real/finalizar.py <folio>` deja una segunda reserva confirmada con la sesión ya terminada (SQL de administración, en medias horas) y corre `avanzar_reservas()`: `Finalizada` con `reserva_finalizada_saldo`, saldo y "Registrar pago" en el historial. Al terminar (pase o falle), `capturas.py` lista los ids de los usuarios, se borran sus objetos de `comprobantes` por la API de Storage con la clave de servicio, `limpiar.py` borra usuarios, reservas, cuotas, comprobantes, avisos y franjas, y el recorrido falla si queda algún huérfano en la base o en el bucket. El número de operación se guarda en mayúsculas. Capturas: `frontend/pruebas/capturas/real-pagos-*.png`.

## Calidad (desde `backend/`)

```bash
uv run pytest               # unitarias + integración contra el stack local
uv run pytest -m "not integracion"   # solo unitarias (no necesitan Supabase)
uv run ruff check .
uv run mypy src
```

Las pruebas de integración se saltan, con un mensaje, si el stack local no responde. Pruebas de la base de datos (pgTAP), desde la raíz: `npx supabase test db`.

## Verificación de la documentación

```bash
python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md
python -m unittest scripts/test_validar_docs.py
```
