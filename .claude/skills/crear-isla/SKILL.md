---
name: crear-isla
description: Úsala cuando dev-frontend deba implementar una pieza interactiva de Bugalú (isla `.astro` con Web Component `<bugalu-*>`), sea un componente del catálogo interactivo o la parte viva de una pantalla que consume la API.
---

# Crear una isla

Carga antes `aplicar-brief`. Una isla es un `.astro` en `frontend/src/islas/` cuyo `<script>` registra `<bugalu-<nombre>>` con `customElements.define`. Nunca `client:*` ni frameworks UI ([frontend-islas](../../../docs/01-arquitectura/frontend-islas.md)).

**Ejemplos canónicos:**
- Interacción local: [AvisoDescartable.astro](../../../frontend/src/islas/AvisoDescartable.astro) (botón `hidden` hasta registrarse, foco tras cerrar).
- Consumo de API: [Perfil.astro](../../../frontend/src/islas/Perfil.astro) (un `<template>` por estado, `<noscript>`) con [api.js](../../../frontend/src/servicios/api.js) y sus pruebas en [perfil.spec.js](../../../frontend/pruebas/perfil.spec.js).

## Pasos

0. **Lee los dos ejemplos canónicos enteros** (isla, `api.js` y su prueba) antes de planificar.
1. **Lee** la ficha del componente o la spec de pantalla, el patrón [estados-sistema](../../../docs/07-diseno/patrones/estados-sistema.md) y, si llama a la API, la sección `## Contrato API` del RF. Sin contrato escrito, detente y avisa a `leader`. Si la ficha y el RF no coinciden (p. ej. mes frente a semana), no elijas tú: pide a `leader` que `disenador-ui` lo cierre.
2. **Sin JavaScript primero:** el frontend es estático (sin servidor), así que los datos de la API solo llegan con JS. El HTML servido explica qué pasa sin JS (`<noscript>` con el estado de error del patrón) y nada queda en "Cargando…" con `aria-busy` para siempre. Los controles que solo sirven con JS nacen `hidden` y la isla los muestra al registrarse. Lo estático (textos, opciones fijas) sí se renderiza en el HTML.
3. **Prueba primero** (Playwright):
   - con `javaScriptEnabled: false` y con JS;
   - teclado: orden de foco, `Escape`/`Enter` si aplica, adónde va el foco al terminar;
   - si llama a la API, `page.route` simula **200, 401, 403/404, 503, red caída y respuesta no JSON**: cada una muestra su estado, nunca pantalla en blanco ni error de consola sin controlar;
   - axe WCAG 2.2 AA en cada estado.
   Mírala fallar.
4. **Implementa:** estados como `<template>` renderizados con componentes del catálogo; la isla clona el que toca. Cada endpoint tiene su función en `servicios/api.js` (como `obtenerPerfil()`), construida sobre `pedir()`: la isla llama a la función, nunca a una URL suelta ni a `fetch`. Un 401 muestra el estado "sesión no válida" con enlace al acceso, como `Perfil`. Nunca el token en URL ni en `console`.
5. **Estilos:** solo tokens de rol, como en `crear-componente`.
6. **Verifica:** `npm run check`, `npm run build`, `npm run test:e2e`; captura de cada estado.

## Errores que ya ocurrieron

| Error | Cómo evitarlo |
|---|---|
| Botón que sin JS se ve y no hace nada | Paso 2: `hidden` hasta registrarse |
| Perfil sin JS en "Cargando…" indefinido | Paso 2: `<noscript>` con el estado de error |
| `aria-pressed` y además nombre que cambia | Un solo mecanismo: nombre fijo + `aria-pressed` |
| Foco perdido al cerrar | Prueba de teclado del paso 3 |
