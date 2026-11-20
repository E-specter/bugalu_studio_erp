---
id: arq-frontend-islas
titulo: Frontend — Arquitectura de Islas (Astro)
estado: borrador
depende_de: [arq-stack, convenciones]
---

# Frontend — Arquitectura de Islas (Astro)

- HTML estático por defecto; JavaScript solo en las islas que requieren interactividad.
- Islas implementadas como componentes `.astro` con `<script>` que registra Web Components (`customElements.define`). Las directivas `client:*` no aplican: son para componentes de frameworks UI.
- HTML semántico (`<main>`, `<nav>`, `<section>`, `<form>`, `<button>`), accesibilidad (ARIA solo cuando el elemento nativo no basta) y manipulación del DOM mínima.
- CSS con tokens de diseño (variables CSS) centralizados (ver [tokens](../07-diseno/tokens.md)).

## Estructura

```
frontend/
├── astro.config.mjs · playwright.config.js · package.json
├── scripts/              # comprobar-tokens.mjs, comprobar-literales.mjs (npm run check)
├── pruebas/              # Playwright + axe; capturas/ y resultados/ ignorados por git
└── src/
    ├── pages/            # rutas (nombre reservado por Astro); [catalogo].astro solo en desarrollo
    ├── layouts/          # LayoutBase, LayoutPublico, LayoutApp
    ├── componentes/      # .astro estáticos, sin JS; internos/ (Icono, MensajeError) fuera del catálogo
    ├── islas/            # .astro que registran <bugalu-*>
    ├── servicios/        # api.js (cliente HTTP), sesion.js (Supabase Auth), aforo.js (aforo y certificado ITSE de sala, RF-03), prosa.js (limpieza en el navegador de `contenido_html`, RF-17), asesorias.js (API de RF-15)
    ├── estilos/          # tokens.css, base.css
    └── assets/           # logotipo en SVG
```

## Islas identificadas

