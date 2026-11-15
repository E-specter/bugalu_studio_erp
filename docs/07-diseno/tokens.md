---
id: diseno-tokens
titulo: Tokens de diseño (Figma ↔ CSS)
estado: borrador
depende_de: [diseno-figma]
---

# Tokens de diseño

- Las variables de Figma son el origen; `frontend/src/estilos/tokens.css` es su reflejo.
- Todo cambio de variable en Figma genera una tarea de actualización de tokens antes de cualquier cambio de pantalla.
- Este archivo mantiene la tabla de correspondencia.

## Convención

Ruta de variable en Figma con `/` → propiedad CSS con prefijo `--` y `-`.

| Variable Figma | Propiedad CSS |
|---|---|
| `color/fondo/primario` | `--color-fondo-primario` |
| `espacio/4` | `--espacio-4` |

## Correspondencia

Pendiente (fases 2 y 4): se llena con la skill `sincronizar-tokens` al definir los fundamentos en Figma.
