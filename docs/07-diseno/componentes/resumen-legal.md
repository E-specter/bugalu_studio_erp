---
id: comp-resumen-legal
titulo: Componente — Resumen legal
estado: borrador
depende_de: [diseno-tokens, comp-casilla, comp-panel, RF-17]
---

# Resumen legal

Bloque que va **antes de cada aceptación** de un texto legal: título del texto, su resumen para pantalla, el enlace al texto completo con su versión y, según el paso, una o varias [casillas](casilla.md). **Decisión del brief** (TAREA-RF20-1): Figma no lo dibuja; lo piden [RF-17](../../03-requerimientos/RF-17.md) CA-04, CA-08, CA-12 y CA-13 y los [resúmenes para pantallas](../../08-legal/resumenes-para-pantallas.md).

## Anatomía

1. Título (`<h3>` o `<legend>`): `fuente-familia-titulo`, `fuente-tamano-base`, `color-texto-principal`, mayúsculas ("CONDICIONES DE CONTRATACIÓN").
2. Resumen: prosa en `color-texto-cuerpo`, `fuente-tamano-base`, `fuente-interlineado-lectura`, ancho máximo `medida-linea-lectura`. Viene de `TextoResumen.resumen` tal cual (no se redacta en la pantalla).
3. Enlace (uno por texto; términos y política comparten bloque y casilla en el registro): "Leer el texto completo (versión 1.0.0)" con icono `external-link` y el aviso visualmente oculto "(se abre en otra pestaña)". Se abre en otra pestaña para no perder lo que la persona ya escribió (CA-13). Destino: la [página pública](../pantallas/RF-17-textos-legales.md#páginas-públicas) con `?version=`.
4. Casillas (según la variante), separadas del enlace por `espacio-4`. **Nunca vienen marcadas.**

Separación entre 1, 2 y 3: `espacio-2`. Varios resúmenes seguidos: regla `borde-grosor-fino` y `espacio-5` entre ellos.

## Variantes

| Variante | Casillas | Uso |
|---|---|---|
| Obligatoria | Una, `required`; su etiqueta es la frase de aceptación del texto legal con su versión | Registro, declaración de agrupación, reserva, asesoría |
| Opcional | Una o varias independientes, sin `required`; marcar y desmarcar cuesta lo mismo | Promociones y usos promocionales en la privacidad del [perfil](../pantallas/RF-17-perfil.md) |
| Lectura | Ninguna; el resumen va junto al botón de la acción | Registro de un pago, política de privacidad cuando se lee y no se acepta |

## Estados

Comunes de la [casilla](casilla.md#estados). Propios:

| Estado | Visual y comportamiento |
|---|---|
| Sin texto (la versión no cargó) | El bloque muestra el aviso Error del bloque con "Reintentar" y la acción que depende de él queda deshabilitada con el motivo "Necesitamos mostrarte las condiciones antes de continuar." |
| Versión desactualizada (409 `texto_desactualizado`) | El bloque se repinta con la versión de `detalles`, la casilla se **desmarca** y un [aviso](aviso.md) Información dentro del bloque dice "Las condiciones cambiaron. Lee la versión {v} y vuelve a marcar la casilla." |
| Obligatoria sin marcar al enviar | Error de grupo de la casilla: "Marca la casilla para aceptar {texto}; sin ella no podemos {acción}." |

## Tokens

`fuente-familia-titulo`, `fuente-tamano-base`, `fuente-interlineado-lectura`, `medida-linea-lectura`, `color-texto-principal`, `color-texto-cuerpo`, `borde-grosor-fino`, `espacio-2`, `espacio-4`, `espacio-5`, `medida-icono-sm`.

## Relaciones

Contiene [casillas](casilla.md); vive dentro de un [panel](panel.md) del paso o de la vista. Rechazar es tan fácil como aceptar: la acción secundaria del paso ("Anterior", "Ahora no") tiene el mismo tamaño que la principal ([barra de acciones](barra-acciones.md)).

## Accesibilidad

- Con casillas, el bloque es un `<fieldset>` cuya `<legend>` es el título; el resumen y el enlace van dentro, antes de las casillas, y la casilla lleva `aria-describedby` al resumen.
- Sin casillas, es una `<section>` con `<h3>`.
- El nombre accesible del enlace incluye el texto y la versión ("Leer los Términos de uso, versión 1.0.0, se abre en otra pestaña").
- Ninguna casilla se marca por programa, tampoco al volver a un paso.

## Código

`frontend/src/componentes/ResumenLegal.astro`, props `variante` (`obligatoria|opcional|lectura`), `titulo`, `resumen`, `enlaces` (`[{ etiqueta, href, version }]`), `casillas` (`[{ nombre, etiqueta }]`). Las islas que reciben el texto en tiempo de ejecución clonan un `<template>` con este marcado (como en la [reserva](../pantallas/RF-04-reservar.md)); el componente se usa tal cual donde el texto se conoce al construir.
