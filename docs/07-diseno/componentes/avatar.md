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

Con foto ([RF-15](../../03-requerimientos/RF-15.md), solo el perfil del profesional): la imagen llena la caja (`object-fit: cover`, recorte recto, sin efectos ni redondeo) sobre el mismo borde; la foto es contenido del usuario y se muestra tal cual. Sin foto, o si la imagen no carga (`error`), las iniciales: letra inicial de la primera y de la última palabra del nombre que se muestra (una sola palabra: su inicial), en mayúsculas.

## Variantes

| Tamaño | Medida | Uso |
|---|---|---|
| Pequeño | `medida-avatar-sm` | Cabecera, menciones |
| Medio | `medida-avatar-md` | Tabla, comentario, miembro asignado |
| Miniatura | `medida-miniatura`; iniciales en `fuente-tamano-titulo-md` | [Tarjeta de profesional](tarjeta-profesional.md) |
| Retrato | Ancho de su columna, como mucho `medida-columna-lateral`, `aspect-ratio: 1`; iniciales en `fuente-tamano-display` | Perfil público del profesional ([perfil público](../pantallas/RF-15-perfil-publico.md)) |

| Rol | Fondo |
|---|---|
| Artista / cliente | `color-fondo-destacado` |
| Personal interno | `color-fondo-invertido` con iniciales `color-texto-invertido` |
| Profesional | `color-fondo-destacado`, como el artista: es su cara ante el cliente |

En el panel interno no hay fotografía ([imagen](../fundamentos/iconografia-imagen.md#imagen-fotográfica), regla 3): las tablas usan Medio con iniciales. Única excepción, la vista previa de la foto que se sube en la [ficha](../pantallas/RF-15-ficha.md) (Miniatura), como la miniatura de una captura de pago.

## Estados

Estático. Con foto: mientras carga, la caja ya tiene su tamaño (dimensiones explícitas, sin salto) y las iniciales debajo; si falla, quedan las iniciales.

## Tokens

`medida-avatar-sm`, `medida-avatar-md`, `medida-miniatura`, `medida-columna-lateral`, `fuente-tamano-titulo-md`, `fuente-tamano-display`, `borde-grosor-fino`, `borde-radio-ninguno`, `color-borde-fuerte`, `color-fondo-destacado`, `color-fondo-invertido`, `color-texto-principal`, `color-texto-invertido`, `fuente-familia-tecnica`, `fuente-peso-medio`.

## Relaciones

En [cabecera-app](cabecera-app.md), [tabla](tabla.md), [comentario](comentario.md), [tarjeta-proyecto](tarjeta-proyecto.md) (responsable).

## Accesibilidad

- Decorativo cuando el nombre está al lado (`aria-hidden="true"`); si va solo, `role="img"` con `aria-label` del nombre completo.
- Con foto: `<img alt="Foto de {nombre}">` si va sola; `alt=""` si el nombre está al lado (como en la tarjeta y el perfil). `loading="lazy"` salvo el Retrato, con `width` y `height`.
- El rol no se deduce solo del fondo: donde importa (comentario, tabla), va en texto junto al nombre.

## Código

`frontend/src/componentes/Avatar.astro`, props `nombre`, `tamano` (`sm|md|miniatura|retrato`), `rol`, `foto` (URL opcional; la isla que lo pinta en el navegador cambia a iniciales en el evento `error` de la imagen).
