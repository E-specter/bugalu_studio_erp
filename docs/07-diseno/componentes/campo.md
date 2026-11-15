---
id: comp-campo
titulo: Componente — Campo
estado: borrador
depende_de: [diseno-tokens, fund-tipografia]
---

# Campo

Capa "Campo" del brief de proyecto (`141:28788`: "Etiqueta y ayuda" + "Entrada"), campos de acceso (`112:363`, `112:367`) y "Búsqueda" del directorio de clientes (`161:842`). Entrada de un dato con su etiqueta.

## Anatomía

1. Etiqueta: `fuente-familia-tecnica`, `fuente-tamano-micro`, mayúsculas; en accesos con prefijo `//` (`// CORREO REGISTRADO`). Indicador de obligatorio: texto "(obligatorio)", no solo asterisco.
2. Ayuda opcional a la derecha de la etiqueta o debajo: `fuente-tamano-pequeno`, `color-texto-secundario`.
3. Entrada: `color-fondo-claro`, `borde-grosor-base` `color-borde-fuerte`, `borde-radio-ninguno`, `sombra-plana` (`112:365`), alto `medida-control-base`, relleno `espacio-4`, valor en `fuente-familia-texto` `fuente-tamano-base`.
4. Mensaje de error bajo la entrada.

Separación etiqueta → entrada: `espacio-2`. Campos en fila: hueco `espacio-3`.

## Variantes

| Variante | Elemento | Notas |
|---|---|---|
| Texto | `<input type="text|email|tel|url|number|date">` | La base |
| Área | `<textarea>` | Alto mínimo 2 × `medida-control-base`; contador de caracteres si hay límite (`145:3617` "Contador") |
| Contraseña | `<input type="password">` + botón `eye` | El botón de mostrar es la isla `<bugalu-contrasena>`; sin JS el campo funciona igual |
| Búsqueda | `<input type="search">` con icono `search` a la izquierda | Atajo de teclado opcional en `fuente-familia-tecnica` a la derecha (`161:842` "Atajo") |
| Selector | `<select>` nativo con la misma caja | Para listas cerradas (servicio, profesional) |
| Archivo | — | Usar [carga-archivos](carga-archivos.md) |

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

| Estado | Visual |
|---|---|
| Hover | Borde sin cambio; fondo `color-fondo-lienzo` |
| Foco | Anillo común; la etiqueta no cambia de color |
| Error | Borde `color-texto-alerta`; mensaje en `color-texto-alerta` con `alert-triangle` y texto que dice cómo corregir |
| Solo lectura | Sin borde de caja, solo regla inferior `borde-grosor-fino`; `readonly` |
| Deshabilitado | Común; el valor sigue legible |

## Tokens

`color-fondo-claro`, `color-fondo-lienzo`, `sombra-plana`, `color-borde-fuerte`, `color-texto-principal`, `color-texto-secundario`, `color-texto-alerta`, `borde-grosor-base`, `borde-grosor-fino`, `borde-radio-ninguno`, `medida-control-base`, `medida-icono-sm`, `espacio-2`, `espacio-3`, `espacio-4`, `fuente-*`.

## Relaciones

Compone los [formularios](../patrones/formularios.md). Para opciones múltiples: [casilla](casilla.md) o [tarjeta-opcion](tarjeta-opcion.md).

## Accesibilidad

- `<label for>` siempre visible; el marcador de posición nunca sustituye a la etiqueta.
- Ayuda y error unidos con `aria-describedby`; error con `aria-invalid="true"`.
- `autocomplete` correcto en datos personales (`email`, `name`, `tel`, `current-password`, `new-password`) (WCAG 1.3.5).
- Botón de mostrar contraseña: `aria-label="Mostrar contraseña"` y `aria-pressed`.

## Código

`frontend/src/componentes/Campo.astro` (props `tipo`, `nombre`, `etiqueta`, `ayuda`, `error`, `obligatorio`); isla `frontend/src/islas/Contrasena.astro` registra `<bugalu-contrasena>`.
