---
id: operacion-produccion-exposicion
titulo: Exponer la plataforma a Internet
estado: borrador
depende_de: [operacion-produccion, operacion-produccion-servicios, ADR-014]
---

# Exponer la plataforma a Internet

Los clientes reservan y pagan desde fuera del estudio: el servidor tiene que responder por HTTPS en tres nombres (`<dominio>`, `api.<dominio>` y `supabase.<dominio>`, ver [produccion](produccion.md#arquitectura)). **El dominio está por reservar** ([ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md)).

## Opciones

| Opción | Puertos abiertos en el router | IP pública fija | HTTPS | Costo | Límites |
|---|---|---|---|---|---|
| **Cloudflare Tunnel** con dominio | Ninguno | No hace falta | Cloudflare | Gratis; el dominio, en Cloudflare | Peticiones de hasta 100 MB (plan Free). Cloudflare termina el TLS y ve el tráfico |
| Puertos 80 y 443 abiertos, con dominio | 80 y 443 | Sí, o DNS dinámico | Caddy con Let's Encrypt | Gratis | No funciona tras CGNAT. El servidor recibe escaneos de Internet directamente |
| Tailscale Funnel, sin dominio | Ninguno | No hace falta | Tailscale | Gratis (función beta) | Solo nombres `<equipo>.<tailnet>.ts.net` y puertos 443, 8443 y 10000. Límite de ancho de banda sin cifra publicada |
| Túnel rápido de Cloudflare, sin dominio | Ninguno | No hace falta | Cloudflare | Gratis, sin cuenta | URL `*.trycloudflare.com` al azar que cambia en cada arranque, sin garantía de servicio, 200 peticiones simultáneas: solo demostraciones |

**Recomendación: Cloudflare Tunnel con el dominio en Cloudflare.** No abre puertos, funciona aunque el proveedor de Internet no dé IP pública fija y no hay certificados que renovar. El tope de 100 MB no afecta a los pagos (6 MB) ni al Libro de Reclamaciones (16 MB). Pero RF-09 (WAV de multipistas y másteres) tendrá que subir el audio por partes: decídelo al implementarlo.

## Sin dominio (pruebas y piloto)

- **Túnel rápido:** `cloudflared tunnel --url http://127.0.0.1:8081` da una URL; cada nombre necesita su propio túnel, y al reiniciar cambian todas. Cada cambio obliga a tocar `SUPABASE_PUBLIC_URL`, `API_EXTERNAL_URL`, `SITE_URL`, `URL_SUPABASE`, `ORIGENES_PERMITIDOS` y las `PUBLIC_*`, y a reconstruir el frontend. Sirve para enseñar la app, no para clientes.
- **Tailscale Funnel:** un nombre estable con HTTPS. Los tres servicios van en un mismo nombre, uno por puerto (443 el frontend, 8443 la API, 10000 Supabase), cada uno hacia un sitio de Caddy en HTTP local, que sigue poniendo el límite de cuerpo. Configuración: [guía de Funnel](https://tailscale.com/kb/1223/funnel).
- Sin dominio propio no hay verificación de marca en Google ni modo activo en Meta, y el correo de Auth lleva enlaces a un nombre ajeno: el acceso social espera al dominio ([credenciales-oauth](credenciales-oauth.md#requisitos-para-pasar-a-producción)).

## Con dominio y Cloudflare Tunnel

1. Reserva el dominio y pon sus servidores de nombres en Cloudflare (o regístralo en Cloudflare). El túnel solo publica nombres de un dominio activo en la cuenta.
2. Zero Trust → **Networks → Tunnels → Create a tunnel** → Cloudflared. El panel muestra la orden que instala el conector como servicio con su token: en Linux, `sudo cloudflared service install <token>`; en Windows, `cloudflared.exe service install <token>` en una consola de administrador. El token es un secreto.
3. En las rutas publicadas del túnel (Public hostnames), `<dominio>`, `api.<dominio>` y `supabase.<dominio>` van a `http://127.0.0.1:8081`, Caddy en modo túnel ([produccion-servicios](produccion-servicios.md#proxy-inverso-con-límite-de-cuerpo)). Cloudflare crea los registros DNS.
4. En el router no se abre nada. En el servidor, el cortafuegos deniega toda entrada salvo SSH desde la red del estudio.

### IP real del visitante con túnel

El conector `cloudflared` conecta con Caddy desde 127.0.0.1: sin más, Caddy y la API ven a todos los visitantes en esa IP y el límite de 5 hojas por hora por IP del Libro de Reclamaciones valdría para todo el estudio. Se arregla en dos sitios, y ambos confían solo en 127.0.0.1:

1. Bloque global del Caddy en modo túnel ([produccion-servicios](produccion-servicios.md#proxy-inverso-con-límite-de-cuerpo)): Caddy toma la IP de `CF-Connecting-IP` (la fija Cloudflare) solo si la petición llega de 127.0.0.1, y `api.<dominio>` la envía como `X-Forwarded-For`.

   ```caddyfile
   servers {
   	trusted_proxies static 127.0.0.1/32
   	client_ip_headers CF-Connecting-IP
   }
   ```
2. Servicio de la API con `--forwarded-allow-ips 127.0.0.1`: uvicorn solo lee `X-Forwarded-For` de Caddy; una cabecera enviada por otro cliente no cambia su IP (lo prueba `test_el_limite_usa_la_ip_reenviada_solo_si_el_proxy_es_de_confianza`).

### Comprobación del Libro de Reclamaciones

Cada alta crea una hoja que no se puede borrar: hazla **antes de abrir al público** y con datos de prueba. Contra Caddy desde el servidor (`http://127.0.0.1:8081`, que acepta `CF-Connecting-IP` por venir de 127.0.0.1):

```bash
for i in 1 2 3; do { printf '\211PNG\r\n\032\n'; head -c 4000000 /dev/zero; } > a$i.png; done   # 12 MB en total
alta() {  # $1 = IP del visitante
  curl -s -w '\n%{http_code}\n' -H 'Host: api.<dominio>' -H "CF-Connecting-IP: $1" \
    -F 'datos={"confirmado":true,"consumidor":{"nombre":"Prueba","tipo_documento":"dni","documento":"12345678","domicilio":"Av. Prueba 1","correo":"prueba@example.com"},"bien":{"tipo":"servicio"},"tipo":"queja","detalle":"Alta de prueba del despliegue.","pedido":"Ninguno: es una prueba.","medio_respuesta":"correo"}' \
    -F adjuntos=@a1.png -F adjuntos=@a2.png -F adjuntos=@a3.png http://127.0.0.1:8081/api/v1/reclamaciones
}
alta 203.0.113.10; alta 203.0.113.11
```

- Las dos altas (12 MB cada una, desde dos IP distintas) deben dar `201`. Un `413` significa que el bloque de 16 MB de `/api/v1/reclamaciones*` no está activo.
- En la base, `select count(distinct ip_hash) from public.intento_reclamacion where creado_en > now() - interval '5 minutes';` debe dar **2**. Con **1**, la API ve a todos desde 127.0.0.1: falta `--forwarded-allow-ips` o `trusted_proxies`.

## Con dominio y puertos abiertos

1. Comprueba que la IP WAN del router coincide con la que ve un servicio de "cuál es mi IP": si no, estás tras CGNAT y esta opción no sirve. Si la IP cambia, usa DNS dinámico.
2. Registros `A` de `<dominio>`, `api.<dominio>` y `supabase.<dominio>` a esa IP.
3. Reenvía en el router los puertos 80 y 443 al servidor, y ninguno más (nunca 5432, 5433, 6543 ni 8000).
4. Caddy sin el bloque del túnel: obtiene los certificados solo.

## Al tener el dominio

- Supabase: `SUPABASE_PUBLIC_URL`, `API_EXTERNAL_URL`, `SITE_URL` y `ADDITIONAL_REDIRECT_URLS` ([produccion-supabase](produccion-supabase.md#2-variables-del-env-de-supabase)), y `docker compose up -d`.
- Backend: `URL_SUPABASE` y `ORIGENES_PERMITIDOS`, y reinicio del servicio.
- Frontend: las `PUBLIC_*` y `npm run build`.
- Google y Meta: el callback `https://supabase.<dominio>/auth/v1/callback`, el dominio verificado en Google Search Console y los textos legales publicados ([credenciales-oauth](credenciales-oauth.md)).
- Las sesiones abiertas con el nombre anterior dejan de valer: el emisor de los JWT cambia.

Fuentes de las cuatro partes de producción: [Supabase, Docker](https://supabase.com/docs/guides/self-hosting/docker) · [Supabase, claves nuevas y ES256](https://supabase.com/docs/guides/self-hosting/self-hosted-auth-keys) · [Supabase, acceso a Postgres](https://supabase.com/docs/guides/self-hosting/accessing-postgres) · [Supabase, flujo del CLI](https://supabase.com/docs/guides/local-development/cli-workflows) · [Supabase, `db push`](https://supabase.com/docs/reference/cli/supabase-db-push) · [Supabase, copias y restauración](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore) · [Supabase, restaurar en autoalojado](https://supabase.com/docs/guides/self-hosting/restore-from-platform) · [Docker y cortafuegos](https://docs.docker.com/engine/network/packet-filtering-firewalls/) · [Caddy, `request_body`](https://caddyserver.com/docs/caddyfile/directives/request_body) · [Nginx, `client_max_body_size`](https://nginx.org/en/docs/http/ngx_http_core_module.html#client_max_body_size) · [Uvicorn, opciones](https://uvicorn.dev/settings/) · [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/) · [Cloudflare, túnel rápido](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/) · [Cloudflare, error 413](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/) · [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) · [Astro en Cloudflare](https://docs.astro.build/en/guides/deploy/cloudflare/) · [Astro en Netlify](https://docs.astro.build/en/guides/deploy/netlify/) (consultadas el 2026-11-16).
