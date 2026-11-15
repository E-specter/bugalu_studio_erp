---
id: comp-navegacion-lateral
titulo: Componente — Navegación lateral
estado: borrador
depende_de: [diseno-tokens, comp-cabecera-app]
---

# Navegación lateral

"Navegación lateral" (`161:651`, `145:2928`): sección + elementos de navegación (icono, etiqueta, metadato) y, al pie, un bloque de control ("Control de sala" en el panel interno, "Control del proyecto" en el portal).

## Anatomía

1. Columna de `medida-nav-lateral`, fondo `color-fondo-superficie`, regla derecha `borde-grosor-base` `color-borde-fuerte`, relleno `espacio-4`.
2. Título de sección: `fuente-familia-tecnica`, `fuente-tamano-micro`, `color-texto-secundario`.
3. Elemento de navegación: alto `medida-control-base`, icono `medida-icono-md`, etiqueta `fuente-tamano-pequeno`, metadato a la derecha (contador en `fuente-familia-tecnica`). Separación entre elementos `espacio-2`.
4. Bloque de control al pie: mini panel con lectura (canal / nivel), fase actual, [barra de progreso](barra-progreso.md) y ayuda.

## Variantes

| Variante | Elementos | Bloque al pie |
|---|---|---|
| Estudio (panel interno) | Dashboard, clientes, proyectos, entregables, revisiones, agenda… según rol | Control de sala: sesión en curso |
| Portal (artista) | Dashboard, proyecto, versiones, revisiones, historial | Control del proyecto: fase y avance |

Los elementos dependen del rol ([RF-01](../../03-requerimientos/RF-01.md)); nunca se muestra un destino al que el rol no tiene acceso.

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

| Estado | Visual |
|---|---|
| Hover | Fondo `color-fondo-claro` |
| Actual | Fondo `color-fondo-destacado`, `borde-grosor-base` `color-borde-fuerte`, etiqueta en `fuente-peso-titulo` |
| Con pendientes | Metadato en [etiqueta](etiqueta-tecnica.md) Alerta (p. ej. pagos por validar) |

## Tokens

`medida-nav-lateral`, `medida-control-base`, `medida-icono-md`, `color-fondo-superficie`, `color-fondo-claro`, `color-fondo-destacado`, `color-borde-fuerte`, `color-texto-secundario`, `borde-grosor-base`, `espacio-2`, `espacio-4`, `fuente-*`.

## Relaciones

Solo ≥ `punto-quiebre-escritorio`; por debajo la sustituye [navegacion-tactil](navegacion-tactil.md) con los mismos destinos.

## Accesibilidad

- `<nav aria-label="Principal">` con `<ul>` de enlaces; el actual con `aria-current="page"`.
- El contador del metadato se lee con contexto: `<span class="visualmente-oculto">pendientes:</span> 3`.

## Código

`frontend/src/componentes/NavegacionLateral.astro`, props `variante`, `destinos` (etiqueta, href, icono, contador), `actual`; ranura `control`.
