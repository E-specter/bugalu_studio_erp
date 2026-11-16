---
id: comp-archivo
titulo: Componente — Archivo
estado: borrador
depende_de: [diseno-tokens, comp-etiqueta-tecnica]
---

# Archivo

"Archivo" de los adjuntos del brief (`141:28788`: nombre + metadato + etiqueta) y "Archivo final" / "Archivo y descarga" de la versión aprobada (`145:4170`). Representa un archivo ya subido.

## Anatomía

1. Contenedor: `color-fondo-superficie`, `borde-grosor-base`, relleno `espacio-4`.
2. Icono de tipo (`audio-waveform` para audio, `image` para captura de pago, `file` para otros y PDF), `medida-icono-sm`. Una imagen adjunta antes de enviar muestra en su lugar la miniatura: cuadro de `medida-miniatura`, `object-fit: contain` sobre `color-fondo-claro`, `borde-grosor-fino`.
3. Nombre del archivo: `fuente-familia-tecnica`, `fuente-tamano-base` (`CYBERNETIC_MIX_V3.wav`); si es largo se parte en líneas (`overflow-wrap: anywhere`): se lee entero y no desborda; nunca se recorta. Decisión de la revisión visual de pagos: la elipsis en medio pedía JS y escondía justo lo que distingue dos capturas.
4. Metadato: formato, tamaño, duración, integridad (`fuente-tamano-micro`, `color-texto-secundario`).
5. [Etiqueta](etiqueta-tecnica.md) de formato o estado y acción (descargar, quitar).

## Variantes

| Variante | Acción | Uso |
|---|---|---|
| Adjunto | Quitar (`x`) | Referencias del brief, captura de pago antes de enviar |
| Descarga | Descargar (`download`) por formato (WAV, MP3, FLAC) | Máster definitivo ([RF-12](../../03-requerimientos/RF-12.md)) |
| Lectura | Ninguna, o enlace "Abrir {nombre}" (`external-link`, pestaña nueva) | Historial; comprobante PDF en la [ficha del pago](../pantallas/RF-05-pagos.md) |

## Estados

Las acciones cumplen los [estados comunes](README.md#estados-comunes). Descarga no habilitada (pago pendiente, [RF-11](../../03-requerimientos/RF-11.md)): botón deshabilitado con motivo visible ("Disponible al validar el pago de posproducción").

## Tokens

`color-fondo-superficie`, `color-fondo-claro`, `color-texto-secundario`, `borde-grosor-base`, `borde-grosor-fino`, `espacio-4`, `medida-icono-sm`, `medida-miniatura`, `fuente-familia-tecnica`, `fuente-tamano-base`, `fuente-tamano-micro`.

## Relaciones

Resultado de [carga-archivos](carga-archivos.md); dentro de [tarjeta-version](tarjeta-version.md).

## Accesibilidad

- Enlace de descarga con `download` y texto completo: "Descargar CYBERNETIC_MIX_V3 en WAV (54 MB)".
- Botón quitar: `aria-label="Quitar <nombre>"`.
- Miniatura: `alt="Vista previa de <nombre>"`. Enlace a pestaña nueva: "Abrir {nombre}" + "(pestaña nueva)" visualmente oculto ("Abrir comprobante.pdf (pestaña nueva)"); por eso `nombre` es el nombre de un archivo, en minúsculas, no una frase.

## Código

`frontend/src/componentes/Archivo.astro`, props `nombre`, `tipo`, `metadato`, `etiqueta`, `variante`, `href`.
