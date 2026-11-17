---
id: operacion-montaje-local
titulo: Montaje del entorno de desarrollo
estado: borrador
depende_de: [operacion-entornos]
---

# Montaje del entorno de desarrollo

De cero a la app funcionando en un equipo con Windows. Pruebas: [pruebas-locales](pruebas-locales.md). Servicios y puertos del stack: [entornos](entornos.md#servicios-del-stack-local-de-supabase). Producción: [produccion](produccion.md).

## Requisitos

- Git y Docker Desktop (con WSL 2) en marcha.
- Node.js 22.23 o superior (Astro 7) con `npm`; también da `npx supabase` (CLI 3).
- Python 3.14 y [`uv`](https://docs.astral.sh/uv/) (`requires-python >= 3.14`).
- Claude Code con los MCP de [herramientas-mcp](herramientas-mcp.md).

## 1. Clonar y levantar Supabase

Las órdenes `npx supabase` se lanzan siempre desde la raíz del repositorio:

```bash
git clone <URL del repositorio> bugalu_studio_erp
cd bugalu_studio_erp
npx supabase start          # stack propio de Bugalú (project_id "bugalu", puertos 456xx)
npx supabase db reset       # aplica supabase/migrations y supabase/seed.sql
npx supabase status         # URLs y claves del stack local
```

La primera vez descarga las imágenes de Docker (varios minutos). `supabase/seed.sql` es solo de desarrollo: fija la contraseña `bugalu_api_dev` del rol de la API y carga datos para pagar y contacto de ejemplo.

## 2. Backend

```bash
cd backend
cp .env.example .env        # completa las claves con `npx supabase status`
uv sync
uv run python -m bugalu     # API en http://127.0.0.1:8000 (docs en /docs)
curl -i http://127.0.0.1:8000/api/v1/perfil   # sin token devuelve 401
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
| `ORIGENES_PERMITIDOS` | Orígenes del frontend, separados por comas (`http://localhost:4321,http://127.0.0.1:4321`). Vacío = sin CORS: el navegador bloquea las llamadas del frontend |
| `SMTP_HOST` / `SMTP_PUERTO` | Servidor de correo de la bandeja `notificacion`. En local, Mailpit: `127.0.0.1` y `45625` (`[local_smtp] smtp_port` en `supabase/config.toml`); los correos se ven en `http://127.0.0.1:45624` |
| `SMTP_USUARIO` / `SMTP_CLAVE` / `SMTP_STARTTLS` | Vacías en local (Mailpit, sin credenciales). En producción, la cuenta de Google del estudio: [correo-gmail](correo-gmail.md) |
| `CORREO_REMITENTE` | Remitente de los avisos de reserva |
| `INTERVALO_ENVIO_CORREOS` | Segundos entre envíos de la tarea periódica de la API (por defecto 30; `0` la desactiva, como en las pruebas). Para enviar una vez a mano: `uv run python -m bugalu.herramientas.enviar_correos` |

**Arranque con `python -m bugalu`, no con `fastapi dev`:** en Windows, uvicorn usa por defecto un bucle de eventos (`ProactorEventLoop`) con el que `psycopg` asíncrono no funciona. `bugalu/__main__.py` arranca uvicorn con la fábrica `bugalu.main:crear_app` (no hay `app` de módulo: importar `bugalu.main` no exige `.env`), con un bucle compatible (`compartido/bucle.py`) y recarga automática.

## 3. Frontend

Astro estático con `npm`:

```bash
cd frontend
npm install
cp .env.example .env        # completa la clave publicable
npm run dev                 # http://localhost:4321
```

Variables de `frontend/.env` (ignorado por git; solo `PUBLIC_*`, llegan al navegador y se leen al construir):

| Variable | Origen |
|---|---|
| `PUBLIC_URL_API` | Backend de desarrollo, `http://127.0.0.1:8000` |
| `PUBLIC_URL_SUPABASE` | `API_URL` de `npx supabase status` (puerto 45621): la sesión se lee de ahí |
| `PUBLIC_CLAVE_PUBLICABLE_SUPABASE` | `PUBLISHABLE_KEY` de `npx supabase status`. Nunca pongas la clave secreta ni la de servicio |
| `PUBLIC_ACCESO_PROVEEDORES` | Botones de acceso social (`google`, `facebook`); vacío = ninguno ([credenciales-oauth](credenciales-oauth.md)) |

Sin sesión, `http://localhost:4321/app/perfil` muestra "Tu sesión no es válida"; regístrate o entra desde `http://localhost:4321/acceso/`.

## 4. Primer administrador (CA-11)

Con el usuario ya registrado y `URL_BASE_DATOS_ADMIN` en `backend/.env`, desde `backend/`: `uv run python -m bugalu.herramientas.crear_administrador <correo>`. Es idempotente; si el correo no existe, falla con un mensaje claro.

## 5. Textos legales (RF-17)

Tras cada `npx supabase db reset` los textos legales quedan vacíos. Desde `backend/`, con `URL_BASE_DATOS_ADMIN` en `.env`: `uv run python -m bugalu.herramientas.cargar_textos_legales [carpeta]`. Publica, vigente ya, la primera versión de cada texto sin versiones desde `docs/08-legal/` (versión del frontmatter; condiciones con el anexo de propiedad intelectual; resúmenes de `resumenes-para-pantallas.md`). Es idempotente y no toca un texto que ya tenga versiones. En producción se corre una vez, con los textos ya aprobados por el abogado.

## Configuración de Supabase que conviene conocer

Tras cambiar `supabase/config.toml`: `npx supabase stop` y `npx supabase start`.

- **Auth (RF-01):** contraseña de 8+ caracteres con minúscula, mayúscula, número y símbolo. Las pruebas de integración y cualquier alta usan contraseñas que lo cumplan (p. ej. `Clave-Segura-123`). Auth redirige al frontend (`site_url` `http://localhost:4321`, más `http://127.0.0.1:4321`).
- **Verificación del correo (CA-06):** el CLI local no permite iniciar sesión con el correo sin confirmar, así que `enable_confirmations = false` (Supabase confirma al registrar) y la verificación se lleva en `usuario.correo_verificado_en`: el perfil pide un enlace de un solo uso (llega a Mailpit, `http://127.0.0.1:45624`) y el backend la registra. Ver [ADR-008](../00-proyecto/decisiones/ADR-008-acceso-y-roles-v1.md).
- **Google y Meta (desactivados por defecto):** el cliente OAuth, `supabase/.env` (copia de `supabase/.env.example`, ignorado por git) y `enabled = true` en `[auth.external.google]` o `[auth.external.facebook]`: [credenciales-oauth](credenciales-oauth.md).
- **PostgREST** (`/rest/v1`) no expone `public` (`[api] schemas = ["graphql_public"]`; la lista vacía vuelve al valor por defecto, que incluye `public`): `GET /rest/v1/usuario` da 404 `PGRST205` y `POST /rest/v1/rpc/es_administrador` da 404 `PGRST202`. Los datos solo se leen por el backend (ADR-007).
- **Requisito de despliegue (pagos):** `LimitePagos` solo rechaza `POST /api/v1/pagos` por `Content-Length`; sin esa cabecera (chunked) Starlette vuelca el multipart a disco antes del 413. En producción el proxy limita el cuerpo: [produccion-servicios](produccion-servicios.md#proxy-inverso-con-límite-de-cuerpo).

## Problemas frecuentes

- **Docker apagado:** `npx supabase start` falla al conectar con el demonio de Docker y las pruebas de integración se saltan ("stack local no responde"). Abre Docker Desktop, espera a que diga que está en marcha y repite.
- **Puertos excluidos de Windows:** `Ports are not available ... bind: An attempt was made to access a socket in a way forbidden by its access permissions` al arrancar el stack. Hyper-V y WSL reservan bloques de puertos que cambian tras cada reinicio. Míralos con `netsh interface ipv4 show excludedportrange protocol=tcp`. Si un bloque cubre los 456xx, en una consola de administrador: `net stop winnat`, `npx supabase start` y `net start winnat`.
- **El stack `valmont` (puertos 543xx) es de otro proyecto:** no lo pares ni lo borres. Nunca uses `npx supabase stop --all`. `docker ps` muestra los contenedores con sufijo `_bugalu` o `_valmont`; antes de usar el MCP, `npx supabase status` debe mostrar la API en 45621.
- **La API no arranca con `Configuracion invalida: falta ...`:** falta una variable obligatoria en `backend/.env`.
- **503 `autenticacion_no_disponible` o `base_de_datos_no_disponible`:** el stack está parado o `URL_SUPABASE`/`URL_BASE_DATOS` no apuntan a los 456xx.
- **El navegador bloquea las llamadas (CORS):** el origen del frontend no está en `ORIGENES_PERMITIDOS`; añádelo y reinicia la API.
- **Puerto ocupado en las pruebas:** `test:e2e` usa 4321 y 4322 (cámbialos con `PUERTO_PRUEBAS`, p. ej. `4331`); `test:e2e:real` necesita el 4321 libre: para `npm run dev` antes.
- **Un cambio de `config.toml` o de `supabase/.env` no surte efecto:** reinicia el stack. Un cambio de `frontend/.env` exige reiniciar `npm run dev` o reconstruir.
