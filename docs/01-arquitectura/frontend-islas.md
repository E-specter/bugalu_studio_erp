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
| Registro de pago con captura | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md) |
| Validación de pagos (Administrador) | [RF-05](../03-requerimientos/RF-05.md) |
| Contraseña: mostrar u ocultar y medidor de robustez (`<bugalu-contrasena>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Acceso: iniciar sesión, registrarse, solicitar acceso interno, recuperar y restablecer (`<bugalu-acceso>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Estado de la solicitud de acceso interno (`<bugalu-solicitud>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Reserva por pasos (`<bugalu-reserva>`) | [RF-02](../03-requerimientos/RF-02.md), [RF-04](../03-requerimientos/RF-04.md) |
| Mis reservas y agenda (`<bugalu-reservas>`) | [RF-04](../03-requerimientos/RF-04.md) |
| Publicación de franjas, cierres y parámetros (`<bugalu-franjas>`) | [RF-03](../03-requerimientos/RF-03.md) |
| Tarifas, recargos y feriados (`<bugalu-tarifas>`) | [RF-02](../03-requerimientos/RF-02.md) |
| Bandeja de solicitudes y usuarios del Administrador (`<bugalu-solicitudes>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Perfil propio, editable (`<bugalu-perfil>`) | [RF-01](../03-requerimientos/RF-01.md) |
| Aviso descartable (`<bugalu-aviso>`) | Transversal ([aviso](../07-diseno/componentes/aviso.md)) |
| Carga de entregables y capturas (`<bugalu-carga-archivos>`) | [RF-09](../03-requerimientos/RF-09.md) |
| Reproductor con forma de onda y comentarios por timestamp (`<bugalu-reproductor>`) | [RF-10](../03-requerimientos/RF-10.md) |
