---
id: ADR-014
titulo: Alojamiento inicial en un servidor local del estudio
estado: aprobado
depende_de: [D-08, ADR-007]
---

# ADR-014: Alojamiento inicial en un servidor local del estudio

## Contexto

Faltaba decidir dónde corre la plataforma (D-08).

## Decisión

Usuario, 2026-11-16: inicialmente todo en local: Supabase con Docker y el backend en un servidor del estudio; el frontend estático en ese servidor o en un servicio gratuito. No hay dominio todavía; se reservará uno.

## Consecuencias

- La guía de producción documenta el montaje en el servidor del estudio: Docker, Supabase, backend como servicio, HTTPS, copias de seguridad, `pg_cron`, correo ([ADR-011](ADR-011-correo-gmail-del-estudio.md)) y el **límite de tamaño de las peticiones** en el proxy.
- Para que los clientes lleguen desde Internet hace falta exponer el servidor (dominio y túnel o puerto público con HTTPS); la guía compara las opciones.
- El acceso con Google y Meta y el correo con buena entrega necesitan el dominio y los textos legales ([ADR-012](ADR-012-textos-legales-y-consentimientos.md)).