| Isla | Requerimiento |
|---|---|
| Calendario de sala: reserva y agenda (`<bugalu-calendario>`) | [RF-02](../03-requerimientos/RF-02.md), [RF-03](../03-requerimientos/RF-03.md), [RF-04](../03-requerimientos/RF-04.md) |
| Agenda de asesoría: calendario en modo `asesoria` (`<bugalu-calendario modo="asesoria">`, [calendario](../07-diseno/componentes/calendario.md#modos)) | [RF-15](../03-requerimientos/RF-15.md) |
| Directorio de profesionales y perfil público (`<bugalu-directorio vista="lista\|perfil">`, `islas/Directorio.astro`) | [RF-15](../03-requerimientos/RF-15.md) |
| Ficha y horarios del profesional (`<bugalu-profesional vista="ficha\|horarios">`, `islas/Profesional.astro`) | [RF-15](../03-requerimientos/RF-15.md) |
| Profesionales, especialidades y precios del Administrador (`<bugalu-profesionales vista="lista\|especialidades">`, `islas/Profesionales.astro`) | [RF-15](../03-requerimientos/RF-15.md) |
| Registro de pago con captura (`<bugalu-pago>`, `islas/Pago.astro`, [spec](../07-diseno/pantallas/RF-05-registrar-pago.md); suma el resumen legal de pago) | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md), [RF-17](../03-requerimientos/RF-17.md) |
| Pagos por validar, ficha del pago, datos para pagar y cola de devoluciones del Administrador (`<bugalu-pagos vista="lista\|revisar\|datos\|devoluciones\|devolucion">`, `islas/Pagos.astro`, [spec](../07-diseno/pantallas/RF-05-pagos.md), [devoluciones](../07-diseno/pantallas/RF-18-devoluciones.md)) | [RF-05](../03-requerimientos/RF-05.md), [RF-18](../03-requerimientos/RF-18.md) |
| Mis créditos y pedir devolución; créditos de un cliente en su ficha (`<bugalu-creditos>`, `islas/Creditos.astro`, vistas `lista` y `ficha`, [spec](../07-diseno/pantallas/RF-18-creditos.md)) | [RF-18](../03-requerimientos/RF-18.md) |
| Contraseña: mostrar u ocultar y medidor de robustez (`<bugalu-contrasena>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Acceso: iniciar sesión, registrarse, solicitar acceso interno, recuperar y restablecer (`<bugalu-acceso>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Estado de la solicitud de acceso interno (`<bugalu-solicitud>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Reserva por pasos (`<bugalu-reserva>`; paso `cuenta` y casilla de condiciones, [spec](../07-diseno/pantallas/RF-17-registro-y-aceptaciones.md)) | [RF-02](../03-requerimientos/RF-02.md), [RF-04](../03-requerimientos/RF-04.md), [RF-17](../03-requerimientos/RF-17.md) |
| Mis reservas, agenda y reprogramar con selector de horario y vista previa (`<bugalu-reservas>`, vista `reprogramar` en `islas/Reservas.astro`, [spec](../07-diseno/pantallas/RF-18-reprogramar.md)) | [RF-04](../03-requerimientos/RF-04.md), [RF-18](../03-requerimientos/RF-18.md) |
| Publicación de franjas, cierres y parámetros (`<bugalu-franjas>`; los parámetros sensibles pasan por `<bugalu-cambio-sensible>`) | [RF-03](../03-requerimientos/RF-03.md), [RF-20](../03-requerimientos/RF-20.md) |
| Tarifas, recargos, feriados e impuestos (`<bugalu-tarifas vista="…\|impuestos">`; los cambios sensibles pasan por `<bugalu-cambio-sensible>`) | [RF-02](../03-requerimientos/RF-02.md), [RF-20](../03-requerimientos/RF-20.md) |
| Vista previa y confirmación escrita de un cambio sensible (`<bugalu-cambio-sensible>`, `islas/CambioSensible.astro`, la montan `<bugalu-tarifas>` y `<bugalu-franjas>`, [spec](../07-diseno/pantallas/RF-20-cambios-sensibles.md)) | [RF-20](../03-requerimientos/RF-20.md) |
| Registro de cambios del Administrador (`<bugalu-registro-cambios>`, `islas/RegistroCambios.astro`, [spec](../07-diseno/pantallas/RF-20-registro-cambios.md)) | [RF-20](../03-requerimientos/RF-20.md) |
| Bandeja de solicitudes y usuarios del Administrador (`<bugalu-solicitudes>`; suma documentos repetidos y textos aceptados) | [RF-01](../03-requerimientos/RF-01.md), [RF-17](../03-requerimientos/RF-17.md) |
| Perfil propio, editable, con modalidad, documento, integrantes, domicilio y redes (`<bugalu-perfil>`) y privacidad con consentimientos e historial (`<bugalu-privacidad>`, `islas/Privacidad.astro`, ruta `/app/perfil/privacidad/`; separada de Perfil para no duplicar estados), [spec de RF-17](../07-diseno/pantallas/RF-17-perfil.md) | [RF-01](../03-requerimientos/RF-01.md), [RF-17](../03-requerimientos/RF-17.md) |
| Aceptación de textos pendientes tras registrarse o ingresar (`<bugalu-aceptacion>`, `islas/Aceptacion.astro`, `/acceso/textos?volver=`; `<bugalu-acceso>` pasa por ahí y `LayoutApp` avisa; piezas en `servicios/aceptaciones.js`, `resumen-legal.js` y `perfil-datos.js`) | [RF-17](../03-requerimientos/RF-17.md) |
| Texto legal público por versión (`<bugalu-texto-legal tipo="…">`, `islas/TextoLegal.astro`, páginas `/legal/` y `/legal/{slug}/?version=`; pinta `contenido_html` saneado por el backend y lo vuelve a limpiar en el navegador; sin JS, el contacto del estudio) y textos del Administrador (`<bugalu-textos-legales vista="lista\|publicar\|ver">`, `islas/TextosLegales.astro`, sobre `IslaGestion`; rutas `/app/textos`, `/app/textos/ver?tipo=&version=` (`pages/app/textos/ver.astro`) y `/app/textos/publicar?tipo=`; consumo en `servicios/textos-legales.js` y `servicios/prosa.js`). La [spec](../07-diseno/pantallas/RF-17-textos-legales.md) también amplía el filtro `?documento=repetido` de `<bugalu-solicitudes>` y su ficha de persona (U1 con modalidad, documento, domicilio, redes e integrantes; U3 textos aceptados con `aceptacionesDe(id)` y la pieza compartida `servicios/historial-aceptaciones.js`, que usa también `<bugalu-privacidad>`) | [RF-17](../03-requerimientos/RF-17.md) |
| Aviso descartable (`<bugalu-aviso>`) | Transversal ([aviso](../07-diseno/componentes/aviso.md)) |
| Carga de entregables y capturas (`<bugalu-carga-archivos>`, `islas/CargaArchivos.astro`; primero la variante `captura`, dentro de `<bugalu-pago>`) | [RF-05](../03-requerimientos/RF-05.md), [RF-09](../03-requerimientos/RF-09.md) |
| Reproductor con forma de onda y comentarios por timestamp (`<bugalu-reproductor>`) | [RF-10](../03-requerimientos/RF-10.md) |
| Libro de Reclamaciones: formulario público con confirmación, constancia imprimible y transcripción del respaldo físico (`<bugalu-reclamacion>`, `islas/Reclamacion.astro`, [spec](../07-diseno/pantallas/RF-16-formulario.md)) | [RF-16](../03-requerimientos/RF-16.md) |
| Mis reclamos del cliente y bandeja de reclamaciones del Administrador (`<bugalu-reclamos>`, `islas/Reclamos.astro`) | [RF-16](../03-requerimientos/RF-16.md) |
| Agendar asesoría por pasos: profesional, duración, horario, cuenta, confirmar y listo (`<bugalu-agendar>`, `islas/Agendar.astro`, páginas `/asesorias/agendar/`, `horario/`, `cuenta/`, `confirmar/` y `listo/`) | [RF-15](../03-requerimientos/RF-15.md) |
| Mis asesorías, detalle, pago, reprogramar y agenda del profesional o del Administrador (`<bugalu-agenda>`, `islas/Agenda.astro`, páginas `/app/asesorias/{mias,detalle,pagar,reprogramar,agenda}`) | [RF-15](../03-requerimientos/RF-15.md) |

El contador de PAGOS de la navegación no es isla: lo pinta el script de `LayoutApp` que ya carga el perfil ([navegación lateral](../07-diseno/componentes/navegacion-lateral.md#variantes)).
