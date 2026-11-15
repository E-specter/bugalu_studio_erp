---
id: comp-avatar
titulo: Componente — Avatar
estado: borrador
depende_de: [diseno-tokens]
---

# Avatar

Capa "Avatar" (40 apariciones): perfil en cabecera (`161:640`, 26 px), identidad en tabla de clientes (`161:842`, 38 px) y autor de comentario (`145:3617`, 38 px). Identifica a una persona con sus iniciales.

## Anatomía

1. Caja cuadrada (`borde-radio-ninguno`), `borde-grosor-fino` `color-borde-fuerte`, fondo `color-fondo-destacado`.
2. Iniciales: `fuente-familia-tecnica`, `fuente-peso-medio`, mayúsculas, centradas, `color-texto-principal`.

Sin fotografía: las pantallas solo usan iniciales y así se mantiene (no hay carga de foto de perfil en ningún RF).

## Variantes

| Tamaño | Medida | Uso |
|---|---|---|
| Pequeño | `medida-avatar-sm` | Cabecera, menciones |
| Medio | `medida-avatar-md` | Tabla, comentario, miembro asignado |

| Rol | Fondo |
|---|---|
| Artista / cliente | `color-fondo-destacado` |
| Personal interno | `color-fondo-invertido` con iniciales `color-texto-invertido` |

## Estados

Estático.

## Tokens

`medida-avatar-sm`, `medida-avatar-md`, `borde-grosor-fino`, `borde-radio-ninguno`, `color-borde-fuerte`, `color-fondo-destacado`, `color-fondo-invertido`, `color-texto-principal`, `color-texto-invertido`, `fuente-familia-tecnica`, `fuente-peso-medio`.

## Relaciones

En [cabecera-app](cabecera-app.md), [tabla](tabla.md), [comentario](comentario.md), [tarjeta-proyecto](tarjeta-proyecto.md) (responsable).

## Accesibilidad

- Decorativo cuando el nombre está al lado (`aria-hidden="true"`); si va solo, `role="img"` con `aria-label` del nombre completo.

## Código

`frontend/src/componentes/Avatar.astro`, props `nombre`, `tamano`, `rol`.
