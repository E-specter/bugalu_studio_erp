---
id: comp-campo
titulo: Componente — Campo
estado: borrador
depende_de: [diseno-tokens, fund-tipografia]
---

# Campo

Capa "Campo" del brief de proyecto (`141:28788`: "Etiqueta y ayuda" + "Entrada"), campos de acceso (`112:363`, `112:367`) y "Búsqueda" del directorio de clientes (`161:842`). Entrada de un dato con su etiqueta.

## Anatomía

1. Etiqueta: `fuente-familia-tecnica`, `fuente-peso-medio`, `fuente-tamano-micro`, mayúsculas. Indicador de obligatorio: texto "(obligatorio)", no solo asterisco. En la estructura Acceso lleva el prefijo `//` (`// CORREO REGISTRADO`) como adorno: `content: "// " / ""` en `::before`, para que no se lea; lo aplica el layout de acceso, no el componente.
2. Ayuda opcional a la derecha de la etiqueta o debajo: `fuente-tamano-pequeno`, `color-texto-secundario`.
3. Entrada: `color-fondo-claro`, `borde-grosor-base` `color-borde-fuerte`, `borde-radio-ninguno`, `sombra-plana` (`112:365`), alto `medida-control-base`, relleno `espacio-4`, valor en `fuente-familia-texto` `fuente-tamano-base`.
4. Mensaje de error bajo la entrada.

Separación etiqueta → entrada: `espacio-2`. Campos en fila: hueco `espacio-3`.

## Variantes

