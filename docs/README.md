# Bugalú Studio ERP — Índice documental

Fuente de verdad del proyecto. Lee este índice y carga **solo** los archivos que tu tarea referencia.

Validación: `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`

## Ruta de lectura por rol

| Rol | Leer primero |
|---|---|
| `leader` | Este índice completo · [leader](04-agentes/leader.md) · [equipo](04-agentes/equipo.md) · [decisiones](00-proyecto/decisiones/README.md) |
| `disenador-ui` | [disenador-ui](04-agentes/disenador-ui.md) → [brief](07-diseno/brief.md) → [figma](07-diseno/figma.md) (solo fase 2) → RF de la tarea |
| `dev_backend` | [dev-backend](04-agentes/dev-backend.md) → [backend-hexagonal](01-arquitectura/backend-hexagonal.md) → [modelo-datos](01-arquitectura/modelo-datos.md) → [convenciones](01-arquitectura/convenciones.md) → RF de la tarea |
| `dev_frontend` | [dev-frontend](04-agentes/dev-frontend.md) → [frontend-islas](01-arquitectura/frontend-islas.md) → [convenciones](01-arquitectura/convenciones.md) → [brief](07-diseno/brief.md) → RF y spec de pantalla de la tarea |
| `dev_audit` | [dev-audit](04-agentes/dev-audit.md) → [implementacion](05-protocolos/implementacion.md) → [pruebas](05-protocolos/pruebas.md) → tarea y entrega |
| `documentador` | [documentador](04-agentes/documentador.md) → este índice |

## 00 · Proyecto

[vision](00-proyecto/vision.md) · [alcance](00-proyecto/alcance.md) · [glosario](00-proyecto/glosario.md) · [decisiones](00-proyecto/decisiones/README.md)

## 01 · Arquitectura

[stack](01-arquitectura/stack.md) · [backend-hexagonal](01-arquitectura/backend-hexagonal.md) · [frontend-islas](01-arquitectura/frontend-islas.md) · [modelo-datos](01-arquitectura/modelo-datos.md) · [convenciones](01-arquitectura/convenciones.md)

## 02 · Dominio

[actores-roles](02-dominio/actores-roles.md) · [reglas-negocio](02-dominio/reglas-negocio.md) · [estados-reserva](02-dominio/estados-reserva.md)

Flujos: [ciclo-servicio](02-dominio/flujos/ciclo-servicio.md) · [registrar-reserva](02-dominio/flujos/registrar-reserva.md) · [agendar-asesoria](02-dominio/flujos/agendar-asesoria.md) · [versionado-feedback](02-dominio/flujos/versionado-feedback.md)

## Requerimientos

Orden de implementación (fase 7): RF-01 → RF-03/04 → RF-05/06 → RF-15 → RF-02 → RF-07/08 → RF-09/10 → RF-11/12 → RF-13 → RF-14.

| RF | Título | Módulo | Estado |
|---|---|---|---|
| [RF-01](03-requerimientos/RF-01.md) | Autenticar usuario y gestionar perfil | `identidad` | implementado |
| [RF-02](03-requerimientos/RF-02.md) | Simular precio y emitir cotización a medida | `catalogo` | borrador (CA-01…CA-05 implementados; CA-06 con RF-15) |
| [RF-03](03-requerimientos/RF-03.md) | Publicar y consultar franjas de sala | `reservas` | implementado |
| [RF-04](03-requerimientos/RF-04.md) | Registrar reserva de sala | `reservas` | implementado |
| [RF-05](03-requerimientos/RF-05.md) | Registrar y validar pagos | `pagos` | implementado |
| [RF-06](03-requerimientos/RF-06.md) | Gestionar estado de reserva y notificaciones | `reservas` | implementado |
| [RF-07](03-requerimientos/RF-07.md) | Asignar personal técnico a sala | `personal` | borrador |
| [RF-08](03-requerimientos/RF-08.md) | Administrar ficha de proyecto musical | `proyectos` | borrador |
| [RF-09](03-requerimientos/RF-09.md) | Cargar y versionar entregables de audio | `entregables` | borrador |
| [RF-10](03-requerimientos/RF-10.md) | Auditar audio y registrar observaciones técnicas | `entregables` | borrador |
| [RF-11](03-requerimientos/RF-11.md) | Cobrar posproducción | `pagos` | borrador |
| [RF-12](03-requerimientos/RF-12.md) | Descargar máster digital definitivo | `entregables` | borrador |
| [RF-13](03-requerimientos/RF-13.md) | Evaluar calidad y cierre de servicio | `proyectos` | borrador |
| [RF-14](03-requerimientos/RF-14.md) | Generar reportes de operatividad y gestión | `reportes` | borrador |
| [RF-15](03-requerimientos/RF-15.md) | Agendar asesoría artística | `asesorias` | borrador |
| [RF-16](03-requerimientos/RF-16.md) | Libro de Reclamaciones virtual | `reclamaciones` | borrador |
| [RF-17](03-requerimientos/RF-17.md) | Registro reforzado de artistas y aceptación de textos legales | `identidad` | borrador |
| [RF-18](03-requerimientos/RF-18.md) | Cancelar y reprogramar con política de niveles y créditos | `reservas` | borrador |
| [RF-19](03-requerimientos/RF-19.md) | Calendario de Google y videollamadas | `notificaciones` | borrador |
| [RF-20](03-requerimientos/RF-20.md) | Parámetros sensibles con barreras y auditoría | `catalogo` | borrador |

