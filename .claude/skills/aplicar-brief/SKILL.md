---
name: aplicar-brief
description: Reglas del brief de diseño de Bugalú Studio. Úsala siempre que escribas, revises o especifiques interfaz (Astro, CSS, islas, specs de pantalla).
---

# Aplicar el brief

Manda el [brief](../../../docs/07-diseno/brief.md). Si no cubre un caso, amplía primero el brief.

## Tokens
- Ningún valor visual a mano: color, tamaño, espacio, borde, radio, sombra y duración salen de [tokens](../../../docs/07-diseno/tokens.md) como `var(--token)`.
- Usa tokens de rol, nunca `color-marca-*`.
- Si falta un token, agrégalo primero a tokens con su origen.

## Componentes
- Compón solo con el [catálogo](../../../docs/07-diseno/componentes/README.md) y los [patrones](../../../docs/07-diseno/patrones/README.md). Si falta uno, primero escribe su ficha.
- Respeta la ficha. Un botón primario por vista.
- HTML nativo antes que isla.

## Contraste y foco (WCAG 2.2 AA)
- Solo pares de [contraste verificado](../../../docs/07-diseno/fundamentos/color.md#contraste-verificado) y las [reglas de color](../../../docs/07-diseno/fundamentos/color.md#reglas): prosa en `color-texto-cuerpo`, títulos y datos en `color-texto-principal`; naranja solo en hover y alerta crítica.
- El estado nunca se comunica solo con color.
- Foco visible según los [estados comunes](../../../docs/07-diseno/componentes/README.md#estados-comunes); nunca lo quites sin sustituto.
- Teclado completo, textos alternativos, ARIA solo si el nativo no basta; tamaño de objetivo de WCAG 2.5.8.

## Movimiento
- Solo lo del catálogo de [movimiento](../../../docs/07-diseno/fundamentos/movimiento.md). Con `prefers-reduced-motion: reduce` no hay desplazamientos ni bucles.

## Puntos de quiebre
- Primero móvil; `min-width` con los `punto-quiebre-*` de [espaciado y retícula](../../../docs/07-diseno/fundamentos/espaciado-reticula.md#adaptabilidad). Táctil: `medida-control-tactil`; zoom al 200 % sin pérdida.

## Fundamentos
- Sigue [tipografía](../../../docs/07-diseno/fundamentos/tipografia.md), [forma y elevación](../../../docs/07-diseno/fundamentos/forma-elevacion.md), [iconografía e imagen](../../../docs/07-diseno/fundamentos/iconografia-imagen.md) y [logotipo](../../../docs/07-diseno/fundamentos/logotipo.md).

## Voz y copy
- Español, segunda persona, frases cortas ([voz](../../../docs/07-diseno/brief.md#decisiones-artísticas)). Títulos y etiquetas en mayúsculas técnicas; el contenido del usuario, tal cual.
- El botón dice qué pasa ("Publicar versión"). El error dice qué pasó y cómo corregirlo.
- Traduce anglicismos; conserva los términos del audio.
- Fechas, importes y códigos según [formato de datos](../../../docs/07-diseno/patrones/estructura-app.md#formato-de-datos).

## Estados obligatorios
- Todo bloque con datos del servidor define vacío, carga, error y éxito según [estados del sistema](../../../docs/07-diseno/patrones/estados-sistema.md).
- Validación según [formularios](../../../docs/07-diseno/patrones/formularios.md).
