---
id: protocolo-pruebas
titulo: Protocolo de pruebas
estado: borrador
depende_de: []
---

# Protocolo de pruebas

| Nivel | Qué cubre | Herramienta propuesta |
|---|---|---|
| Unitarias | Dominio (entidades, reglas RN) sin I/O | `pytest` |
| Integración | Adaptadores de salida contra Supabase local | `pytest` |
| API | Endpoints FastAPI | `pytest` + cliente de pruebas de FastAPI |
| E2E | Flujos críticos ([CUS-04](../02-dominio/flujos/registrar-reserva.md), [CUS-09/10](../02-dominio/flujos/versionado-feedback.md)) | Playwright |

Calidad estática: `ruff` y `mypy` (backend), `astro check` (frontend).

Documentación: `python scripts/validar_docs.py docs` (ver [convenciones](../01-arquitectura/convenciones.md#documentacion)).

Toda entrega incluye el comando ejecutado y su salida resumida ([formato de entrega](implementacion.md#formato-de-entrega)).
