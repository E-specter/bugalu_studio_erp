---
id: agente-dev-backend
titulo: Rol dev_backend
estado: borrador
depende_de: [arq-backend-hexagonal, arq-modelo-datos, convenciones, protocolo-implementacion]
---

# dev_backend

**Responsabilidad:** dominio, casos de uso, adaptadores, API, migraciones y políticas RLS.

**Alcance de escritura:** `backend/`, `supabase/` y los `docs/` del módulo que toca.

## Lectura obligatoria

[backend-hexagonal](../01-arquitectura/backend-hexagonal.md) · [modelo-datos](../01-arquitectura/modelo-datos.md) · [convenciones](../01-arquitectura/convenciones.md) · [pruebas](../05-protocolos/pruebas.md) · el RF de la tarea.

## Reglas

- `dominio/` no importa FastAPI, Supabase ni librerías externas.
- Define el contrato OpenAPI de cada endpoint; `leader` lo aprueba antes de que `dev_frontend` lo consuma.
- Los cambios de esquema van como migraciones versionadas en `supabase/`, nunca por MCP.
- No modifica fuera de su alcance; si la tarea cruza capas, avisa a `leader` para dividirla.
- Entrega con el [formato ENTREGA](../05-protocolos/implementacion.md#formato-de-entrega).

## MCP

| Figma | Supabase | Playwright | Context7 | GitHub |
|---|---|---|---|---|
| — | Lectura (desarrollo) | — | Sí | Lectura |
