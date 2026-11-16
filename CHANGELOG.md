# Changelog

## 2026-11-16

- **RF-01 Autenticar usuario y gestionar perfil (implementado):** registro de artistas con medidor de robustez (8 caracteres con minúsculas, mayúsculas, números y símbolos, exigido por Supabase Auth), acceso de artistas e interno, recuperación de contraseña, verificación de correo propia antes del primer pago, solicitud de acceso del personal con aprobación del Administrador, gestión de roles con protección del último administrador (serializada), perfil editable y Google preparado para artistas (desactivado hasta tener credenciales). ADR-008 (D-10 fuera de la v1). 184 pruebas de backend, 88 pgTAP, 317 de Playwright y recorrido real de punta a punta (`npm run test:e2e:real`). Auditoría Opus aprobada tras corregir una carrera del último administrador y un 500 por byte NUL.

## 2026-11-15

- **Auditoría del esqueleto (fase 6):** PostgREST deja de exponer `public` (el backend es el único camino a los datos) y el backend se conecta con el rol `bugalu_api` en lugar del superusuario (ampliación de ADR-007); formato de error único también para 404/405/422; ningún token, base caída ni JWKS roto devuelve 500; foco y anuncio al reintentar el perfil, nombres coherentes y objetivos táctiles; herramientas de escritura del conector de Supabase de claude.ai denegadas. 50 pruebas de backend, 23 pgTAP y 55 de Playwright.
- **Skills propias (fase 5):** `crear-componente`, `crear-isla`, `crear-slice-backend`, `crear-migracion`, `auditar-entrega` y `crear-tarea`, probadas en seco sobre casos reales. El contrato API vive en el RF; convenciones de claves foráneas (`id_<tabla>`) y fechas (`timestamptz`, ISO 8601, hora de Lima). MCP de Supabase local solo de lectura.
- **Frontend (fase 4):** Astro estático con `tokens.css` generado y comprobado contra `tokens.md`, fuentes propias (@fontsource), layouts público y de app, 11 componentes base con la isla `<bugalu-contrasena>` y `<bugalu-aviso>`, catálogo de desarrollo y página de perfil con cliente de la API y sesión de Supabase. 48 pruebas Playwright con axe (WCAG 2.2 AA); CORS del backend por lista de orígenes.
- **Backend (fase 3):** Supabase local propio (`project_id` bugalu, puertos 456xx) con tabla `usuario` (RLS, rol no editable por el usuario) y buckets privados; esqueleto FastAPI hexagonal con `uv`, acceso a PostgreSQL con psycopg y RLS por transacción (ADR-007), JWT de Supabase Auth y `GET /api/v1/perfil`. 23 pruebas de backend y 14 pgTAP.
- **Diseño (fase 2):** brief técnico extraído de Figma y verificado (12 llamadas; figma.md congelado): fundamentos, 90+ tokens con contraste WCAG 2.2 AA, 28 fichas de componentes, patrones y logotipo en SVG. Skills `aplicar-brief` (precargada en disenador-ui y dev-frontend) y `disenar-pantalla`.
- **Contratación y D-01..D-04 (fase 1):** ADR-003..006 (Supabase Storage, pagos sin pasarela con validación manual, Supabase Auth, claves UUID). Flujo real del estudio: franjas semanales por sala, reserva de grabación o ensayo en múltiplos de 30 min, asesoría con profesional (presencial o virtual), cuotas 50/50 o plan a medida, posproducción 50/50. Reglas RN-12..RN-16, RF-02..05 y RF-11 reescritos, RF-15 nuevo. Spec: docs/superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md.
- **Equipo multiagente:** seis roles (`leader`, `disenador-ui`, `dev-backend`, `dev-frontend`, `dev-audit`, `documentador`) con modelo, effort, maxTurns, skills precargadas y herramientas por lista permitida. Configuración en `docs/04-agentes/equipo.md`.
- **Ciclo de bajo consumo:** un implementador más `dev-audit` por tarea; Opus solo en las compuertas.
- **Decisiones:** ADR-001 (Figma como fuente de extracción única) y ADR-002 (Code Connect descartado) cierran D-13 y D-14.
- **Supabase solo local:** `.mcp.json` apunta al MCP del stack local.
- **Validador:** comprueba que los agentes coincidan con `equipo.md`.
- **Diseño:** medidas en `rem`/`em` (solo bordes, sombra y efectos en px) y logotipo navy o lavanda con contraste mínimo 7:1.

## 2026-11-14

- **Fase 0:** `PROYECTO.md` se segmenta en `docs/` (RF-01..RF-14, reglas, arquitectura, protocolos), con `CLAUDE.md`, los subagentes iniciales, `.mcp.json` y el validador de documentación.
