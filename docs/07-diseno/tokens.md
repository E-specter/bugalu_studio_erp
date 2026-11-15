---
id: diseno-tokens
titulo: Tokens de diseño
estado: borrador
depende_de: [diseno-brief]
---

# Tokens de diseño

- Este archivo es el **origen** de los tokens; `frontend/src/estilos/tokens.css` es su reflejo exacto.
- Se extraen una vez de Figma (fase 2) y desde entonces se cambian **aquí**: primero el token, después las pantallas.
- Un token nuevo solo se agrega si ningún token existente cubre el uso.

## Convención de nombres

`<categoria>-<rol>-<variante>` en `kebab-case`, con prefijo `--` en CSS.

| Token | Propiedad CSS |
|---|---|
| `color-fondo-primario` | `--color-fondo-primario` |
| `espacio-4` | `--espacio-4` |

## Tabla de tokens

Columnas: token · valor · uso · origen en Figma (solo durante la extracción).

Pendiente (fase 2).
