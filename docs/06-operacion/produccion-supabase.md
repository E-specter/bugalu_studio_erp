---
id: operacion-produccion-supabase
titulo: Supabase autoalojado en el servidor del estudio
estado: borrador
depende_de: [operacion-produccion, ADR-007, ADR-011, ADR-014]
---

# Supabase autoalojado

Docker Compose oficial de Supabase ([guía](https://supabase.com/docs/guides/self-hosting/docker)). Arquitectura y secretos: [produccion](produccion.md). Las rutas de ejemplo son de Linux (`/srv/supabase`).

## 1. Instalar

Con Docker Engine y Docker Compose instalados. Fija una versión publicada (`self-hosted/v<versión>`, la guía oficial indica la actual): no mezcles imágenes sueltas.

```bash
git clone --depth 1 --branch self-hosted/v<versión> https://github.com/supabase/supabase /tmp/supabase
sudo mkdir -p /srv/supabase && sudo cp -r /tmp/supabase/docker/. /srv/supabase/
cd /srv/supabase
cp .env.example .env
sh utils/generate-keys.sh                     # secretos nuevos; revisa que quedan en .env
sh utils/add-new-auth-keys.sh --update-env    # clave publicable y secreta, y firma ES256 (JWKS)
docker compose pull
```

- **`add-new-auth-keys.sh` es obligatorio:** con `JWT_KEYS`, Auth firma con ES256 y publica la clave en `/auth/v1/.well-known/jwks.json`. Sin él, Auth firma con HS256 y el backend rechaza todas las peticiones con sesión.
- `POSTGRES_PASSWORD` solo con letras y números (va dentro de URL). Nunca arranques con los valores de `.env.example`.
- La alternativa es el instalador rápido (solo Linux), que hace lo mismo y pregunta las URL: revisa el script antes de ejecutarlo.

## 2. Variables del `.env` de Supabase

| Variable | Valor | Por qué |
|---|---|---|
| `SUPABASE_PUBLIC_URL` | `https://supabase.<dominio>` | URL pública del gateway |
| `API_EXTERNAL_URL` | `https://supabase.<dominio>/auth/v1` | Emisor (`iss`) de los JWT: el backend lo espera igual a `URL_SUPABASE` + `/auth/v1` |
| `SITE_URL` | `https://<dominio>` | Base de los enlaces de los correos de Auth |
| `ADDITIONAL_REDIRECT_URLS` | `https://<dominio>,https://<dominio>/**` | Vuelta del acceso social a `/app/` |
| `ENABLE_EMAIL_AUTOCONFIRM` | `true` | Equivale a `enable_confirmations = false`: la verificación la lleva el backend (CA-06) |
| `DISABLE_SIGNUP` | `false` | Registro de artistas y clientes |
| `JWT_EXPIRY` | `3600` | Igual que `jwt_expiry` |
| `PGRST_DB_SCHEMAS` | `graphql_public` | **ADR-007:** la API REST no expone `public`. El valor por defecto (`public,graphql_public`) lo expondría |
| `SMTP_HOST`, `SMTP_PORT` | `smtp.gmail.com`, `587` | [correo-gmail](correo-gmail.md); el valor por defecto `supabase-mail` no existe en producción |
| `SMTP_USER`, `SMTP_ADMIN_EMAIL` | La cuenta del estudio | Usuario y remitente |
| `SMTP_PASS` | Contraseña de aplicación `bugalu-auth` | Distinta de la del backend |
| `SMTP_SENDER_NAME` | `Bugalú Studio` | |
| `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD` | Propios | Acceso a Studio |

## 3. Servicio `auth` en `docker-compose.yml`

`supabase/config.toml` fija reglas que el `.env` no trae. Añádelas al bloque `environment` del servicio `auth`:

```yaml
      GOTRUE_PASSWORD_MIN_LENGTH: "8"
      GOTRUE_PASSWORD_REQUIRED_CHARACTERS: "<minúsculas>:<mayúsculas>:<dígitos>:<símbolos>"
      GOTRUE_RATE_LIMIT_EMAIL_SENT: "30"
```

- La contraseña exige un carácter de cada grupo separado por `:` (un `:` dentro de un grupo se escapa con `\`). Usa los mismos grupos que `lower_upper_letters_digits_symbols` del CLI y comprueba que `Clave-Segura-123` se acepta y `clavesegura` no.
- Acceso social: descomenta las líneas `GOTRUE_EXTERNAL_GOOGLE_*` del servicio y las `GOOGLE_*` del `.env`, con `GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI: ${API_EXTERNAL_URL}/callback`. Meta, igual con `GOTRUE_EXTERNAL_FACEBOOK_*`. Credenciales: [credenciales-oauth](credenciales-oauth.md).
- Asuntos y plantillas en español: `GOTRUE_MAILER_SUBJECTS_RECOVERY` y `GOTRUE_MAILER_SUBJECTS_MAGIC_LINK`; el HTML, con `GOTRUE_MAILER_TEMPLATES_*` (una URL que el contenedor pueda leer).

## 4. Puertos solo en el propio servidor

- Docker publica los puertos por delante del cortafuegos del sistema (`ufw` no los filtra). En `docker-compose.yml`, antepón `127.0.0.1:` a los puertos que publican `api-gw` (8000) y `supavisor` (5432 y 6543).
- El backend se conecta directo a PostgreSQL, sin Supavisor: añade al servicio `db` (que no publica ningún puerto)

  ```yaml
      ports:
        - "127.0.0.1:5433:5432"
  ```

  El backend ya tiene su propio pool, y por Supavisor el usuario lleva el sufijo del inquilino (`postgres.<POOLER_TENANT_ID>`).
- Studio: `http://127.0.0.1:8000` en el servidor, o desde otro equipo con `ssh -L 8000:127.0.0.1:8000 <usuario>@<servidor>`. El proxy no lo publica.

Arranca y comprueba: `docker compose up -d`, `docker compose ps` (todos `healthy`) y `docker compose exec db psql -U postgres -c 'select version();'` debe decir 17, como el desarrollo (`major_version = 17`). Si dice 15, usa la variante de Postgres 17 de la guía oficial antes de cargar datos.

## 5. Esquema, rol de la API y `pg_cron`

Desde una copia del repositorio en el servidor (raíz), con la conexión de administración:

```bash
export URL_ADMIN="postgresql://postgres:<POSTGRES_PASSWORD>@127.0.0.1:5433/postgres"
npx supabase db push --remote "$URL_ADMIN" --dry-run   # lista lo que aplicaría
npx supabase db push --remote "$URL_ADMIN"
```

- **Nunca `db reset` ni `--include-seed`:** `seed.sql` pone la contraseña de desarrollo de `bugalu_api` y datos de ejemplo. El CLI 3 usa `--remote`; los anteriores, `--db-url`.
- **Contraseña de `bugalu_api`** (la migración crea el rol sin ella): `docker compose exec db psql -U postgres` y, dentro, `\password bugalu_api`. Larga, aleatoria, solo letras y números. Va a `URL_BASE_DATOS` ([produccion-servicios](produccion-servicios.md)).
- **`pg_cron`:** las migraciones crean la extensión y programan `caducar_reservas` y `avanzar_reservas` cada minuto. Compruébalo:

  ```sql
  select jobname, schedule, active from cron.job;
  select status, return_message, start_time from cron.job_run_details order by start_time desc limit 10;
  ```

  `cron.job_run_details` suma unas 2 880 filas al día. Su limpieza periódica (p. ej. lo de más de 7 días) debe llegar como migración; mientras tanto, bórralas a mano.
- **Datos de arranque:** sin el seed, ningún método de pago está activo. El Administrador carga los datos para pagar y el contacto del estudio desde la app.
