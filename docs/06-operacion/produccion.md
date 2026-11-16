---
id: operacion-produccion
titulo: Producción en el servidor del estudio
estado: borrador
depende_de: [ADR-014, ADR-007, ADR-011, ADR-012, operacion-entornos]
---

# Producción en el servidor del estudio

[ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md): Supabase con Docker y el backend en un servidor del estudio; el frontend estático en ese servidor o en un servicio gratuito. **El dominio está por reservar:** donde dice `<dominio>`, pon el que se reserve.

Partes, en el orden de montaje:

1. [produccion-supabase](produccion-supabase.md): Supabase autoalojado, Auth, migraciones, rol de la API y `pg_cron`.
2. [produccion-servicios](produccion-servicios.md): backend como servicio, frontend estático y proxy con HTTPS y **límite de cuerpo**.
3. [produccion-exposicion](produccion-exposicion.md): cómo llegar desde Internet, con y sin dominio.
4. [produccion-mantenimiento](produccion-mantenimiento.md): copias y restauración, actualizaciones y monitoreo.

## Arquitectura

```text
Internet ─► Cloudflare Tunnel o puertos 80/443 ─► Caddy (HTTPS, límite de cuerpo)
  <dominio>           ─► frontend/dist (archivos estáticos)
  api.<dominio>       ─► backend FastAPI en 127.0.0.1:8080 (servicio del sistema)
  supabase.<dominio>  ─► gateway de Supabase en 127.0.0.1:8000 (solo /auth/v1 y /storage/v1)
backend ─► PostgreSQL de Supabase en 127.0.0.1:5433 (rol bugalu_api, ADR-007)
backend y Auth ─► smtp.gmail.com:587 (ADR-011)
```

Nada más escucha fuera del servidor: Studio, PostgreSQL y Supavisor quedan en `127.0.0.1`.

**Sistema operativo:** Linux (Ubuntu Server LTS u otra distribución con Docker Engine) es lo recomendado: el instalador rápido de Supabase es solo para Linux y Docker Engine corre como servicio del sistema. Windows sirve con Docker Desktop (WSL 2), pero Docker Desktop se inicia con la sesión de un usuario y los scripts de la carpeta `docker/` de Supabase deben tener finales de línea LF.

**Equipo:** Supabase pide como mínimo 4 GB de RAM, 2 núcleos y 40 GB de SSD, y recomienda 8 GB, 4 núcleos y 80 GB o más. Suma el espacio de los comprobantes, de las copias y, con RF-09, del audio.

## CLI o Supabase autoalojado

| | CLI (`npx supabase start`, desarrollo) | Autoalojado (Docker Compose oficial) |
|---|---|---|
| Propósito | Solo desarrollo. Supabase: no está endurecido para producción y nunca debe recibir tráfico externo | Servidor propio en producción |
| Credenciales | Por defecto (`postgres:postgres`, claves de ejemplo) | Generadas por sus scripts |
| TLS y límite de peticiones | No tiene | Detrás de un proxy con HTTPS |
| Puertos | Publica los 456xx en todas las interfaces (`0.0.0.0`) | Gateway 8000 y Supavisor 5432/6543; se restringen a `127.0.0.1` |
| Studio | Sin contraseña | Con usuario y contraseña |
| Configuración | `supabase/config.toml` | `.env` y `docker-compose.yml` (variables `GOTRUE_*`, `PGRST_*`) |
| Correo | Mailpit integrado | SMTP real (Gmail) |
| Migraciones | `db reset` (con `seed.sql`) | `db push` (sin seed) |
| JWT ES256 con JWKS y clave publicable | Sí | Sí, con `utils/add-new-auth-keys.sh` |
| Actualizaciones | Con la versión del CLI | `update.sh`, instantáneas mensuales |

**Recomendación: Supabase autoalojado.** El CLI se queda en los equipos de desarrollo. Las dos variantes firman los JWT con ES256 y publican el JWKS, que es lo único que acepta el backend (`compartido/autenticacion.py`).

## Secretos y variables

Ningún secreto se versiona ni se escribe en `docs/`. Los `.env.example` del repositorio quedan sin valores.

| Secreto | Dónde vive |
|---|---|
| `POSTGRES_PASSWORD`, `DASHBOARD_PASSWORD`, `JWT_SECRET`, `JWT_KEYS`, `SUPABASE_SECRET_KEY` y demás claves generadas | `.env` de la carpeta de Supabase autoalojado |
| Contraseña del rol `bugalu_api` | La base y `URL_BASE_DATOS` de `backend/.env` |
| Contraseñas de aplicación de Gmail (`bugalu-backend`, `bugalu-auth`) | `backend/.env` y `.env` de Supabase ([correo-gmail](correo-gmail.md)) |
| ID y secreto de los clientes OAuth de producción | `.env` de Supabase ([credenciales-oauth](credenciales-oauth.md)) |
| Token del túnel de Cloudflare | Servicio `cloudflared` |

- Cada `.env` con permisos `600` y dueño el usuario del servicio. Guarda una copia de todos en el gestor de contraseñas del estudio: sin ellos no se restaura una copia ([produccion-mantenimiento](produccion-mantenimiento.md)).
- La clave secreta de Supabase (`SUPABASE_SECRET_KEY`) no la usa el backend: no la copies a `backend/.env`. Al frontend solo va la publicable.
- Si un secreto se filtra, rótalo; borrarlo de un archivo no basta.

## Lista de verificación antes de abrir al público

- [ ] Textos legales publicados en el dominio: política de privacidad, términos e instrucciones de eliminación de datos ([ADR-012](../00-proyecto/decisiones/ADR-012-textos-legales-y-consentimientos.md)).
- [ ] Dominio reservado y HTTPS válido en `<dominio>`, `api.<dominio>` y `supabase.<dominio>`.
- [ ] **Límite de cuerpo activo:** la comprobación de [produccion-servicios](produccion-servicios.md#proxy-inverso-con-límite-de-cuerpo) devuelve 413 desde fuera.
- [ ] OAuth en producción: clientes `bugalu-produccion` con el callback `https://supabase.<dominio>/auth/v1/callback`, app de Google publicada y app de Meta en modo activo ([credenciales-oauth](credenciales-oauth.md#requisitos-para-pasar-a-producción)).
- [ ] Correo real: backend y Auth con Gmail y la prueba de extremo a extremo de [correo-gmail](correo-gmail.md#5-prueba-de-extremo-a-extremo) superada.
- [ ] Mailpit desactivado: ni el backend ni Auth apuntan a Mailpit o a `supabase-mail`, y no hay ningún servidor de correo de pruebas publicado.
- [ ] Secretos generados (ninguno de `.env.example`), `.env` con permisos `600` y Studio accesible solo desde el propio servidor.
- [ ] PostgREST sin `public` (`PGRST_DB_SCHEMAS=graphql_public`): `GET /rest/v1/usuario` no devuelve datos.
- [ ] `pg_cron`: `caducar_reservas` y `avanzar_reservas` corren cada minuto sin fallos.
- [ ] Copias: la primera hecha y **la restauración probada** en otra máquina.
- [ ] Monitoreo externo activo, con avisos al correo del estudio.
- [ ] `seed.sql` sin aplicar; primer Administrador creado; datos para pagar y contacto del estudio cargados desde la app.
- [ ] `ORIGENES_PERMITIDOS` solo con `https://<dominio>`; `PUBLIC_CATALOGO` sin definir en el build.
