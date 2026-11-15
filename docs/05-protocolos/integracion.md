---
id: protocolo-integracion
titulo: Protocolo de integración
estado: borrador
depende_de: [protocolo-implementacion]
---

# Protocolo de integración

1. Auditoría **APROBADO** ([dev-audit](../04-agentes/dev-audit.md)).
2. Pruebas en verde (ver [pruebas](pruebas.md)).
3. `leader` autoriza el merge a la rama principal; no hay merges automáticos.
4. `leader` actualiza el changelog, el índice [docs/README.md](../README.md) y el `estado` del RF (`implementado`).
