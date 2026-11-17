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
    ├── servicios/        # api.js (cliente HTTP), sesion.js (Supabase Auth)
    ├── estilos/          # tokens.css, base.css
    └── assets/           # logotipo en SVG
```

## Islas identificadas

| Isla | Requerimiento |
|---|---|
| Calendario de sala: reserva y agenda (`<bugalu-calendario>`) | [RF-02](../03-requerimientos/RF-02.md), [RF-03](../03-requerimientos/RF-03.md), [RF-04](../03-requerimientos/RF-04.md) |
| Agenda de asesoría | [RF-15](../03-requerimientos/RF-15.md) |
| Registro de pago con captura (`<bugalu-pago>`, `islas/Pago.astro`, [spec](../07-diseno/pantallas/RF-05-registrar-pago.md); suma el resumen legal de pago) | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md), [RF-17](../03-requerimientos/RF-17.md) |
| Pagos por validar, ficha del pago y datos para pagar del Administrador (`<bugalu-pagos vista="lista\|revisar\|datos">`, `islas/Pagos.astro`, [spec](../07-diseno/pantallas/RF-05-pagos.md)) | [RF-05](../03-requerimientos/RF-05.md) |
| Contraseña: mostrar u ocultar y medidor de robustez (`<bugalu-contrasena>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Acceso: iniciar sesión, registrarse, solicitar acceso interno, recuperar y restablecer (`<bugalu-acceso>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Estado de la solicitud de acceso interno (`<bugalu-solicitud>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Reserva por pasos (`<bugalu-reserva>`; paso `cuenta` y casilla de condiciones, [spec](../07-diseno/pantallas/RF-17-registro-y-aceptaciones.md)) | [RF-02](../03-requerimientos/RF-02.md), [RF-04](../03-requerimientos/RF-04.md), [RF-17](../03-requerimientos/RF-17.md) |
| Mis reservas y agenda (`<bugalu-reservas>`) | [RF-04](../03-requerimientos/RF-04.md) |
| Publicación de franjas, cierres y parámetros (`<bugalu-franjas>`; los parámetros sensibles pasan por `<bugalu-cambio-sensible>`) | [RF-03](../03-requerimientos/RF-03.md), [RF-20](../03-requerimientos/RF-20.md) |
| Tarifas, recargos, feriados e impuestos (`<bugalu-tarifas vista="…\|impuestos">`; los cambios sensibles pasan por `<bugalu-cambio-sensible>`) | [RF-02](../03-requerimientos/RF-02.md), [RF-20](../03-requerimientos/RF-20.md) |
| Vista previa y confirmación escrita de un cambio sensible (`<bugalu-cambio-sensible>`, `islas/CambioSensible.astro`, la montan `<bugalu-tarifas>` y `<bugalu-franjas>`, [spec](../07-diseno/pantallas/RF-20-cambios-sensibles.md)) | [RF-20](../03-requerimientos/RF-20.md) |
| Registro de cambios del Administrador (`<bugalu-registro-cambios>`, `islas/RegistroCambios.astro`, [spec](../07-diseno/pantallas/RF-20-registro-cambios.md)) | [RF-20](../03-requerimientos/RF-20.md) |
| Bandeja de solicitudes y usuarios del Administrador (`<bugalu-solicitudes>`; suma documentos repetidos y textos aceptados) | [RF-01](../03-requerimientos/RF-01.md), [RF-17](../03-requerimientos/RF-17.md) |
| Perfil propio, editable, con modalidad, documento, integrantes, domicilio y redes (`<bugalu-perfil>`) y privacidad con consentimientos e historial (`<bugalu-privacidad>`, `islas/Privacidad.astro`, ruta `/app/perfil/privacidad/`; separada de Perfil para no duplicar estados), [spec de RF-17](../07-diseno/pantallas/RF-17-perfil.md) | [RF-01](../03-requerimientos/RF-01.md), [RF-17](../03-requerimientos/RF-17.md) |
| Aceptación de textos pendientes tras registrarse o ingresar (`<bugalu-aceptacion>`, `islas/Aceptacion.astro`, `/acceso/textos?volver=`; `<bugalu-acceso>` pasa por ahí y `LayoutApp` avisa; piezas en `servicios/aceptaciones.js`, `resumen-legal.js` y `perfil-datos.js`) | [RF-17](../03-requerimientos/RF-17.md) |
| Texto legal público por versión (`<bugalu-texto-legal tipo="…">`, `islas/TextoLegal.astro`, páginas `/legal/` y `/legal/{slug}/?version=`; pinta `contenido_html` saneado por el backend y lo vuelve a limpiar en el navegador; sin JS, el contacto del estudio) y textos del Administrador (`<bugalu-textos-legales vista="lista\|publicar">`, `islas/TextosLegales.astro`, sobre `IslaGestion`; rutas `/app/textos` y `/app/textos/publicar?tipo=`; consumo en `servicios/textos-legales.js`). La [spec](../07-diseno/pantallas/RF-17-textos-legales.md) también amplía el filtro `?documento=repetido` de `<bugalu-solicitudes>` | [RF-17](../03-requerimientos/RF-17.md) |
| Aviso descartable (`<bugalu-aviso>`) | Transversal ([aviso](../07-diseno/componentes/aviso.md)) |
| Carga de entregables y capturas (`<bugalu-carga-archivos>`, `islas/CargaArchivos.astro`; primero la variante `captura`, dentro de `<bugalu-pago>`) | [RF-05](../03-requerimientos/RF-05.md), [RF-09](../03-requerimientos/RF-09.md) |
| Reproductor con forma de onda y comentarios por timestamp (`<bugalu-reproductor>`) | [RF-10](../03-requerimientos/RF-10.md) |

El contador de PAGOS de la navegación no es isla: lo pinta el script de `LayoutApp` que ya carga el perfil ([navegación lateral](../07-diseno/componentes/navegacion-lateral.md#variantes)).
