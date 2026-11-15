---
id: diseno-brief
titulo: Brief técnico de diseño — índice
estado: borrador
depende_de: [ADR-001]
---

# Brief técnico de diseño

Fuente de verdad visual del proyecto. Se extrae una vez de Figma ([origen](figma.md)) y desde entonces se **extiende de forma coherente** desde aquí. Las skills `aplicar-brief` y `disenar-pantalla` lo resumen y enlazan, nunca lo copian.

## Principios

- Ningún valor visual (color, tamaño, espaciado, radio, sombra) se escribe a mano en el código: todo sale de [tokens](tokens.md).
- Toda pantalla se compone con componentes del [catálogo](componentes/README.md); si falta uno, primero se agrega al catálogo.
- Cada pantalla tiene su spec en `pantallas/RF-xx-<pantalla>.md`, con el RF que cubre.
- Insumo de identidad: *Taller de marca Bugalú* (Alesin Branding Studio, 2026) y la guía brutalista del archivo de Figma.

## Decisiones artísticas

Pendiente (fase 2). Dirección visual, atributos de marca y el porqué de cada decisión.

## Índice

| Tema | Archivo | Estado |
|---|---|---|
| Logotipo y variantes | `fundamentos/logotipo.md` | Pendiente (fase 2) |
| Color | `fundamentos/color.md` | Pendiente (fase 2) |
| Tipografía | `fundamentos/tipografia.md` | Pendiente (fase 2) |
| Espaciado y retícula | `fundamentos/espaciado-reticula.md` | Pendiente (fase 2) |
| Forma y elevación | `fundamentos/forma-elevacion.md` | Pendiente (fase 2) |
| Movimiento | `fundamentos/movimiento.md` | Pendiente (fase 2) |
| Iconografía e imagen | `fundamentos/iconografia-imagen.md` | Pendiente (fase 2) |
| Tokens | [tokens](tokens.md) | Convención definida |
| Componentes | [catálogo](componentes/README.md) | Pendiente (fase 2) |
| Patrones | `patrones/` | Pendiente (fase 2) |
| Pantallas | `pantallas/` | Pendiente (fase 2) |

## Transversales

- **Audiencias:** Artista/Cliente (experiencia pública, móvil y escritorio); personal interno y Administrador (panel operativo, escritorio).
- **Principios UX:** jerarquía clara, densidad según el perfil, retroalimentación de estados y prevención de errores. Detalle: pendiente (fase 2).
- **Adaptabilidad:** puntos de quiebre por dispositivo; la cabina trabaja en escritorio y el cliente en móvil y escritorio. Detalle: pendiente (fase 2).
- **Accesibilidad:** WCAG 2.2 AA: contraste, foco visible, navegación por teclado, textos alternativos.
- **Movimiento:** respeto de `prefers-reduced-motion`.
