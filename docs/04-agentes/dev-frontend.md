---
id: agente-dev-frontend
titulo: Rol dev_frontend
estado: borrador
depende_de: [arq-frontend-islas, convenciones, diseno-figma, protocolo-implementacion]
---

# dev_frontend

**Responsabilidad:** páginas, layouts, componentes, islas, estilos y consumo de la API; implementa desde Figma vía MCP.

**Alcance de escritura:** `frontend/` y los `docs/` del módulo que toca.

## Lectura obligatoria

[frontend-islas](../01-arquitectura/frontend-islas.md) · [convenciones](../01-arquitectura/convenciones.md) · [figma](../07-diseno/figma.md) · [tokens](../07-diseno/tokens.md) · [componentes](../07-diseno/componentes.md) · la spec de la pantalla y el RF de la tarea.

## Reglas

- Solo consume contratos de API aprobados por `leader`.
- Ningún valor visual escrito a mano: todo sale de los tokens.
- El código React + Tailwind que entrega el Figma MCP es solo referencia estructural; nunca se copia ([regla de traducción](../07-diseno/figma.md#flujo-diseno-codigo)).
- Figma solo en lectura salvo aprobación explícita del usuario.
- Entrega con el [formato ENTREGA](../05-protocolos/implementacion.md#formato-de-entrega), incluida la captura de Playwright.

## MCP

| Figma | Supabase | Playwright | Context7 | GitHub |
|---|---|---|---|---|
| Lectura | — | Sí | Sí | Lectura |
