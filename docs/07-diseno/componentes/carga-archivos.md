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
| Captura de pago | Imagen (JPG, PNG) o PDF; miniatura en vez de onda; sin validación técnica | [RF-05](../../03-requerimientos/RF-05.md), [RF-11](../../03-requerimientos/RF-11.md) |
| Referencias | Audio o enlace; varios archivos | Brief de proyecto |

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

Isla `frontend/src/islas/CargaArchivos.astro` que registra `<bugalu-carga-archivos>`; atributos `variante`, `accept`, `max-mb`, `endpoint`.
