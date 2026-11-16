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
   La columna ocupa todo el alto disponible bajo la cabecera (la regla derecha llega al pie de la ventana aunque el contenido sea corto).
2. Título de sección: `fuente-familia-tecnica`, `fuente-tamano-micro`, mayúsculas, `color-texto-secundario`; dice el área según la variante ("ESTUDIO", "PORTAL").
3. Elemento de navegación: alto `medida-control-base`, icono `medida-icono-md`, etiqueta `fuente-tamano-pequeno`, contador opcional a la derecha. Separación entre elementos `espacio-2`. El contador solo existe para **pendientes que piden acción** (pagos por validar, revisiones abiertas) y siempre es una [etiqueta](etiqueta-tecnica.md) Alerta; los totales informativos no van en la navegación.
4. Bloque de control al pie: mini panel con lectura (canal / nivel), fase actual, [barra de progreso](barra-progreso.md) y ayuda.

## Variantes

| Variante | Elementos | Bloque al pie |
|---|---|---|
| Estudio (panel interno) | Dashboard, clientes, proyectos, entregables, revisiones, agenda… según rol | Control de sala: sesión en curso |
| Portal (artista) | Dashboard, proyecto, versiones, revisiones, historial | Control del proyecto: fase y avance |

Los elementos dependen del rol ([RF-01](../../03-requerimientos/RF-01.md)); nunca se muestra un destino al que el rol no tiene acceso.

Destinos implementados (etiqueta ≤ 9 caracteres · icono · ruta):

| Rol | Destinos |
|---|---|
| Cliente | INICIO (`house`, `/app/`) · RESERVAS (`calendar-check`, `/app/reservas/`) · PERFIL (menú de la cabecera) |
| Personal | INICIO · AGENDA (`calendar`, `/app/agenda/`) |
| Administrador | INICIO · AGENDA · ACCESOS (`user-plus`) · USUARIOS (`users`) · FRANJAS (`calendar-cog`, `/app/franjas/`) · TARIFAS (`tag`, `/app/tarifas/`). En móvil, TARIFAS (sexto) va al menú de la [cabecera](cabecera-app.md), con `aria-current="page"` cuando es la sección actual ([navegación táctil](navegacion-tactil.md)) |

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

| Estado | Visual |
|---|---|
| Hover | Fondo `color-fondo-claro` |
| Actual | Fondo `color-fondo-destacado`, `borde-grosor-base` `color-borde-fuerte`, etiqueta en `fuente-peso-titulo` |
| Con pendientes | Contador en [etiqueta](etiqueta-tecnica.md) Alerta |
| Rol sin cargar | Estado neutro mientras llega el perfil: el título de sección ("ESTUDIO" / "PORTAL") nace vacío con su línea reservada (`visibility: hidden`, sin salto de maquetación) y aparece al conocer el rol; si el perfil no carga, sigue oculto. Los destinos comunes se pintan ya; los que dependen del rol entran **al final** de la lista, sin desplazar los existentes. Nunca se pinta una variante por defecto que luego cambia (un artista no debe leer "ESTUDIO" ni "PANEL INTERNO"). Igual en la [navegación táctil](navegacion-tactil.md) y en el área de la [cabecera](cabecera-app.md) |

## Tokens

`medida-nav-lateral`, `medida-control-base`, `medida-icono-md`, `color-fondo-superficie`, `color-fondo-claro`, `color-fondo-destacado`, `color-borde-fuerte`, `color-texto-secundario`, `borde-grosor-base`, `espacio-2`, `espacio-4`, `fuente-*`.

## Relaciones

Solo ≥ `punto-quiebre-escritorio`; por debajo la sustituye [navegacion-tactil](navegacion-tactil.md) con los mismos destinos.

## Accesibilidad

- `<nav aria-label="Principal">` con `<ul>` de enlaces; el actual con `aria-current="page"`.
- El contador del metadato se lee con contexto: `<span class="visualmente-oculto">pendientes:</span> 3`.

## Código

`frontend/src/componentes/NavegacionLateral.astro`, props `variante`, `destinos` (etiqueta, href, icono, contador), `actual`, `etiqueta` (`aria-label` del `<nav>`, por defecto "Principal"); ranura `control`.
