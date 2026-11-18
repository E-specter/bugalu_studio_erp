---
id: comp-tarjeta-profesional
titulo: Componente — Tarjeta de profesional
estado: borrador
depende_de: [diseno-tokens, comp-avatar, comp-etiqueta-tecnica, comp-tarjeta-proyecto, RF-15]
---

# Tarjeta de profesional

Un profesional artístico en el [directorio público](../pantallas/RF-15-directorio.md): quién es, qué hace y cuánto cuesta una asesoría con él. **Decisión del brief** (TAREA-RF15-1): Figma no tiene directorio ([brecha](../figma.md#brecha-detectada)); se extiende la [tarjeta de proyecto](tarjeta-proyecto.md) (contenedor, enlace extendido, hover) con la identidad del [avatar](avatar.md). No basta la de proyecto: no tiene foto, especialidades ni precios.

## Anatomía

1. Contenedor `<article>`: `color-fondo-superficie`, `borde-grosor-base` `color-borde-fuerte`, sin sombra, relleno `espacio-5`. Dentro, de arriba abajo con hueco `espacio-4`:
2. Identidad, en fila: [avatar](avatar.md) Miniatura (foto o iniciales) + bloque de nombre con hueco `espacio-4`:
   - Nombre que se muestra (`nombre_artistico` o, si no hay, `nombre`) como `<h2>` (o el nivel que toque en la página): `fuente-familia-titulo`, `fuente-tamano-titulo-sm`, `color-texto-principal`, tal cual (sin pasar a mayúsculas: es contenido del usuario). Es el enlace al perfil.
   - Con nombre artístico, debajo, el nombre completo: `fuente-tamano-base`, `color-texto-secundario`.
3. Especialidades: lista de [etiquetas](etiqueta-tecnica.md) Neutra en fila que se ajusta, hueco `espacio-2`, en el orden de la API.
4. Precios: `<dl>` en `fuente-familia-tecnica`; por duración ofrecida, `<dt>` "30 MIN" (`fuente-tamano-micro`, `color-texto-secundario`) y `<dd>` importe (`fuente-tamano-base`, `color-texto-principal`, `tabular-nums`). Dos columnas si hay dos duraciones.
5. Pie: "Ver perfil" con icono `arrow-right` (`fuente-tamano-pequeno`), alineado a la izquierda. Es texto, no un segundo enlace (ver Accesibilidad).

Retícula: una columna; ≥ `punto-quiebre-tableta`, dos; ≥ `punto-quiebre-escritorio`, tres; hueco `espacio-6`. Las tarjetas de una fila igualan su alto.

## Variantes

Una. Sin precio no hay tarjeta: un perfil sin duraciones no es público ([RF-15](../../03-requerimientos/RF-15.md) CA-03).

## Estados

Toda la tarjeta enlaza al perfil: [estados comunes](README.md#estados-comunes). Hover (con puntero): fondo `color-fondo-claro`. Foco: el anillo del enlace se dibuja alrededor de **toda la tarjeta** (`:focus-within` en el `<article>`, con el `outline` de los estados comunes), no solo del nombre, porque toda la tarjeta es el objetivo. Carga y error los resuelve la pantalla, no la tarjeta.

## Tokens

`color-fondo-superficie`, `color-fondo-claro`, `color-borde-fuerte`, `color-texto-principal`, `color-texto-secundario`, `borde-grosor-base`, `espacio-2`, `espacio-4`, `espacio-5`, `espacio-6`, `fuente-familia-titulo`, `fuente-familia-tecnica`, `fuente-tamano-titulo-sm`, `fuente-tamano-base`, `fuente-tamano-pequeno`, `fuente-tamano-micro`, `medida-miniatura`, `medida-icono-sm`, `punto-quiebre-tableta`, `punto-quiebre-escritorio`.

## Relaciones

Usa [avatar](avatar.md) y [etiqueta técnica](etiqueta-tecnica.md). Va en la lista del [directorio](../pantallas/RF-15-directorio.md) (Landing). Patrón de enlace extendido de la [tarjeta de proyecto](tarjeta-proyecto.md).

## Accesibilidad

- `<article>` con el nombre como `<a>` que se extiende a toda la tarjeta con un pseudoelemento (como la tarjeta de proyecto): el lector lee un solo enlace con el nombre, no la tarjeta entera. Nombre accesible del enlace: "{nombre que se muestra}, ver perfil". El "Ver perfil" visible del pie es `aria-hidden="true"` para no repetirlo.
- El avatar lleva `alt=""` (el nombre está al lado). Las etiquetas de especialidad van en una `<ul>` con `aria-label="Especialidades"`.
- Los importes se leen con su duración ("30 MIN, S/ 80,00") gracias a `<dt>`/`<dd>`.
- Objetivo táctil: toda la tarjeta; muy por encima de 24 × 24 px.

## Código

`frontend/src/componentes/TarjetaProfesional.astro`, props `nombre`, `nombre_artistico`, `foto`, `especialidades` (`[{id, nombre}]`), `duraciones` (`[{minutos, precio}]`), `href`, `nivel` (del encabezado, por defecto 2). Como los datos llegan en el navegador (salida estática), la página la usa dentro de un `<template>` que `<bugalu-directorio>` clona y llena, igual que las plantillas del historial ([piezas internas](README.md#piezas-internas)).
