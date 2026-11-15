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
2. Icono de tipo (`audio-waveform` para audio, `image` para captura de pago, `file` para otros), `medida-icono-sm`.
3. Nombre del archivo: `fuente-familia-tecnica`, `fuente-tamano-base` (`CYBERNETIC_MIX_V3.wav`); corte con elipsis en medio si es largo, nombre completo en `title`.
4. Metadato: formato, tamaño, duración, integridad (`fuente-tamano-micro`, `color-texto-secundario`).
5. [Etiqueta](etiqueta-tecnica.md) de formato o estado y acción (descargar, quitar).

## Variantes

| Variante | Acción | Uso |
|---|---|---|
| Adjunto | Quitar (`x`) | Referencias del brief, captura de pago antes de enviar |
| Descarga | Descargar (`download`) por formato (WAV, MP3, FLAC) | Máster definitivo ([RF-12](../../03-requerimientos/RF-12.md)) |
| Lectura | Ninguna | Historial |

## Estados

Las acciones cumplen los [estados comunes](README.md#estados-comunes). Descarga no habilitada (pago pendiente, [RF-11](../../03-requerimientos/RF-11.md)): botón deshabilitado con motivo visible ("Disponible al validar el pago de posproducción").

## Tokens

`color-fondo-superficie`, `color-texto-secundario`, `borde-grosor-base`, `espacio-4`, `medida-icono-sm`, `fuente-familia-tecnica`, `fuente-tamano-base`, `fuente-tamano-micro`.

## Relaciones

Resultado de [carga-archivos](carga-archivos.md); dentro de [tarjeta-version](tarjeta-version.md).

## Accesibilidad

- Enlace de descarga con `download` y texto completo: "Descargar CYBERNETIC_MIX_V3 en WAV (54 MB)".
- Botón quitar: `aria-label="Quitar <nombre>"`.

## Código

`frontend/src/componentes/Archivo.astro`, props `nombre`, `tipo`, `metadato`, `etiqueta`, `variante`, `href`.