| Variante | Elemento | Notas |
|---|---|---|
| Texto | `<input type="text|email|tel|url|number|date|time">` | La base. Hora: `time` con `step="1800"` (medias horas, hora de Lima). Importe: `text` con `inputmode="decimal"`, prefijo "S/" en la etiqueta y dos decimales (la isla acepta coma o punto) |
| Área | `<textarea>` | Alto mínimo 2 × `medida-control-base`. Si hay límite: `maxlength` + la ayuda lo dice ("Máximo 500 caracteres"). El contador en vivo (`145:3617` "Contador") necesita JS: se hace isla con la primera pantalla que lo pida |
| Contraseña | `<input type="password">` + botón `eye` | El botón de mostrar es la isla `<bugalu-contrasena>`; sin JS el campo funciona igual. En una contraseña nueva suma el [medidor](#medidor-de-robustez) |
| Búsqueda | `<input type="search">` con icono `search` a la izquierda | Sin atajo de teclado: el "Atajo" de `161:842` no se adopta (un atajo de una tecla choca con WCAG 2.1.4 y pide JS) |
| Selector | `<select>` nativo con la misma caja | Para listas cerradas (servicio, profesional) |
| Archivo | — | Usar [carga-archivos](carga-archivos.md) |

## Medidor de robustez

Solo en contraseñas **nuevas** (`autocomplete="new-password"`: registro, solicitud de acceso, nueva contraseña); nunca al iniciar sesión. Cumple el CA-02 de [RF-01](../../03-requerimientos/RF-01.md). Decisión del brief: Figma solo rotula "(MIN 8 CARACT.)" (`112:270`).

Anatomía, entre la entrada y el mensaje de error, a `espacio-2` de la entrada:

1. Nivel: [indicador de estado](indicador-estado.md) En línea, "ROBUSTEZ: MEDIA".
2. Lista `<ul>` de las cinco condiciones, una por línea con hueco `espacio-1`: icono `medida-icono-sm` + texto `fuente-tamano-pequeno` en `color-texto-cuerpo`, separados `espacio-2`; el icono, centrado en la altura de la primera línea del texto (no más bajo).

| Condición | Texto | Qué cuenta (igual que Supabase Auth) |
|---|---|---|
| Longitud | Al menos 8 caracteres | 8 o más caracteres |
| Minúscula | Una minúscula (a-z) | `a-z`; la ñ y las vocales con tilde no cuentan |
| Mayúscula | Una mayúscula (A-Z) | `A-Z`; ídem |
| Número | Un número (0-9) | `0-9` |
| Símbolo | Un símbolo, como ! ? # $ % | ``!@#$%^&*()_+-=[]{};'\:"\|<>?,./`~`` |

| Condición | Icono | Color del icono | Texto oculto tras el texto |
|---|---|---|---|
| Pendiente | `circle` | `color-texto-secundario` | ": pendiente" |
| Cumplida | `check-circle` | `color-texto-exito` | ": cumplida" |

| Nivel | Cuándo | Tono del indicador |
|---|---|---|
| Sin evaluar | Campo vacío | Neutro, "ROBUSTEZ: SIN EVALUAR" |
| Débil | Falta alguna condición: Supabase Auth la rechazaría | Problema |
| Media | Las cinco, con 8 a 11 caracteres | Pendiente |
| Fuerte | Las cinco, con 12 o más | Correcto |

Comportamiento: la isla `<bugalu-contrasena medidor>` evalúa en el navegador en cada entrada, sin enviar nada. Al enviar con nivel Débil, error del campo que nombra lo que falta ("Falta una mayúscula y un símbolo.") y no se llama al servicio. Sin JS: la lista se ve como requisitos (sin iconos de estado ni nivel) y quedan `required` y `minlength="8"` nativos.

Accesibilidad del medidor:

- La entrada lleva `aria-describedby` a la ayuda ("Mínimo 8 caracteres con minúscula, mayúscula, número y símbolo.") y al error; la lista no, para no leer cinco líneas en cada foco. Se recorre con el cursor de lectura.
- Cada condición dice su estado en texto ("Un número: cumplida"); el icono es `aria-hidden`. Color, icono y texto, nunca solo color.
- Anuncio: una región `role="status"` oculta y propia del campo, presente desde la carga, dice **solo el nivel** ("Robustez media") cuando cambia, tras 1 s sin escribir o al salir del campo. Nunca en cada pulsación ni la lista entera; el indicador visible no lleva rol.

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

`color-fondo-claro`, `color-fondo-lienzo`, `sombra-plana`, `color-borde-fuerte`, `color-texto-principal`, `color-texto-secundario`, `color-texto-alerta`, `borde-grosor-base`, `borde-grosor-fino`, `borde-radio-ninguno`, `medida-control-base`, `medida-icono-sm`, `espacio-1`, `espacio-2`, `espacio-3`, `espacio-4`, `fuente-*`. Medidor: `color-texto-cuerpo`, `color-texto-exito` y los del [indicador de estado](indicador-estado.md).

## Relaciones

Compone los [formularios](../patrones/formularios.md). Para opciones múltiples: [casilla](casilla.md) o [tarjeta-opcion](tarjeta-opcion.md).

## Accesibilidad

- `<label for>` siempre visible; el marcador de posición nunca sustituye a la etiqueta.
- Ayuda y error unidos con `aria-describedby`; error con `aria-invalid="true"`.
- `autocomplete` correcto en datos personales (`email`, `name`, `tel`, `current-password`, `new-password`) (WCAG 1.3.5).
- Botón de mostrar contraseña: botón de alternancia con nombre **fijo** `aria-label="Mostrar contraseña"` y `aria-pressed="true|false"`; cambia el icono (`eye` / `eye-off`), nunca el nombre. Mide `medida-control-tactil` de ancho y el alto de la entrada.

## Código

`frontend/src/componentes/Campo.astro`, props `tipo` (`text|email|tel|url|number|date|time|password|search|area|selector`), `nombre`, `etiqueta`, `ayuda`, `error`, `obligatorio`, `soloLectura`, `valor`, `id`; el resto de atributos va al control (`autocomplete`, `placeholder`…). `selector` recibe los `<option>` en la ranura; `medidor` (solo con `password`) añade el [medidor de robustez](#medidor-de-robustez). Isla `frontend/src/islas/Contrasena.astro` registra `<bugalu-contrasena>` (atributo `medidor`).
