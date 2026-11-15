---
id: comp-panel
titulo: Componente — Panel
estado: borrador
depende_de: [diseno-tokens, fund-forma-elevacion]
---

# Panel

Capa "Panel" y bloques con "Título de sección" (76 apariciones): "Identificador" (código + título) + "Ayuda" (`141:28788`, `161:609`). Agrupa contenido relacionado bajo un título.

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base` `color-borde-fuerte`, `borde-radio-ninguno`, relleno `espacio-5`.
2. Título de sección:
   - Identificador: código en `fuente-familia-tecnica` `fuente-tamano-micro` (`[02]`, `A1`) + título en `fuente-familia-titulo` `fuente-tamano-titulo-sm` mayúsculas.
   - Ayuda opcional: `fuente-tamano-pequeno`, `color-texto-secundario`.
   - Acción o etiqueta opcional alineada a la derecha.
3. Cuerpo: separado del título por `espacio-4`.

Paneles apilados con hueco `espacio-6`.

## Variantes

| Variante | Diferencia | Uso |
|---|---|---|
| Base | — | Agrupaciones de formulario, listados |
| Sin borde | Sin contenedor, solo título + regla `borde-grosor-fino` | Secciones del contenido principal (actividad reciente) |
| Destacado | Fondo `color-fondo-destacado` | Un bloque que debe leerse primero (entrega destacada, próximo hito). El lavanda no es la única señal: va primero en el orden y su título lo nombra ("PRÓXIMA ENTREGA") |
| Técnico | Fondo `color-fondo-invertido`, texto `color-texto-invertido`, foco `color-foco-invertido`. Borde parcial (efecto 10, `88:344`): solo el lado izquierdo en `color-borde-tecnico`, mismo grosor `borde-grosor-base` que el resto del contorno ([forma](../fundamentos/forma-elevacion.md#bordes), regla 1); decorativo | Paneles de control: cadena de señal, monitor |
| Lateral | Ancho `medida-columna-lateral` | Panel de acción a la derecha (transformación, comentario) |

## Estados

Estático. Carga (prop `cargando`): el cuerpo lleva `aria-busy="true"` y el texto "Cargando…" en lugar de la ranura; vacío y error según [estados del sistema](../patrones/estados-sistema.md).

## Tokens

`color-fondo-superficie`, `color-fondo-destacado`, `color-fondo-invertido`, `color-borde-fuerte`, `color-borde-tecnico`, `color-texto-secundario`, `color-texto-invertido`, `borde-grosor-base`, `borde-grosor-fino`, `borde-radio-ninguno`, `espacio-4`, `espacio-5`, `espacio-6`, `medida-columna-lateral`, `fuente-*`.

## Relaciones

Contenedor de casi todo: [tabla](tabla.md), [lista-eventos](lista-eventos.md), [campo](campo.md), [metrica](metrica.md).

## Accesibilidad

- `<section aria-labelledby>` apuntando al título, que es un encabezado del nivel que corresponda (`<h2>` bajo el título de pantalla).
- El código del identificador es parte del texto del encabezado, no un elemento separado que interrumpa la lectura.

## Código

`frontend/src/componentes/Panel.astro`, props `codigo`, `titulo`, `ayuda`, `variante`, `nivel` (2–4), `cargando`, `id` (base del id del título; si dos paneles comparten título en la vista, es obligatorio); ranuras `acciones` y por defecto.
