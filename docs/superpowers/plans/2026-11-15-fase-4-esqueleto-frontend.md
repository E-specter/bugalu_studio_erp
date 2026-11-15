# Fase 4 — Esqueleto frontend · Plan

> **Ejecución:** ciclo de bajo consumo ([implementacion](../../05-protocolos/implementacion.md#ciclo-de-bajo-consumo)). `dev-frontend` implementa TAREA-401 → 402 → 403 (403 incluye un ajuste de CORS de `dev-backend`). `disenador-ui` hace la revisión visual; `dev-audit` con `model: "opus"` cierra la fase.

**Goal:** Frontend Astro estático con tokens del brief, tres layouts, 11 componentes base, página de catálogo y cliente de la API con sesión de Supabase.

**Diseño aprobado por el usuario (2026-11-15):** Astro estable con salida estática, `npm`, JavaScript nativo; fuentes propias con `@fontsource`; `@supabase/supabase-js` solo para la sesión; 11 componentes base (el resto por RF en la fase 7); `/catalogo` solo en desarrollo; sin pantalla de acceso (RF-01, fase 7).

## Global Constraints

- [frontend-islas](../../01-arquitectura/frontend-islas.md), [convenciones](../../01-arquitectura/convenciones.md) e identificadores en español ASCII.
- Skill `aplicar-brief` cargada al empezar cada tarea; ningún valor visual fuera de `tokens.css` (que refleja exactamente [tokens](../../07-diseno/tokens.md), con las unidades de [espaciado-reticula](../../07-diseno/fundamentos/espaciado-reticula.md#unidades)).
- Cada componente sigue su ficha de [componentes](../../07-diseno/componentes/README.md): anatomía, variantes, estados comunes y propios, ARIA.
- WCAG 2.2 AA: axe sin violaciones; foco visible; `prefers-reduced-motion`; objetivos ≥ 24 × 24.
- Islas: `.astro` + `<script>` que registra `<bugalu-*>` con `customElements.define`; sin `client:*` ni frameworks UI.
- Variables de entorno públicas con prefijo `PUBLIC_`; ninguna clave secreta en el frontend (solo la publicable de Supabase).

## Review Focus

1. **Zoom y tamaño de letra:** a 200 % y con letra del navegador a 20 px, nada se corta ni se solapa (medidas en `rem`).
2. **Navegación móvil fija:** el foco nunca queda tapado al tabular (WCAG 2.4.11).
3. **Estados sin color:** seleccionado, actual y error se distinguen sin color (borde, icono, texto, ARIA).
4. **API caída o 401/503:** la interfaz muestra el estado de error del patrón [estados-sistema](../../07-diseno/patrones/estados-sistema.md), nunca una pantalla en blanco.
5. **Fuentes no cargadas:** la pila de respaldo mantiene la jerarquía y no hay salto de maquetación grave.

---

### TAREA-401: Proyecto Astro, tokens, base y layouts

- [ ] `frontend/` con Astro (salida estática) y `npm`; scripts `dev`, `build`, `check`, `test:e2e`.
- [ ] `src/estilos/tokens.css` (espejo de `tokens.md`) y `src/estilos/base.css` (reinicio, tipografía, foco, movimiento reducido, `scroll-padding-top: var(--medida-zona-fija-movil)` en móvil).
- [ ] Fuentes con `@fontsource` (Unbounded, Mona Sans, Geist, Geist Mono) solo con los pesos de `tokens.md`.
- [ ] `src/layouts/`: `LayoutBase.astro`, `LayoutPublico.astro`, `LayoutApp.astro` ([estructura-app](../../07-diseno/patrones/estructura-app.md)); el logotipo desde `docs/07-diseno/fundamentos/assets/` copiado a `public/` o `src/assets/` con sus reglas de color.
- [ ] Playwright + `@axe-core/playwright`: prueba de humo de los layouts (sin violaciones axe, foco visible).

### TAREA-402: Componentes base y catálogo

- [ ] `src/componentes/`: Boton, Campo, Casilla, EtiquetaTecnica, Aviso, IndicadorEstado, Panel, EncabezadoPantalla, CabeceraApp, NavegacionLateral, NavegacionTactil; isla `src/islas/Contrasena.astro` (`<bugalu-contrasena>`).
- [ ] `src/pages/catalogo.astro` (solo en desarrollo): cada componente con sus variantes y estados.
- [ ] Playwright: axe sin violaciones en `/catalogo`, Review Focus 1–3, capturas en escritorio (1440) y móvil (390).
- [ ] Actualizar la columna "Estado" del catálogo a `Implementado` en los 11.

### TAREA-403: Cliente de la API y sesión (`dev-frontend` + CORS de `dev-backend`)

- [ ] `src/servicios/sesion.js` (`@supabase/supabase-js`, URL y clave publicable desde `PUBLIC_*`) y `src/servicios/api.js` (base `PUBLIC_URL_API`, `Authorization: Bearer`, error `{error:{codigo,mensaje}}`, 401 → sesión no válida, 503 → servicio no disponible).
- [ ] Página `src/pages/app/perfil.astro` con `LayoutApp` que consume `GET /api/v1/perfil` y muestra cargando / no autenticado / error / datos.
- [ ] Backend: CORS solo para el origen del frontend de desarrollo, desde configuración (`dev-backend`, con prueba).
- [ ] Playwright: Review Focus 4 (API caída, 401, 503) con respuestas simuladas.
- [ ] `docs/06-operacion/montaje-local.md`: sección frontend.

### Cierre (`leader`)

- [ ] `disenador-ui`: revisión visual de capturas contra el brief y las fichas.
- [ ] `documentador`: changelog y hoja de ruta.
- [ ] Compuerta `dev-audit` Opus con este Review Focus; informe en `docs/superpowers/auditorias/`.
