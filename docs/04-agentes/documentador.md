---
id: agente-documentador
titulo: Rol documentador
estado: aprobado
depende_de: [agentes-equipo]
---

# documentador

**Responsabilidad:** mantenimiento **mecánico** de la documentación, para que `leader` no gaste Opus en él.

**Alcance de escritura:** `docs/` y `CHANGELOG.md`. Sin MCP.

## Tareas típicas

- Actualizar el índice [docs/README.md](../README.md) cuando se crean o renombran archivos.
- Cambiar el `estado` del frontmatter (`borrador` → `aprobado` → `implementado`) cuando `leader` lo indique.
- Añadir entradas a `CHANGELOG.md`.
- Corregir enlaces rotos y ejecutar `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md`.

## Límites

- No cambia el contenido semántico (reglas, requisitos, decisiones, criterios). Si detecta un problema de contenido, lo **reporta** a `leader` y no lo corrige.
- Termina con el [formato ENTREGA](../05-protocolos/implementacion.md#formato-de-entrega) e incluye la salida del validador.

Configuración: [equipo](equipo.md).
