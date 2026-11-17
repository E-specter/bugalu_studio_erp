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
| Foco | `outline` de `borde-grosor-base` en `color-foco-anillo` (`color-foco-invertido` sobre navy) con separación `borde-grosor-base` | Solo `:focus-visible`; nunca se elimina sin sustituto. Excepción: los destinos no interactivos de foco por programa (`tabindex="-1"`): el de "Saltar al contenido" ([estructura de app](../patrones/estructura-app.md#navegación)) y los títulos (`h1`, `h2`) que reciben el foco al cargar un paso o abrir un panel. Los avisos enfocados sí llevan anillo |
| Activo | Desplazamiento de tecla solo si el componente lleva `sombra-plana` ([forma](../fundamentos/forma-elevacion.md#interacción-física)); sin sombra, ningún cambio propio | — |
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
| Aviso | [aviso](aviso.md) | `componentes/Aviso.astro` + isla `<bugalu-aviso>` (descartable) | Implementado |
| Indicador de estado | [indicador-estado](indicador-estado.md) | `componentes/IndicadorEstado.astro` | Implementado |
| Barra de progreso | [barra-progreso](barra-progreso.md) | `componentes/BarraProgreso.astro` | Borrador |
| Avatar | [avatar](avatar.md) | `componentes/Avatar.astro` | Borrador |
| Métrica | [metrica](metrica.md) | `componentes/Metrica.astro` | Borrador |
| Panel | [panel](panel.md) | `componentes/Panel.astro` | Implementado |
| Encabezado de pantalla | [encabezado-pantalla](encabezado-pantalla.md) | `componentes/EncabezadoPantalla.astro` | Implementado |
| Cabecera de app | [cabecera-app](cabecera-app.md) | `componentes/CabeceraApp.astro` | Implementado |
| Navegación lateral | [navegacion-lateral](navegacion-lateral.md) | `componentes/NavegacionLateral.astro` | Implementado |
| Navegación táctil | [navegacion-tactil](navegacion-tactil.md) | `componentes/NavegacionTactil.astro` | Implementado |
| Pasos | [pasos](pasos.md) | `componentes/Pasos.astro` | Implementado |
| Barra de acciones | [barra-acciones](barra-acciones.md) | `componentes/BarraAcciones.astro` | Implementado (Flujo, Formulario, Decisión y Móvil) |
| Resumen persistente | [resumen-persistente](resumen-persistente.md) | `componentes/ResumenPersistente.astro` | Borrador |
| Tabla | [tabla](tabla.md) | `componentes/Tabla.astro` | Implementado |
| Tarjeta de proyecto | [tarjeta-proyecto](tarjeta-proyecto.md) | `componentes/TarjetaProyecto.astro` | Borrador |
| Lista de eventos | [lista-eventos](lista-eventos.md) | `componentes/ListaEventos.astro` | Borrador |
| Archivo | [archivo](archivo.md) | `componentes/Archivo.astro` | Implementado (Adjunto y Lectura; Descarga entra con RF-12) |
| Tarjeta de versión | [tarjeta-version](tarjeta-version.md) | `componentes/TarjetaVersion.astro` | Borrador |
| Comentario | [comentario](comentario.md) | `componentes/Comentario.astro` | Borrador |
| Marco de registro | [marco-registro](marco-registro.md) | `componentes/MarcoRegistro.astro` | Implementado |
| Resumen legal | [resumen-legal](resumen-legal.md) | `componentes/ResumenLegal.astro` | Borrador (RF-17) |
| Pie público | [pie-publico](pie-publico.md) | `componentes/PiePublico.astro` | Borrador (RF-17) |
| Calendario | [calendario](calendario.md) | isla `<bugalu-calendario>` | Implementado |
| Reproductor | [reproductor](reproductor.md) | isla `<bugalu-reproductor>` | Borrador |
| Carga de archivos | [carga-archivos](carga-archivos.md) | isla `<bugalu-carga-archivos>` (`islas/CargaArchivos.astro`) | Implementado (Captura de pago; audio y referencias entran con su RF) |
| Registro de pago | [registrar-pago](../pantallas/RF-05-registrar-pago.md) | isla `<bugalu-pago>` (`islas/Pago.astro`) | Implementado |
| Pagos del Administrador | [pagos](../pantallas/RF-05-pagos.md) | isla `<bugalu-pagos>` (`islas/Pagos.astro`) | Implementado |
| Cambio sensible | [cambios sensibles](../pantallas/RF-20-cambios-sensibles.md) | isla `<bugalu-cambio-sensible>` (`islas/CambioSensible.astro`; la montan `<bugalu-tarifas>` y `<bugalu-franjas>`) | Implementado (ajustes pendientes de TAREA-RF20-6) |
| Registro de cambios | [registro de cambios](../pantallas/RF-20-registro-cambios.md) | isla `<bugalu-registro-cambios>` (`islas/RegistroCambios.astro`) | Implementado (ajustes pendientes de TAREA-RF20-6) |

Rutas relativas a `frontend/src/`. Islas en `islas/<Nombre>.astro`.

## Reglas de las fichas

- **Variantes responsivas** (Móvil de cabecera y encabezado): no son props; el componente cambia con el punto de quiebre. El catálogo de desarrollo las muestra según el ancho de la ventana y se comprueban con las capturas de escritorio y móvil.
- **Atributos extra:** los componentes con control (`Boton`, `Campo`, `Casilla`) y `IndicadorEstado` reenvían al elemento nativo los atributos que no son props (`autocomplete`, `aria-*`, `role`, `disabled`, `form`…). La ficha no los enumera.
- **Props fuera de la ficha:** se aceptan si la ficha los recoge en su sección Código; si no, primero se amplía la ficha.

## Piezas internas

`frontend/src/componentes/internos/` contiene piezas que solo usan los componentes; **no son del catálogo** y una pantalla nunca las importa:

| Pieza | Qué es | La usan |
|---|---|---|
| `Icono.astro` + `lucide.js` | SVG en línea de un icono de la [tabla de iconos](../fundamentos/iconografia-imagen.md#iconos), decorativo (`aria-hidden`), `medida-icono-sm` o `-md` | Todos los que llevan icono |
| `MensajeError.astro` | Mensaje de error con `alert-triangle` en `color-texto-alerta` ([estados comunes](#estados-comunes), Error) | [campo](campo.md), [casilla](casilla.md) (error de grupo) |

Si una pantalla necesita un icono o un mensaje suelto, se usa el componente del catálogo que lo contiene; si no existe, se escribe su ficha.

## Fuera del catálogo (no hay diseño en Figma)

Diálogo de confirmación y notificación emergente: no aparecen en ninguna pantalla. Si un RF los necesita, se agrega su ficha antes de la pantalla; mientras tanto, la confirmación usa una página o paso propio y el resultado un [aviso](aviso.md) ([estados del sistema](../patrones/estados-sistema.md)).
