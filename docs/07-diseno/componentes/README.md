# Catálogo de componentes

Índice de los componentes del sistema visual. Cada componente tiene su ficha `<componente>.md` en esta carpeta (anatomía, variantes, estados, tokens, relaciones, accesibilidad y su ruta de código). Extraídos en la fase 2 de las pantallas de Figma ([registro](../figma.md)); el diseño se extiende desde aquí.

## Reglas

- Componente sin interactividad → `frontend/src/componentes/<Nombre>.astro`, sin JS.
- Componente interactivo → isla en `frontend/src/islas/` que registra `<bugalu-<nombre>>` ([frontend-islas](../../01-arquitectura/frontend-islas.md)).
- Antes de crear una isla, se intenta con HTML nativo: `<details>`, `<dialog>`, `<select>`, formularios `GET` y enlaces. Solo es isla lo que de verdad necesita JS.
- Una pantalla solo usa componentes de este catálogo. Si falta uno, primero se agrega su ficha.
- Valores visuales: solo [tokens](../tokens.md).

## Estados comunes

Todos los componentes interactivos los cumplen; cada ficha solo documenta lo que cambia.

| Estado | Visual | Comportamiento |
|---|---|---|
| Reposo | Según la variante | — |
| Hover | Cambio de fondo según la variante en `movimiento-duracion-rapida` | Solo con puntero (`@media (hover: hover)`) |
| Foco | `outline` de `borde-grosor-base` en `color-foco-anillo` (`color-foco-invertido` sobre navy) con separación `borde-grosor-base` | Solo `:focus-visible`; nunca se elimina sin sustituto |
| Activo | Desplazamiento de tecla ([forma](../fundamentos/forma-elevacion.md#interacción-física)) | — |
| Deshabilitado | `opacity: var(--efecto-opacidad-capa)`, sin sombra, cursor `not-allowed` | Atributo `disabled` nativo; si debe seguir siendo enfocable para explicar por qué, `aria-disabled="true"` + texto de ayuda |
| Error | Borde en `color-texto-alerta` + mensaje con icono `alert-triangle` | `aria-invalid="true"` y `aria-describedby` al mensaje |
| Carga | Contenido sustituido por texto "Cargando…" o barra de progreso; mantiene su tamaño | `aria-busy="true"` en el contenedor |

## Componentes

| Componente | Ficha | Código | Estado |
|---|---|---|---|
| Botón | [boton](boton.md) | `componentes/Boton.astro` | Implementado |
| Etiqueta técnica | [etiqueta-tecnica](etiqueta-tecnica.md) | `componentes/EtiquetaTecnica.astro` | Implementado |
| Campo | [campo](campo.md) | `componentes/Campo.astro` + isla `<bugalu-contrasena>` | Implementado |
| Casilla | [casilla](casilla.md) | `componentes/Casilla.astro` | Implementado |
| Tarjeta de opción | [tarjeta-opcion](tarjeta-opcion.md) | `componentes/TarjetaOpcion.astro` | Borrador |
| Aviso | [aviso](aviso.md) | `componentes/Aviso.astro` | Implementado |
| Indicador de estado | [indicador-estado](indicador-estado.md) | `componentes/IndicadorEstado.astro` | Implementado |
| Barra de progreso | [barra-progreso](barra-progreso.md) | `componentes/BarraProgreso.astro` | Borrador |
| Avatar | [avatar](avatar.md) | `componentes/Avatar.astro` | Borrador |
| Métrica | [metrica](metrica.md) | `componentes/Metrica.astro` | Borrador |
| Panel | [panel](panel.md) | `componentes/Panel.astro` | Implementado |
| Encabezado de pantalla | [encabezado-pantalla](encabezado-pantalla.md) | `componentes/EncabezadoPantalla.astro` | Implementado |
| Cabecera de app | [cabecera-app](cabecera-app.md) | `componentes/CabeceraApp.astro` | Implementado |
| Navegación lateral | [navegacion-lateral](navegacion-lateral.md) | `componentes/NavegacionLateral.astro` | Implementado |
| Navegación táctil | [navegacion-tactil](navegacion-tactil.md) | `componentes/NavegacionTactil.astro` | Implementado |
| Pasos | [pasos](pasos.md) | `componentes/Pasos.astro` | Borrador |
| Barra de acciones | [barra-acciones](barra-acciones.md) | `componentes/BarraAcciones.astro` | Borrador |
| Resumen persistente | [resumen-persistente](resumen-persistente.md) | `componentes/ResumenPersistente.astro` | Borrador |
| Tabla | [tabla](tabla.md) | `componentes/Tabla.astro` | Borrador |
| Tarjeta de proyecto | [tarjeta-proyecto](tarjeta-proyecto.md) | `componentes/TarjetaProyecto.astro` | Borrador |
| Lista de eventos | [lista-eventos](lista-eventos.md) | `componentes/ListaEventos.astro` | Borrador |
| Archivo | [archivo](archivo.md) | `componentes/Archivo.astro` | Borrador |
| Tarjeta de versión | [tarjeta-version](tarjeta-version.md) | `componentes/TarjetaVersion.astro` | Borrador |
| Comentario | [comentario](comentario.md) | `componentes/Comentario.astro` | Borrador |
| Marco de registro | [marco-registro](marco-registro.md) | `componentes/MarcoRegistro.astro` | Borrador |
| Calendario | [calendario](calendario.md) | isla `<bugalu-calendario>` | Borrador |
| Reproductor | [reproductor](reproductor.md) | isla `<bugalu-reproductor>` | Borrador |
| Carga de archivos | [carga-archivos](carga-archivos.md) | isla `<bugalu-carga-archivos>` | Borrador |

Rutas relativas a `frontend/src/`. Islas en `islas/<Nombre>.astro`.

## Fuera del catálogo (no hay diseño en Figma)

Diálogo de confirmación y notificación emergente: no aparecen en ninguna pantalla. Si un RF los necesita, se agrega su ficha antes de la pantalla; mientras tanto, la confirmación usa una página o paso propio y el resultado un [aviso](aviso.md) ([estados del sistema](../patrones/estados-sistema.md)).
