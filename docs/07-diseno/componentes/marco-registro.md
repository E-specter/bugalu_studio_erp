---
id: comp-marco-registro
titulo: Componente — Marco de registro
estado: borrador
depende_de: [diseno-tokens, fund-iconografia-imagen]
---

# Marco de registro

Decoración técnica de los accesos (`112:61`, `112:286`): cuatro marcas de registro en las esquinas (`m1`–`m4`, 24 × 24: cruz de líneas + punto), escuadras en dos esquinas opuestas (`FX / Borde`, 110 × 3) y scanlines sobre el panel. Aplica los efectos 07 y 11 de la guía (`88:277`, `88:366`).

## Anatomía

1. Superficie: `color-fondo-invertido` (o imagen con tratamiento duotono).
2. Marcas de registro: en cada esquina, a `espacio-5` del borde; cruz de `borde-grosor-fino` + punto de `medida-senal`, en `color-borde-tecnico`.
3. Escuadras: esquinas superior izquierda e inferior derecha, `borde-grosor-grueso` `color-borde-tecnico`.
4. Patrón opcional: scanlines con `efecto-patron-paso` a `efecto-opacidad-capa`.
5. Contenido en ranura (texto de bienvenida, nota del estudio).

## Variantes

| Variante | Uso |
|---|---|
| Panel | Columna visual de los accesos e inicio del portal |
| Esquinas | Solo escuadras, sobre un [panel](panel.md) Técnico |

## Estados

Decorativo, sin estados.

## Tokens

`color-fondo-invertido`, `color-borde-tecnico`, `borde-grosor-fino`, `borde-grosor-grueso`, `medida-senal`, `espacio-5`, `efecto-patron-paso`, `efecto-opacidad-capa`.

## Relaciones

En [estructura de app](../patrones/estructura-app.md#acceso). Nunca en el panel interno operativo.

## Accesibilidad

- Marcas, escuadras y patrón con `aria-hidden="true"` (pseudoelementos o SVG decorativo).
- El texto de la ranura mantiene el contraste de `color-texto-invertido` sobre `color-fondo-invertido`; el patrón no pasa por debajo del texto.

## Código

`frontend/src/componentes/MarcoRegistro.astro`, prop `variante`; ranura por defecto.
