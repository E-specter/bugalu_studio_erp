---
id: comp-carga-archivos
titulo: Componente — Carga de archivos (isla)
estado: borrador
depende_de: [diseno-tokens, comp-barra-progreso, arq-frontend-islas]
---

# Carga de archivos

"Proceso de carga" de la carga y validación de WAV (`161:1750`): archivo en carga (cabecera, forma de onda, progreso), validación técnica (lista de pruebas), historial técnico y "Cadena de señal". Sube uno o varios archivos con progreso y validación.

## Anatomía

1. Zona de soltar: [panel](panel.md) con `borde-grosor-base` discontinuo, icono `upload`, texto "Arrastra el archivo o selecciónalo" y botón secundario "Seleccionar archivo". Formatos y tamaño máximo visibles.
2. Archivo en carga: nombre (`fuente-familia-tecnica`), forma de onda (audio) o miniatura (imagen), [barra de progreso](barra-progreso.md) Carga.
3. Validación técnica (audio): lista de pruebas con [indicador](indicador-estado.md) por prueba (formato, frecuencia de muestreo, profundidad de bits, picos, integridad).
4. Resultado: [archivo](archivo.md) Adjunto.

## Variantes

| Variante | Acepta | Uso |
|---|---|---|
| Entregable de audio | WAV; validación técnica completa; historial en [lista de eventos](lista-eventos.md) Terminal | [RF-09](../../03-requerimientos/RF-09.md) |
| Captura de pago | Imagen (JPG, PNG) o PDF, un archivo de hasta 5 MB; miniatura en vez de onda; sin validación técnica. Ver abajo | [RF-05](../../03-requerimientos/RF-05.md), [RF-11](../../03-requerimientos/RF-11.md) |
| Referencias | Audio o enlace; varios archivos | Brief de proyecto |
| Adjuntos de reclamo | PDF, JPG o PNG; de 0 a 3 archivos de hasta 5 MB cada uno; como Captura de pago, pero varios. Ver abajo | [RF-16](../../03-requerimientos/RF-16.md) |

### Captura de pago

Primera variante que se implementa ([registrar pago](../pantallas/RF-05-registrar-pago.md)); las demás entran con su RF. Decisión del brief para no construir lo que no usa:

- **El archivo viaja con el formulario**, no por su cuenta: la isla envuelve un `<input type="file" name="captura" accept="image/jpeg,image/png,application/pdf">` real dentro del `<form>` de la pantalla, que lo envía en su `multipart/form-data`. Sin atributo `endpoint` ni subida previa.
- **Sin zona de soltar ni barra de progreso:** un solo archivo pequeño que en móvil se elige de la galería. La subida es el envío del formulario: su estado es el Carga del Primario (y el texto de más de 10 s de [estados del sistema](../patrones/estados-sistema.md#carga)).
- Anatomía: etiqueta y ayuda del [campo](campo.md) → control "Seleccionar archivo" (`upload`) con el aspecto del [botón](boton.md) Secundario → al elegir, [archivo](archivo.md) Adjunto (miniatura si es imagen, `file` si es PDF; metadato "PNG · 1,2 MB") con "Quitar"; quitar devuelve el foco a "Seleccionar archivo".
- **Control visible = `<label for>` del input real.** El `<input type="file">` queda visualmente oculto (no `display: none`: sigue en el formulario y recibe el foco); el `<label>` con aspecto de Secundario abre el selector con clic y su anillo de foco se pinta cuando el input tiene `:focus-visible` (selector hermano). Con adjunto, el input sale del orden de teclado y la parada es "Quitar". Error: borde `color-texto-alerta` en el label. Mientras se envía el formulario, "Quitar" está deshabilitado como el resto de controles.
- Validación en el navegador como primera capa (la del servidor, por la firma, manda): tamaño > 5 MB y tipo fuera de `accept` → error del campo con [estados comunes](README.md#estados-comunes) Error y el texto de la pantalla.

### Adjuntos de reclamo

Decisión del brief (TAREA-RF16-1): la Captura de pago con tres cambios, sin zona de soltar ni progreso.

- **Varios archivos:** `<input type="file" multiple accept="application/pdf,image/jpeg,image/png">`. Cada elección **se suma** a la lista (no la reemplaza) hasta 3; la isla guarda los `File` en memoria y la pantalla los manda como `adjuntos[]` en su `FormData` (el formulario ya se envía por JS, [formulario de RF-16](../pantallas/RF-16-formulario.md)). Con 3, el control se oculta y la ayuda dice "Máximo 3 archivos."
- **Lista:** un [archivo](archivo.md) Adjunto por archivo, en el orden elegido, cada uno con su "Quitar"; quitar lleva el foco al siguiente "Quitar" o, si no queda ninguno, al control.
- **Error por archivo:** tipo fuera de `accept` o más de 5 MB no entra en la lista; el error del campo nombra el archivo y la regla. Si el servidor rechaza uno ya en la lista (413, 422 `adjunto_no_permitido`), ese [archivo](archivo.md) toma el estado Error (borde `color-texto-alerta` y mensaje debajo) hasta que se quite.

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios:

| Estado | Visual |
|---|---|
| Arrastrando encima | Zona con fondo `color-fondo-destacado` y borde continuo |
| Subiendo | Barra con porcentaje y tamaño; botón "Cancelar" |
| Validando | Barra indeterminada; pruebas "EN CURSO" |
| Válido | Cada prueba con [indicador](indicador-estado.md) Correcto y texto ("FORMATO WAV · OK"); archivo listo |
| Rechazado | Borde `color-texto-alerta`; prueba fallida con indicador Problema y texto "FALLA"; mensaje con la causa y la regla ("Formato MP3 no admitido: sube el WAV de la sesión"); los límites técnicos los fija el RF |
| Error de red | [Aviso](aviso.md) Error con "Reintentar"; lo ya subido se conserva |

## Tokens

`borde-grosor-base`, `color-fondo-destacado`, `color-texto-exito`, `color-texto-alerta`, `fuente-familia-tecnica`.

## Relaciones

Usa [barra-progreso](barra-progreso.md), [indicador-estado](indicador-estado.md), [archivo](archivo.md). Ver [audio y versiones](../patrones/audio-y-versiones.md).

## Accesibilidad

- **Sin JS:** `<input type="file" accept>` dentro de un `<form>` con `enctype="multipart/form-data"`; la isla añade arrastrar y progreso.
- La zona de soltar no es la única vía: el botón "Seleccionar archivo" es un control real con foco.
- Progreso y resultado de validación en `role="status"`; rechazo en `role="alert"`.

## Código

Isla `frontend/src/islas/CargaArchivos.astro` que registra `<bugalu-carga-archivos>`; atributos `variante` (`captura|reclamo|audio|referencias`), `accept`, `max-mb`, `nombre` (el `name` del input), `endpoint` (solo audio y referencias).
