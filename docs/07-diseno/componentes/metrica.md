---
id: comp-metrica
titulo: Componente — Métrica
estado: borrador
depende_de: [diseno-tokens, comp-panel]
---

# Métrica

Capa "Métrica" de "Indicadores generales" (`161:609`, `145:2885`, `169:4267`; 28 apariciones): etiqueta + valor + metadato. Un número clave del panel.

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base` `color-borde-fuerte`, relleno `espacio-4`.
2. Etiqueta: `fuente-familia-tecnica`, `fuente-tamano-micro`, mayúsculas, `color-texto-secundario`.
3. Valor: `fuente-familia-titulo`, `fuente-tamano-titulo-md`, `tabular-nums`.
4. Metadato: `fuente-tamano-pequeno`, `color-texto-secundario` (comparación, periodo: "+2 esta semana").

Fila de 4 en escritorio (hueco `espacio-3`), 2 por fila en móvil.

## Variantes

| Variante | Diferencia | Uso |
|---|---|---|
| Base | — | Contadores (proyectos activos, sesiones de la semana) |
| Con tendencia | Metadato con icono `arrow-up-right` / `arrow-down-right` y texto ("+12 % vs. mes anterior") | Reportes ([RF-14](../../03-requerimientos/RF-14.md)) |
| Atención | Borde `color-texto-alerta` y metadato explicativo | Pagos por validar vencidos, entregas atrasadas |

## Estados

Estático. Carga: el valor se sustituye por "—" con `aria-busy="true"`; sin datos: "0" y metadato "Sin registros en el periodo" (nunca vacío).

## Tokens

`color-fondo-superficie`, `color-borde-fuerte`, `color-texto-secundario`, `color-texto-alerta`, `borde-grosor-base`, `espacio-3`, `espacio-4`, `fuente-familia-tecnica`, `fuente-familia-titulo`, `fuente-tamano-micro`, `fuente-tamano-titulo-md`, `fuente-tamano-pequeno`.

## Relaciones

Grupo de métricas bajo el [encabezado-pantalla](encabezado-pantalla.md) en [estructura de app](../patrones/estructura-app.md). Si enlaza a un listado filtrado, toda la métrica es un `<a>` con los [estados comunes](README.md#estados-comunes).

## Accesibilidad

- Lista `<dl>`: etiqueta en `<dt>`, valor en `<dd>`; así se lee "Proyectos activos: 12".
- La tendencia se expresa en texto, no solo con la flecha.

## Código

`frontend/src/componentes/Metrica.astro`, props `etiqueta`, `valor`, `metadato`, `variante`, `href`.
