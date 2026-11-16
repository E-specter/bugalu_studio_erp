---
id: operacion-produccion-mantenimiento
titulo: Copias, actualizaciones y monitoreo en producción
estado: borrador
depende_de: [operacion-produccion, operacion-produccion-supabase, operacion-despliegue]
---

# Copias, actualizaciones y monitoreo

Montaje: [produccion](produccion.md). Rutas de ejemplo de Linux: Supabase en `/srv/supabase`, repositorio en `/srv/bugalu`, copias en `/srv/copias`.

## Copias de seguridad

| Qué | Dónde está | Cómo |
|---|---|---|
| Base de datos, con `auth.users` y los metadatos de `storage.objects` | Contenedor `db` | Volcado lógico diario |
| Archivos del bucket `comprobantes` (y `entregables` con RF-09) | `/srv/supabase/volumes/storage` | Copia de la carpeta, después del volcado |
| Configuración y secretos: `.env` y `docker-compose.yml` de Supabase, `backend/.env`, `frontend/.env`, `Caddyfile` | Servidor | Gestor de contraseñas del estudio y copia cifrada |

**Volcado diario,** con un script programado (cron o un temporizador de systemd; en Windows, el Programador de tareas). La URL de administración se lee de un archivo con permisos `600`:

```bash
set -euo pipefail
D=/srv/copias/$(date +%F); mkdir -p "$D"
URL=$(cat /srv/copias/.url-admin)    # postgresql://postgres:<POSTGRES_PASSWORD>@127.0.0.1:5433/postgres
cd /srv/bugalu
npx supabase db dump --remote "$URL" -f "$D/roles.sql" --role-only
npx supabase db dump --remote "$URL" -f "$D/schema.sql"
npx supabase db dump --remote "$URL" -f "$D/data.sql" --use-copy --data-only
docker compose -f /srv/supabase/docker-compose.yml exec -T db pg_dump -U postgres -n supabase_migrations postgres > "$D/historial.sql"
tar -czf "$D/storage.tar.gz" -C /srv/supabase/volumes storage
```

- Primero la base y después los archivos: así cada fila de `storage.objects` del volcado tiene su archivo.
- `historial.sql` guarda el registro de migraciones aplicadas, que el volcado no incluye: sin él, `db push` intentaría aplicarlas otra vez.
- **Fuera del servidor:** una copia cifrada diaria en un disco externo y otra en la nube (p. ej. con `restic`). Contiene datos personales y capturas de pago.
- Retención: 7 diarias y 4 semanales.
- **Copia en frío (opcional, semanal):** `docker compose stop`, copiar `volumes/db/data` y `volumes/storage`, y `docker compose start`. Son unos minutos sin servicio (de madrugada), pero restaura exacto en la misma versión de Supabase.

## Restauración

Se ensaya **cada mes** en otra máquina, nunca sobre el servidor en uso. Se restaura siempre en un Supabase nuevo y luego se cambia a él.

1. Supabase autoalojado de la **misma versión**, con el mismo `.env` y los cambios de [produccion-supabase](produccion-supabase.md). Con claves distintas, los usuarios tienen que volver a entrar.
2. Sin aplicar migraciones (el volcado trae el esquema), con `psql` en el equipo:

   ```bash
   psql --single-transaction --variable ON_ERROR_STOP=1 \
     --file roles.sql --file schema.sql \
     --command 'SET session_replication_role = replica' \
     --file data.sql --dbname "$URL"
   psql --file historial.sql --dbname "$URL"
   ```

   La primera vez, sin `--single-transaction`, para ver todos los errores de una pasada. En `historial.sql`, los errores de "ya existe" no importan.
3. Archivos: con el stack parado, `tar -xzf storage.tar.gz -C /srv/supabase/volumes`, y arranca.
4. Contraseña de `bugalu_api` con `\password bugalu_api`: las de los roles con acceso no van en el volcado.
5. Comprueba: `select count(*) from auth.users;`, las últimas reservas, que una captura de pago se abre desde la app y que `cron.job` tiene sus dos tareas. Si faltan, prográmalas con las mismas sentencias `cron.schedule` de las migraciones.

## Actualizaciones

**De la plataforma,** tras la aprobación de `leader` ([despliegue](despliegue.md)):

1. Copia de seguridad.
2. `git pull` del commit o la etiqueta aprobados.
3. Migraciones: `npx supabase db push --remote "$URL" --dry-run` y, si es lo esperado, sin `--dry-run`. Van antes que el código, que espera el esquema nuevo.
4. Backend: `uv sync --no-dev` y `sudo systemctl restart bugalu-api`.
5. Frontend: `npm ci && npm run build`. Caddy sirve el `dist/` nuevo sin reiniciar.
6. Comprobación rápida con la tabla de monitoreo.

Una migración aplicada no se edita: la corrección es otra migración.

**De Supabase:** `update.sh` trae la siguiente instantánea `self-hosted/v*` y fusiona tus cambios de `docker-compose.yml` y `.env`. Antes, copia de seguridad y lectura del registro de cambios de Supabase (hay cambios incompatibles, como el paso de Postgres 15 a 17 o el del gateway). Después, revisa que siguen los ajustes de [produccion-supabase](produccion-supabase.md): `127.0.0.1:`, el puerto de `db`, las `GOTRUE_*` y `PGRST_DB_SCHEMAS`.

**Del sistema y Docker:** parches de seguridad cada mes, con reinicio fuera del horario de sesiones.

## Monitoreo básico

| Qué | Cómo |
|---|---|
| API viva | `curl -s -o /dev/null -w "%{http_code}" https://api.<dominio>/api/v1/perfil` responde `401` |
| Auth viva | `curl -s https://supabase.<dominio>/auth/v1/.well-known/jwks.json` devuelve una clave `EC` |
| Aviso externo | Un servicio gratuito de monitoreo de disponibilidad que llame a esas dos URL cada 5 minutos y avise al correo del estudio |
| Registros | `journalctl -u bugalu-api`, `journalctl -u caddy` y `docker compose logs auth storage` |
| `pg_cron` | `select status, count(*) from cron.job_run_details where start_time > now() - interval '1 day' group by status;` sin `failed` |
| Correos atascados | `select count(*) from public.notificacion where enviada_en is null and intentos >= 5;` en 0 ([correo-gmail](correo-gmail.md#si-no-llega)) |
| Disco | `df -h` y `docker system df`; capturas y copias crecen: actúa al 80 % |
| Copias | Existe la carpeta del día y el simulacro del mes salió bien |
