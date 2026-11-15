---
id: ADR-001
titulo: Figma como fuente de extracción única del diseño
estado: aprobado
depende_de: [D-13]
---

# ADR-001: Figma como fuente de extracción única del diseño

## Contexto

El archivo de Figma ya contiene unas 32 pantallas (landing, guía de estilo brutalista, accesos, portal del artista en escritorio y móvil, panel interno), pero no tiene biblioteca de componentes ni variables. D-13 pedía fijar el archivo maestro, el plan y el asiento, porque de ellos dependen los límites del MCP de Figma.

## Opciones consideradas

1. Figma como fuente viva: se diseña ahí y el código se sincroniza.
2. **Figma como fuente de extracción única: el estilo se traslada una vez a un brief técnico y a skills, y después no se usa más.**

## Decisión

Opción 2 (usuario, 2026-11-15).

| Campo | Valor |
|---|---|
| Archivo | `bugalu_studio_erp`, file key `GxpFTDX6L0uFwg6xlulhXF` |
| Páginas | `references`, `brief`, `landing-page`, `blueprint-funcional`, `login`, `erp` |
| Plan y asiento (`whoami`, 2026-11-15) | Asiento **Full** en un plan **Pro** (equipo «Integrador I»). La cuenta pertenece además a un equipo Starter con asiento View |
| Límite esperado | ~200 llamadas/día, **solo si el archivo vive en el equipo Pro**. En el equipo Starter: 6–20 llamadas/mes |
| Quién lo usa | Solo `disenador-ui`, solo en lectura, solo en la fase 2 |

**Condición previa a la fase 2:** el archivo debe estar en el equipo «Integrador I». Si se duplica en lugar de moverse, se actualiza aquí el file key.

## Consecuencias

- La fuente de verdad visual pasa a ser [docs/07-diseno/](../../07-diseno/brief.md); el registro del origen es [figma](../../07-diseno/figma.md).
- `dev-frontend` y `dev-audit` no usan Figma: comparan contra el brief y la spec de pantalla.
- Las pantallas nuevas se diseñan desde el brief; los cambios de estilo se hacen extendiendo el brief, no en Figma.
- Code Connect deja de tener sentido: [ADR-002](ADR-002-code-connect-descartado.md).
