---
id: diseno-tokens
titulo: Tokens de diseño
estado: borrador
depende_de: [diseno-brief]
---

# Tokens de diseño

- Este archivo es el **origen** de los tokens; `frontend/src/estilos/tokens.css` es su reflejo exacto.
- Se extrajeron una vez de Figma (fase 2, [registro](figma.md)) y desde entonces se cambian **aquí**: primero el token, después las pantallas.
- Un token nuevo solo se agrega si ningún token existente cubre el uso.
- El componente usa el token **de rol** (`color-texto-principal`), nunca el de marca (`color-marca-navy`): los de marca solo alimentan a los de rol.

## Convención de nombres

`<categoria>-<rol>-<variante>` en `kebab-case` ASCII, con prefijo `--` en CSS (`color-fondo-lienzo` → `--color-fondo-lienzo`). Escalas numéricas: `espacio-N` = N × 4 px (`espacio-1-5` = 6 px).

Un valor que es otro token (`color-marca-navy`) se escribe en CSS como `var(--color-marca-navy)`.

Columna **origen**: nodo de Figma del que sale el valor, o `inferido` cuando la decisión es del brief (razón en el fundamento enlazado). Contraste: [color](fundamentos/color.md#contraste-verificado).

## Color — marca (solo alimentan a los de rol)

| Token | Valor | Uso | Origen |
|---|---|---|---|
| `color-marca-lavanda` | `#E1C9E3` | Brand Primary | `86:80`, `35:29` |
| `color-marca-navy` | `#262757` | Brand Secondary | `86:86`, `35:29` |
| `color-marca-lienzo` | `#EBEBFF` | Canvas Background | `86:92`, `35:29` |
| `color-marca-naranja` | `#FF5A1F` | Action Primary (naranja reactivo) | `86:98` |
| `color-marca-tinta` | `#231F20` | Contraste | `35:29` |

## Color — rol

| Token | Valor | Uso | Origen |
|---|---|---|---|
| `color-fondo-lienzo` | `color-marca-lienzo` | Fondo de página | `86:93` |
| `color-fondo-superficie` | `#FFFFFF` | Paneles, tablas, campos sobre el lienzo | inferido |
| `color-fondo-destacado` | `color-marca-lavanda` | Botón primario, etiqueta activa, sección destacada, fila seleccionada | `86:81` |
| `color-fondo-invertido` | `color-marca-navy` | Botón secundario, paneles de acceso, cabecera de tabla | `86:87` |
| `color-fondo-alerta` | `color-marca-naranja` | Hover de acción, alerta crítica | `86:99` |
| `color-texto-principal` | `color-marca-navy` | Texto, títulos y valores | `86:87` |
| `color-texto-secundario` | `#4A4B7D` | Ayudas, metadatos, etiquetas de columna | inferido |
| `color-texto-invertido` | `color-marca-lienzo` | Texto sobre `color-fondo-invertido` | inferido |
| `color-texto-sobre-alerta` | `color-marca-tinta` | Texto sobre `color-fondo-alerta` | inferido |
| `color-texto-alerta` | `#9A3009` | Error y alerta como texto o borde sobre fondos claros | inferido |
| `color-texto-exito` | `#14633A` | Estado correcto (validado, aprobado) | inferido |
| `color-texto-aviso` | `#6E4700` | Estado pendiente o en riesgo | inferido |
| `color-borde-fuerte` | `color-marca-navy` | Bordes de componente y reglas | `86:63`, `86:167` |
| `color-borde-tecnico` | `color-marca-lavanda` | Líneas técnicas y marcas de registro (decorativo) | `88:358`, `88:380` |
| `color-foco-anillo` | `color-marca-navy` | Anillo de foco sobre fondos claros | inferido |
| `color-foco-invertido` | `color-marca-lavanda` | Anillo de foco sobre `color-fondo-invertido` | inferido |

## Tipografía

| Token | Valor | Uso | Origen |
|---|---|---|---|
| `fuente-familia-display` | `"Unbounded", system-ui, sans-serif` | Titulares hero y de pantalla | `86:112` |
| `fuente-familia-titulo` | `"Mona Sans", system-ui, sans-serif` | Subtítulos, títulos de sección, botones | `86:119`, `12:40` |
| `fuente-familia-texto` | `"Geist", system-ui, sans-serif` | Lectura y datos | `86:126` |
| `fuente-familia-tecnica` | `"Geist Mono", ui-monospace, monospace` | Códigos, archivos, etiquetas técnicas, tiempos | inferido |
| `fuente-peso-display` | `900` | Unbounded Heavy | `86:112` |
| `fuente-peso-titulo` | `700` | Mona Sans Bold | `86:119` |
| `fuente-peso-medio` | `500` | Etiquetas y valores de tabla | inferido |
| `fuente-peso-regular` | `400` | Geist Regular | `86:126` |
| `fuente-tamano-micro` | `0.6875rem` (11 px) | Etiquetas técnicas, columnas, metadatos | inferido (Figma ≈10 px) |
| `fuente-tamano-pequeno` | `0.75rem` (12 px) | Navegación, ayudas, rutas | pantallas `erp` |
| `fuente-tamano-base` | `0.875rem` (14 px) | Texto de interfaz, celdas, campos | pantallas `erp` |
| `fuente-tamano-lectura` | `1rem` (16 px) | Párrafos y descripciones | `86:127` |
| `fuente-tamano-titulo-sm` | `1.25rem` (20 px) | Títulos de panel y tarjeta | `86:62` |
| `fuente-tamano-titulo-md` | `1.5rem` (24 px) | Subtítulos de sección, valor de métrica | `86:120` |
| `fuente-tamano-titulo-lg` | `2rem` (32 px) | Título de pantalla | pantallas `erp` |
| `fuente-tamano-display` | `3rem` (48 px) | Titular hero | `86:113` |
| `fuente-tamano-hero` | `clamp(2.5rem, 5vw, 4.5rem)` | Titulares de la landing | inferido (`48:91`) |
| `fuente-interlineado-display` | `1` | Display | `86:113` |
| `fuente-interlineado-titulo` | `1.2` | Títulos | `86:120` |
| `fuente-interlineado-interfaz` | `1.3` | Texto de interfaz ≤14 px | inferido |
| `fuente-interlineado-lectura` | `1.5` | Párrafos | `86:127` |
| `fuente-espaciado-etiqueta` | `0.08em` | Mayúsculas técnicas | inferido |

## Espacio

| Token | Valor | Uso | Origen |
|---|---|---|---|
| `espacio-1` | `4px` | Separación mínima icono–texto | `88:293` |
| `espacio-1-5` | `6px` | Relleno vertical de etiqueta | `86:184` |
| `espacio-2` | `8px` | Separación dentro de grupos | pantallas `erp` |
| `espacio-3` | `12px` | Relleno de etiqueta y columna de tablero; hueco entre métricas | `86:184`, `161:1083` |
| `espacio-4` | `16px` | Relleno de métrica, celda y control | pantallas `erp`, `112:365` |
| `espacio-5` | `20px` | Relleno de panel | `141:28788` |
| `espacio-6` | `24px` | Hueco entre paneles y columnas | `131:150` |
| `espacio-8` | `32px` | Margen de contenido y hueco de la landing | `48:100`, `161:688` |
| `espacio-12` | `48px` | Margen lateral de página ancha | `44:4`, `86:20` |
| `espacio-20` | `80px` | Separación entre secciones de la landing | `48:88` |

## Medidas, quiebres y forma

| Token | Valor | Uso | Origen |
|---|---|---|---|
| `medida-nav-lateral` | `220px` | Ancho de la navegación lateral | `161:651` |
| `medida-cabecera-escritorio` | `82px` | Alto de la cabecera de app | `161:610` |
| `medida-cabecera-movil` | `68px` | Alto de la cabecera móvil | `169:5451` |
| `medida-nav-tactil` | `56px` | Alto de la navegación táctil | `169:5490` |
| `medida-contenedor-max` | `1344px` | Ancho máximo de contenido | `44:4` |
| `medida-columna-lateral` | `344px` | Columna lateral (resumen, panel de acción) | `161:688`, `141:28788` |
| `medida-placa-marca` | `54px` | Placa del logo en la cabecera de escritorio | `161:611` |
| `medida-logo-min` | `32px` | Alto mínimo del logo apilado | `169:5454` |
| `medida-linea-lectura` | `72ch` | Longitud máxima de párrafo | inferido |
| `medida-control-base` | `42px` | Alto de botón y campo en escritorio | `86:161`, `112:365` |
| `medida-control-tactil` | `44px` | Alto mínimo de control en móvil | `169:4267` |
| `medida-control-grande` | `48px` | Acción principal de flujo | `141:28788` |
| `medida-icono-sm` | `16px` | Icono en línea | `112:488` |
| `medida-icono-md` | `20px` | Icono de navegación | `161:651` |
| `medida-avatar-sm` | `26px` | Avatar en cabecera | `161:640` |
| `medida-avatar-md` | `38px` | Avatar en tabla y comentario | `161:842` |
| `medida-senal` | `8px` | Punto de estado | `86:191` |
| `medida-progreso` | `8px` | Alto de barra de progreso | `161:651` |
| `medida-reproducir` | `52px` | Botón de reproducción | `145:3617` |
| `punto-quiebre-tableta` | `600px` | Inicio de tableta | inferido |
| `punto-quiebre-escritorio` | `1024px` | Inicio de escritorio | inferido |
| `punto-quiebre-amplio` | `1440px` | Lienzo de diseño de escritorio | frames `erp` |
| `borde-grosor-fino` | `1px` | Reglas, divisores, líneas técnicas | `88:380` |
| `borde-grosor-base` | `2px` | Borde de componente | `86:167` |
| `borde-grosor-grueso` | `3px` | Escuadras de registro | `117:149` |
| `borde-radio-ninguno` | `0` | Todo componente salvo etiqueta | `88:341` |
| `borde-radio-etiqueta` | `4px` | Etiqueta técnica | `86:184` |
| `sombra-plana-sm` | `2px 2px 0 0 var(--color-borde-fuerte)` | Controles en reposo | inferido (`86:63`) |
| `sombra-plana-md` | `4px 4px 0 0 var(--color-borde-fuerte)` | Paneles y tarjetas elevadas | inferido (`86:63`) |

## Movimiento y efectos

| Token | Valor | Uso | Origen |
|---|---|---|---|
| `movimiento-duracion-rapida` | `120ms` | Hover, foco, pulsación | inferido |
| `movimiento-duracion-base` | `200ms` | Apertura de paneles, cambio de paso | inferido |
| `movimiento-duracion-bucle` | `1200ms` | Señal de sincronización activa | inferido |
| `movimiento-curva-estandar` | `cubic-bezier(0.2, 0, 0, 1)` | Toda transición | inferido |
| `efecto-opacidad-capa` | `0.5` | Patrones y transparencias superpuestas | `88:423`, `88:485` |
| `efecto-patron-paso` | `8px` | Paso de rejilla y scanlines | `88:293` |
| `efecto-desenfoque-fondo` | `6px` | Desenfoque de fondo | `88:465` |
| `efecto-degradado-suave` | `linear-gradient(180deg, var(--color-marca-lavanda), var(--color-marca-lienzo))` | Fondos de contexto | `88:403` |

Los `punto-quiebre-*` no se pueden usar dentro de `@media`: `tokens.css` los deja como referencia y las consultas usan el valor literal con un comentario al token.