## 04 · Agentes

[equipo](04-agentes/equipo.md) · [skills-por-fase](04-agentes/skills-por-fase.md) · [leader](04-agentes/leader.md) · [disenador-ui](04-agentes/disenador-ui.md) · [dev-backend](04-agentes/dev-backend.md) · [dev-frontend](04-agentes/dev-frontend.md) · [dev-audit](04-agentes/dev-audit.md) · [documentador](04-agentes/documentador.md)

## 05 · Protocolos

[cambios](05-protocolos/cambios.md) · [implementacion](05-protocolos/implementacion.md) · [pruebas](05-protocolos/pruebas.md) · [integracion](05-protocolos/integracion.md)

## 06 · Operación

Montaje: desarrollo [montaje-local](06-operacion/montaje-local.md) · [pruebas-locales](06-operacion/pruebas-locales.md) — producción [produccion](06-operacion/produccion.md) · [produccion-supabase](06-operacion/produccion-supabase.md) · [produccion-servicios](06-operacion/produccion-servicios.md) · [produccion-exposicion](06-operacion/produccion-exposicion.md) · [produccion-mantenimiento](06-operacion/produccion-mantenimiento.md)

[montaje-local](06-operacion/montaje-local.md) · [entornos](06-operacion/entornos.md) · [despliegue](06-operacion/despliegue.md) · [herramientas-mcp](06-operacion/herramientas-mcp.md) · [credenciales-oauth](06-operacion/credenciales-oauth.md) · [correo-gmail](06-operacion/correo-gmail.md) · [calendario-google](06-operacion/calendario-google.md)

Empresa: [requisitos-empresariales](06-operacion/requisitos-empresariales.md) (trámites legales y administrativos para operaciones)

## 07 · Diseño

[brief](07-diseno/brief.md) · [figma](07-diseno/figma.md) · [tokens](07-diseno/tokens.md) · [componentes](07-diseno/componentes/README.md) · `fundamentos/`, [patrones](07-diseno/patrones/README.md), `pantallas/` (pantallas en la fase 7)

## 08 · Legal

[textos legales](08-legal/README.md) (borradores para revisión de un abogado, [ADR-012](00-proyecto/decisiones/ADR-012-textos-legales-y-consentimientos.md))

## Hoja de ruta

| Fase | Entregable | Rol | Estado |
|---|---|---|---|
| 0 | Segmentar `docs/`, `CLAUDE.md`, `.claude/agents/`, `.mcp.json` | leader | Hecho |
| 0b | Equipo multiagente y ciclo de bajo consumo ([equipo](04-agentes/equipo.md)); ADR-001 y ADR-002 cierran D-13 y D-14 | leader | Hecho |
| 1 | Cerrar D-01 a D-04 (ADR) y conciliar el flujo de contratación de Figma con los RF | leader + usuario | Hecho |
| 2 | Extracción única de Figma al brief técnico y skills `aplicar-brief` / `disenar-pantalla` | disenador-ui | Hecho |
| 3 | Esqueleto backend (`uv`, FastAPI, `compartido/`, módulo de ejemplo) y Supabase local (CLI + Docker) con migraciones base | dev_backend | Hecho |
| 4 | Esqueleto frontend (Astro, layouts, `tokens.css` desde el brief, componentes base, cliente API) | dev_frontend | Hecho |
| 5 | Skills propias del proyecto ([herramientas-mcp](06-operacion/herramientas-mcp.md#skills-propias-del-proyecto)) | leader | Hecho |
| 6 | Auditoría del esqueleto contra arquitectura, convenciones y brief | dev_audit (Opus) | Hecho |
| 7 | Implementación por RF en el orden indicado arriba | todos | En curso: RF-01, RF-03, RF-04, RF-05 y RF-06 hechos; RF-02 parcial; siguiente RF-15 |

Planes de implementación: `superpowers/plans/`. Spec original congelada: `superpowers/specs/PROYECTO-v0.2.md`.
