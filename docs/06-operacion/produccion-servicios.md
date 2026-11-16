---
id: operacion-produccion-servicios
titulo: Backend, frontend y proxy en producción
estado: borrador
depende_de: [operacion-produccion, operacion-produccion-supabase]
---

# Backend, frontend y proxy en producción

Repositorio en `/srv/bugalu` (Windows: `C:\bugalu`, ruta sin espacios), con un usuario sin privilegios `bugalu`. Supabase ya en marcha: [produccion-supabase](produccion-supabase.md).

## Backend

```bash
cd /srv/bugalu/backend
uv sync --no-dev            # sin pytest, ruff ni mypy; bugalu queda en modo editable y lee backend/.env
```

`backend/.env` de producción (permisos `600`):

| Variable | Valor |
|---|---|
| `URL_BASE_DATOS` | `postgresql://bugalu_api:<clave>@127.0.0.1:5433/postgres` |
| `URL_SUPABASE` | `https://supabase.<dominio>`. Debe ser la URL pública: de ella salen el emisor esperado de los JWT, el JWKS y las URL firmadas de las capturas que abre el navegador |
| `CLAVE_PUBLICABLE_SUPABASE` | `SUPABASE_PUBLISHABLE_KEY` del `.env` de Supabase |
| `ORIGENES_PERMITIDOS` | `https://<dominio>` |
| `SMTP_*` y `CORREO_REMITENTE` | Gmail con la contraseña `bugalu-backend` ([correo-gmail](correo-gmail.md#3-backend)) |
| `INTERVALO_ENVIO_CORREOS` | `30` |
| `URL_BASE_DATOS_ADMIN`, `CLAVE_SERVICIO_SUPABASE_PRUEBAS`, `EXIGIR_INTEGRACION` | No van: son de pruebas |

**Primer Administrador** (con su cuenta ya registrada), pasando la conexión de administración solo a esa orden, sin guardarla en `backend/.env`:

```bash
URL_BASE_DATOS_ADMIN="postgresql://postgres:<POSTGRES_PASSWORD>@127.0.0.1:5433/postgres" \
  .venv/bin/python -m bugalu.herramientas.crear_administrador <correo>
```

**Servicio en Linux (systemd),** `/etc/systemd/system/bugalu-api.service`:

```ini
[Unit]
Description=API de Bugalu
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=bugalu
WorkingDirectory=/srv/bugalu/backend
ExecStart=/srv/bugalu/backend/.venv/bin/uvicorn bugalu.main:crear_app --factory --host 127.0.0.1 --port 8080 --loop bugalu.compartido.bucle:crear_bucle
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`sudo systemctl daemon-reload && sudo systemctl enable --now bugalu-api`; registro: `journalctl -u bugalu-api -f`.

- Es la orden de `playwright.real.config.js` sin recarga. El puerto 8080 evita el 8000 del gateway de Supabase.
- Un solo proceso (sin `--workers`): la tarea de correos corre en cada proceso. La bandeja usa `skip locked` y no duplicaría envíos, pero uno basta.

**Servicio en Windows,** con [NSSM](https://nssm.cc) en una consola de administrador:

```powershell
nssm install bugalu-api C:\bugalu\backend\.venv\Scripts\uvicorn.exe "bugalu.main:crear_app --factory --host 127.0.0.1 --port 8080 --loop bugalu.compartido.bucle:crear_bucle"
nssm set bugalu-api AppDirectory C:\bugalu\backend
nssm set bugalu-api AppStdout C:\bugalu\registros\api.log
nssm set bugalu-api AppStderr C:\bugalu\registros\api.log
nssm start bugalu-api
```

En Windows el `--loop` es imprescindible: con el bucle por defecto, `psycopg` asíncrono no funciona ([montaje-local](montaje-local.md)).

## Frontend

Las `PUBLIC_*` se leen al construir: cambiar una exige reconstruir.

```bash
cd /srv/bugalu/frontend
npm ci
# frontend/.env: PUBLIC_URL_API=https://api.<dominio>  PUBLIC_URL_SUPABASE=https://supabase.<dominio>
#                PUBLIC_CLAVE_PUBLICABLE_SUPABASE=<SUPABASE_PUBLISHABLE_KEY>  PUBLIC_ACCESO_PROVEEDORES (vacío sin OAuth)
npm run build               # dist/, sin /catalogo; no definas PUBLIC_CATALOGO
```

- **En el servidor (recomendado):** Caddy sirve `dist/` (abajo). Sale por el mismo túnel y no hay otro servicio que mantener.
- **En un servicio gratuito:** Netlify (directorio base `frontend`, orden `npm run build`, publicación `dist`, `NODE_VERSION` 22.23 o superior) o Cloudflare Workers con archivos estáticos (Astro lo recomienda en lugar de Pages para proyectos nuevos; necesita un `wrangler.jsonc` con `assets.directory` en `./dist`). Las `PUBLIC_*` van en el panel del servicio. Su dominio entra en `ORIGENES_PERMITIDOS`, `SITE_URL` y `ADDITIONAL_REDIRECT_URLS`. La API y Supabase siguen en el servidor.

## Proxy inverso con límite de cuerpo

**Obligatorio.** `LimitePagos` solo rechaza `POST /api/v1/pagos` por `Content-Length`: una subida sin esa cabecera (chunked) llega entera y Starlette la vuelca a disco antes del 413 (el `shortcut:` de `limite.py`). Uvicorn no tiene límite de cuerpo. El proxy corta a **6 MB** (5 MB de captura más campos y envoltura) toda la API; ningún otro endpoint recibe más de unos KB.

[Caddy](https://caddyserver.com/docs/caddyfile/directives/request_body) (HTTPS automático), `/etc/caddy/Caddyfile`:

```caddyfile
<dominio> {
	root * /srv/bugalu/frontend/dist
	file_server
}

api.<dominio> {
	request_body {
		max_size 6MB
	}
	reverse_proxy 127.0.0.1:8080
}

supabase.<dominio> {
	@publico path /auth/v1/* /storage/v1/*
	handle @publico {
		reverse_proxy 127.0.0.1:8000
	}
	handle {
		respond 404
	}
}
```

- **Con los puertos 80 y 443 abiertos,** Caddy obtiene y renueva los certificados solo; el DNS debe apuntar al servidor.
- **Con Cloudflare Tunnel,** Cloudflare pone el HTTPS. Añade al principio el bloque de abajo, escribe cada sitio con `http://` delante (`http://api.<dominio>`) y apunta el túnel a `http://127.0.0.1:8081` ([produccion-exposicion](produccion-exposicion.md)):

  ```caddyfile
  {
  	auto_https off
  	http_port 8081
  	default_bind 127.0.0.1
  }
  ```
- `supabase.<dominio>` solo publica lo que usa el navegador: la sesión (`/auth/v1`) y las URL firmadas de las capturas (`/storage/v1`).
- **Nginx** en su lugar: `client_max_body_size 6m;` en el `server` de `api.<dominio>` (por defecto, 1 MB) y certificados con certbot.

**Comprobación,** sin token, contra Caddy desde el propio servidor (con túnel, `http://127.0.0.1:8081` y `-H "Host: api.<dominio>"`) y después desde fuera:

```bash
head -c 7000000 /dev/zero > grande.bin
curl -s -w "\n%{http_code}\n" -H "Transfer-Encoding: chunked" -F "captura=@grande.bin" https://api.<dominio>/api/v1/pagos
```

Debe responder `413` sin el JSON de la API: lo corta el proxy. Un `401`, o un `413` con `archivo_muy_grande`, significa que la petición llegó a la API: el límite del proxy no está activo.
