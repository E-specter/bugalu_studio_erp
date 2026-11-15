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
├── astro.config.mjs
├── public/
└── src/
    ├── pages/            # rutas (nombre reservado por Astro)
    ├── layouts/          # nombre reservado por convención Astro
    ├── componentes/      # .astro estáticos, sin JS
    ├── islas/            # interactivos: franjas, agenda, pagos, reproductor, carga de archivos
    ├── servicios/        # cliente HTTP hacia la API
    └── estilos/          # tokens.css, base.css
```

## Islas identificadas

| Isla | Requerimiento |
|---|---|
| Franjas de sala y simulación | [RF-02](../03-requerimientos/RF-02.md), [RF-03](../03-requerimientos/RF-03.md), [RF-04](../03-requerimientos/RF-04.md) |
| Agenda de asesoría | [RF-15](../03-requerimientos/RF-15.md) |
| Registro de pago con captura | [RF-05](../03-requerimientos/RF-05.md), [RF-11](../03-requerimientos/RF-11.md) |
| Validación de pagos (Administrador) | [RF-05](../03-requerimientos/RF-05.md) |
| Carga de entregables (drag-and-drop) | [RF-09](../03-requerimientos/RF-09.md) |
| Reproductor con forma de onda y comentarios por timestamp | [RF-10](../03-requerimientos/RF-10.md) |
