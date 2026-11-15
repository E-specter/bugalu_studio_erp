---
id: patron-estructura-app
titulo: Patrón — Estructura de app y navegación
estado: borrador
depende_de: [diseno-brief, fund-espaciado-reticula]
---

# Estructura de app y navegación

Cuatro estructuras (layouts) cubren todas las pantallas de Figma. Toda pantalla nueva elige una; no se inventan estructuras.

| Estructura | Audiencia | Pantallas de origen | Layout Astro |
|---|---|---|---|
| Landing | Visitante | `44:4` | `layouts/Publico.astro` |
| Acceso | Todos | `112:61`, `112:193`, `112:286`, `112:385` | `layouts/Acceso.astro` |
| Flujo | Visitante y artista | `141:28605`–`141:29858` | `layouts/Flujo.astro` |
| App | Artista (portal) y personal (panel interno) | `145:*`, `161:*`, `169:*` | `layouts/App.astro` |

## App

```
┌ cabecera-app ───────────────────────────────────┐
├ navegacion-lateral ┬ main ─────────────────────┤
│ destinos           │ encabezado-pantalla        │
│                    │ métricas (4)               │
│ bloque de control  │ principal (≈70) │ lateral  │
│                    │ barra de estado            │
└────────────────────┴────────────────────────────┘
```

1. [cabecera-app](../componentes/cabecera-app.md) + [navegacion-lateral](../componentes/navegacion-lateral.md) (escritorio) o [navegacion-tactil](../componentes/navegacion-tactil.md) (móvil).
2. `<main>` empieza siempre con [encabezado-pantalla](../componentes/encabezado-pantalla.md).
3. Vistas de resumen (dashboard): [métricas](../componentes/metrica.md) → panel operativo (listado principal + columna lateral de próximas entregas y alertas) → actividad reciente ([lista-eventos](../componentes/lista-eventos.md)).
4. Vistas de detalle: principal (contenido del objeto) + lateral (acción o [resumen](../componentes/resumen-persistente.md) Ficha).
5. Opcional al pie: [indicador de estado](../componentes/indicador-estado.md) Barra.
6. **Lo fijo:** < `punto-quiebre-escritorio`, la fila 1 de la cabecera móvil y la navegación táctil son `sticky` y el documento lleva `scroll-padding-top: var(--medida-zona-fija-movil)` (WCAG 2.4.11, [navegación táctil](../componentes/navegacion-tactil.md)). En escritorio la cabecera no es fija; solo el [resumen persistente](../componentes/resumen-persistente.md) es `sticky`, en su columna.

**Portal vs. panel interno:** misma estructura. El portal muestra el proyecto del artista y su avance; el panel interno, la operación del estudio. Cambian destinos, bloque de control y densidad (el panel interno admite tablas compactas; el portal no).

## Acceso

Pantalla dividida en escritorio: columna de marca (logo, título técnico `[PORTAL_ARTISTAS]`, texto, estado), columna visual con [marco de registro](../componentes/marco-registro.md) e imagen, y columna de formulario con el pie técnico. En móvil, solo marca compacta + formulario. Interno y artista comparten estructura; cambia el texto y la imagen.

## Flujo

Sin navegación lateral: [cabecera-app](../componentes/cabecera-app.md) Flujo + [pasos](../componentes/pasos.md) + formulario + [resumen persistente](../componentes/resumen-persistente.md). Ver [flujo por pasos](flujo-por-pasos.md).

## Landing

Secciones a ancho completo, contenedor `medida-contenedor-max`, separación `espacio-20`. Orden de Figma: hero → manifiesto → pilares → proyectos → servicios → control de versiones → proceso → llamada al portal → pie. Cada sección: índice `[ 01 ]`, título display y descripción. El CTA principal es "Reservar" / "Cotizar" (botón primario grande).

## Navegación

- Un destino = una página con su URL; no hay pestañas que oculten contenido principal.
- El destino actual se marca en la navegación y en la ruta del encabezado.
- Volver: la ruta del [encabezado](../componentes/encabezado-pantalla.md) es la navegación jerárquica; no se depende del botón atrás del navegador.
- Enlace "Saltar al contenido" en toda estructura: primer enfocable, visible al recibir foco, lleva a `<main id="contenido" tabindex="-1">`. El `<main>` recibe el foco para que el siguiente Tab siga desde ahí, pero **no muestra anillo** (`main:focus { outline: none }`): no es un control y un contorno a toda la página confunde; el anillo vuelve en el primer control enfocado.

## Formato de datos

| Dato | Formato | Ejemplo |
|---|---|---|
| Fecha | `D MMM AAAA` | 18 nov 2026 |
| Fecha y hora | `D MMM, HH:mm` (24 h) | 18 nov, 14:30 |
| Relativa (< 7 días) | "hace N h / ayer" + absoluta en `title` | hace 2 h |
| Importe | `S/ 1 250,00` (PEN, [reglas de negocio](../../02-dominio/reglas-negocio.md)) con `tabular-nums` | S/ 450,00 |
| Duración de audio | `m:ss` | 3:45 |
| Códigos | Prefijo + número con ceros | PRY-014, PAG-031 |

Zona horaria del estudio (Lima); idioma de interfaz: español.
