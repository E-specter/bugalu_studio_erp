# Bugalú Studio ERP — Índice documental

Fuente de verdad del proyecto. Lee este índice y carga **solo** los archivos que tu tarea referencia.

Validación: `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`

## Ruta de lectura por rol

| Rol | Leer primero |
|---|---|
| `leader` | Este índice completo · [leader](04-agentes/leader.md) · [decisiones](00-proyecto/decisiones/README.md) |
| `dev_backend` | [dev-backend](04-agentes/dev-backend.md) → [backend-hexagonal](01-arquitectura/backend-hexagonal.md) → [modelo-datos](01-arquitectura/modelo-datos.md) → [convenciones](01-arquitectura/convenciones.md) → RF de la tarea |
| `dev_frontend` | [dev-frontend](04-agentes/dev-frontend.md) → [frontend-islas](01-arquitectura/frontend-islas.md) → [convenciones](01-arquitectura/convenciones.md) → [07-diseno](07-diseno/figma.md) → RF y pantalla de la tarea |
| `dev_audit` | [dev-audit](04-agentes/dev-audit.md) → [implementacion](05-protocolos/implementacion.md) → [pruebas](05-protocolos/pruebas.md) → tarea y entrega |

## 00 · Proyecto

[vision](00-proyecto/vision.md) · [alcance](00-proyecto/alcance.md) · [glosario](00-proyecto/glosario.md) · [decisiones](00-proyecto/decisiones/README.md)

## 01 · Arquitectura

[stack](01-arquitectura/stack.md) · [backend-hexagonal](01-arquitectura/backend-hexagonal.md) · [frontend-islas](01-arquitectura/frontend-islas.md) · [modelo-datos](01-arquitectura/modelo-datos.md) · [convenciones](01-arquitectura/convenciones.md)

## 02 · Dominio

[actores-roles](02-dominio/actores-roles.md) · [reglas-negocio](02-dominio/reglas-negocio.md) · [estados-reserva](02-dominio/estados-reserva.md)

Flujos: [ciclo-servicio](02-dominio/flujos/ciclo-servicio.md) · [registrar-reserva](02-dominio/flujos/registrar-reserva.md) · [versionado-feedback](02-dominio/flujos/versionado-feedback.md)

## Requerimientos

Orden de implementación (fase 7): RF-01 → RF-03/04 → RF-05/06 → RF-07/08 → RF-09/10 → RF-11/12 → RF-13 → RF-02 → RF-14.

| RF | Título | Módulo | Estado |
|---|---|---|---|
| [RF-01](03-requerimientos/RF-01.md) | Autenticar usuario y gestionar perfil | `identidad` | borrador |
| [RF-02](03-requerimientos/RF-02.md) | Solicitar y generar cotización técnica | `catalogo` | borrador |
| [RF-03](03-requerimientos/RF-03.md) | Consultar disponibilidad de salas | `reservas` | borrador |
| [RF-04](03-requerimientos/RF-04.md) | Registrar reserva de sala técnica | `reservas` | borrador |
| [RF-05](03-requerimientos/RF-05.md) | Procesar pago de anticipo | `pagos` | borrador |
| [RF-06](03-requerimientos/RF-06.md) | Gestionar estado de reserva y notificaciones | `reservas` | borrador |
| [RF-07](03-requerimientos/RF-07.md) | Asignar personal técnico a sala | `personal` | borrador |
| [RF-08](03-requerimientos/RF-08.md) | Administrar ficha de proyecto musical | `proyectos` | borrador |
| [RF-09](03-requerimientos/RF-09.md) | Cargar y versionar entregables de audio | `entregables` | borrador |
| [RF-10](03-requerimientos/RF-10.md) | Auditar audio y registrar observaciones técnicas | `entregables` | borrador |
| [RF-11](03-requerimientos/RF-11.md) | Liquidar saldo final de proyecto | `pagos` | borrador |
| [RF-12](03-requerimientos/RF-12.md) | Descargar máster digital definitivo | `entregables` | borrador |
| [RF-13](03-requerimientos/RF-13.md) | Evaluar calidad y cierre de servicio | `proyectos` | borrador |
| [RF-14](03-requerimientos/RF-14.md) | Generar reportes de operatividad y gestión | `reportes` | borrador |

## 04 · Agentes

[leader](04-agentes/leader.md) · [dev-backend](04-agentes/dev-backend.md) · [dev-frontend](04-agentes/dev-frontend.md) · [dev-audit](04-agentes/dev-audit.md)

## 05 · Protocolos

[cambios](05-protocolos/cambios.md) · [implementacion](05-protocolos/implementacion.md) · [pruebas](05-protocolos/pruebas.md) · [integracion](05-protocolos/integracion.md)

## 06 · Operación

[montaje-local](06-operacion/montaje-local.md) · [entornos](06-operacion/entornos.md) · [despliegue](06-operacion/despliegue.md) · [herramientas-mcp](06-operacion/herramientas-mcp.md)

## 07 · Diseño

[brief](07-diseno/brief.md) · [figma](07-diseno/figma.md) · [tokens](07-diseno/tokens.md) · [componentes](07-diseno/componentes.md) · `pantallas/` (vacío hasta la fase 2)

## Hoja de ruta

| Fase | Entregable | Rol | Estado |
|---|---|---|---|
| 0 | Segmentar `docs/`, `CLAUDE.md`, `.claude/agents/`, `.mcp.json` | leader | Hecho |
| 1 | Cerrar D-01 a D-04 y D-13 (ADR); conectar Figma, Supabase y Playwright MCP | leader + usuario | Siguiente |
| 2 | Brief de diseño, fundamentos y componentes base en Figma | usuario + leader | — |
| 3 | Esqueleto backend (`uv`, FastAPI, `compartido/`, módulo de ejemplo) y Supabase local con migraciones base | dev_backend | — |
| 4 | Esqueleto frontend (Astro, layouts, tokens sincronizados desde Figma, cliente API) | dev_frontend | — |
| 5 | Skills propias del proyecto ([herramientas-mcp](06-operacion/herramientas-mcp.md#skills-propias-del-proyecto-fase-5)) | leader | — |
| 6 | Auditoría del esqueleto contra arquitectura, convenciones y diseño | dev_audit | — |
| 7 | Implementación por RF en el orden indicado arriba | todos | — |

Planes de implementación: `superpowers/plans/`. Spec original congelada: `superpowers/specs/PROYECTO-v0.2.md`.
