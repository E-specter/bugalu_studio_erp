# Revisión visual · RF-17 etapa A (aceptaciones, perfil reforzado, privacidad y textos legales)

> `disenador-ui` · 2026-11-17 · TAREA-RF17-8 sobre `d7a2279` · Capturas de `frontend/pruebas/capturas/` (`acceso-textos-*`, `reservar-03-*`, `reservar-04-condiciones-1440`, `reservar-04-confirmar-390`, `pago-resumen-legal-1440`, `app-textos-pendientes-1440`, `perfil-reforzado-*`, `perfil-agrupacion-1440`, `perfil-privacidad-*`, `textos-legales-*`, `textos-admin-*`, `usuarios-documento*`, `libro-reclamaciones-1440`) y código de `frontend/src/islas/{Aceptacion,Reserva,Pago,Perfil,Privacidad,TextoLegal,TextosLegales}.astro`, `componentes/{ResumenLegal,PiePublico,Aviso}.astro`, `componentes/internos/ContactoEstudio.astro` y `layouts/{LayoutApp,LayoutBase}.astro`, contra el [brief](../../07-diseno/brief.md), las specs [registro y aceptaciones](../../07-diseno/pantallas/RF-17-registro-y-aceptaciones.md), [perfil](../../07-diseno/pantallas/RF-17-perfil.md) y [textos legales](../../07-diseno/pantallas/RF-17-textos-legales.md) y las fichas [resumen legal](../../07-diseno/componentes/resumen-legal.md) y [pie público](../../07-diseno/componentes/pie-publico.md). Sin Figma ni servidores.

**Dictamen:** 2 bloqueantes y 9 no bloqueantes. CA-13 se cumple en todo lo capturado: ninguna casilla viene marcada, el resumen se ve antes de cada casilla y "Ahora no" y "Anterior" tienen el mismo tamaño y peso que la acción de aceptar. No hay literales de color, tamaño ni duración en los archivos de RF-17: los únicos valores en `em` son los `@media` de los `punto-quiebre-*`, con su comentario. Todos los pares de color están en el [contraste verificado](../../07-diseno/fundamentos/color.md#contraste-verificado) (aviso Crítico: tinta sobre naranja, 5,23). Las seis decisiones de implementación quedan **aceptadas** y ya están en las specs.

## Bloqueantes

| # | Dónde | Captura | Qué pasa | Qué cambiar |
|---|---|---|---|---|
| B1 | `islas/Privacidad.astro:81` (`TEXTO`) | `perfil-privacidad-1440`, `perfil-privacidad-390` | El título del resumen legal repite el del panel (P1 PROMOCIONES → PROMOCIONES; P2 USOS PROMOCIONALES → USOS PROMOCIONALES) y el enlace dice "Leer el texto completo (versión 2.0.0)". La persona no ve **qué texto** autoriza: en P2 no sabe que acepta parte de las Condiciones de contratación. Un consentimiento debe identificar el texto al que se refiere (CA-12, CA-13; [ficha](../../07-diseno/componentes/resumen-legal.md#anatomía), punto 1: el título es el nombre del texto) | El tercer elemento de cada entrada de `TEXTO` es el nombre del texto: `'Política de privacidad'` y `'Condiciones de contratación'`. Los paneles conservan PROMOCIONES y USOS PROMOCIONALES. Spec ya precisada |
| B2 | `islas/Privacidad.astro:247` (`historial`) | `perfil-privacidad-1440` (sin fila de reserva: el caso no está capturado) | DÓNDE siempre es texto. La spec pide que "Reserva" enlace a su detalle, y `Aceptacion.id_operacion` ya llega en `GET /aceptaciones/mias` | Si `a.contexto === 'reserva' && a.id_operacion`, la celda lleva un `<a href="/app/reservas/detalle?id={id_operacion}">Reserva</a>`; sin `id_operacion`, el texto tal cual. Añadir una fila de reserva al dato de prueba y repetir la captura `perfil-privacidad-1440` |

## No bloqueantes

| # | Dónde | Captura | Qué pasa | Qué cambiar |
|---|---|---|---|---|
| N1 | `layouts/LayoutBase.astro:25` y el foco de las islas | `perfil-agrupacion-1440` (y = 950), `textos-admin-revision-1440`, `textos-admin-publicar-errores-1440` | El enlace "Saltar al contenido" se ve encima de la navegación lateral. Como solo se muestra con `:focus`, parece que después de pulsar "Guardar cambios" o "Revisar y publicar" el foco no queda donde dice la spec (aviso, `<h2>` de R1 o resumen de errores). Las pruebas no pulsan Tab | `dev-frontend`: comprobar `document.activeElement` en esas tres pruebas. Si el foco cae en el enlace de salto, corregir el destino del foco. Si es un efecto de la captura de página completa, dejarlo anotado en la prueba |
| N2 | `islas/TextosLegales.astro:59-64` (plantilla `retirar`) | `textos-admin-retirar-1440` | La regla superior de la barra Decisión toca el párrafo, sin aire | Separar el párrafo de la barra con `espacio-4` (`margin-block-end` del `<p>` o `gap` del cuerpo del panel), como en R1 |
| N3 | `componentes/PiePublico.astro` y `layouts/LayoutPublico.astro` | `reservar-03-cuenta-1440`, `textos-legales-*-1440` (ancho 1440) | El contenido del pie empieza en x = 48 y el del `<main>` en x = 96: dos retículas en la misma página | El pie usa el mismo contenedor y margen que el `<main>` de `LayoutPublico` |
| N4 | `componentes/PiePublico.astro:79` (variante Acceso) | `acceso-textos-1440` | "Libro de Reclamaciones" pasa a otra línea y queda muy separado: `gap: espacio-4` se suma al `min-block-size` táctil de cada enlace | `column-gap: var(--espacio-4); row-gap: 0` (la altura táctil ya separa las filas) |
| N5 | `componentes/internos/ContactoEstudio.astro` | `textos-legales-sin-js-1440`, `libro-reclamaciones-1440` | Separación irregular: los `<li>` con enlace miden `medida-control-tactil` y el tercero no | `min-block-size` y `align-items: center` en el `<li>`, no en el enlace, para que las tres filas midan igual |
| N6 | `islas/TextoLegal.astro` (estados 404, error, sin JS) | `textos-legales-404-1440`, `textos-legales-error-1440`, `textos-legales-sin-js-1440` | El aviso ocupa todo el ancho; en la página normal, aviso y resumen se limitan a `medida-linea-lectura` | Limitar también los avisos de estado a `medida-linea-lectura` |
| N7 | `islas/Perfil.astro` (A4, filas de integrantes) | `perfil-agrupacion-1440` | La columna NOMBRE DEL INTEGRANTE es estrecha (unos 125 px): su etiqueta ocupa dos líneas y la ayuda de ROL queda a la derecha, fuera de su columna | NOMBRE y ROL en columnas iguales (`1fr 1fr auto`) y la ayuda de ROL debajo de la etiqueta |
| N8 | `islas/TextosLegales.astro` (P1 y resumen de errores) | `textos-admin-publicar-1440`, `textos-admin-publicar-errores-1440` | TIPO DE CAMBIO es obligatorio pero no lo indica ([formularios](../../07-diseno/patrones/formularios.md): los obligatorios se marcan con texto). El resumen de errores enlaza "Resumen", pero el campo se llama REGISTRO | `<legend>` "Tipo de cambio (obligatorio)". El enlace del resumen de errores usa la etiqueta del campo ("Resumen de registro"). Spec ya precisada |
| N9 | `islas/Perfil.astro` (A1 y A3) | `perfil-reforzado-1440` | Las marcas son incoherentes: TELÉFONO dice "(opcional)", pero TIPO DE DOCUMENTO, NÚMERO, NOMBRE ARTÍSTICO y DOMICILIO, también opcionales, no dicen nada | Como casi todo es opcional, se marca solo NOMBRE "(obligatorio)" y se quita "(opcional)" de TELÉFONO (su ayuda ya dice "Lo necesitas para reservar"). Viene de RF-01 y no bloquea |

## Decisiones de implementación aceptadas

Ya están en las specs:

1. **Privacidad en isla propia** `<bugalu-privacidad>` en `/app/perfil/privacidad`; `<bugalu-perfil>` queda con los datos ([perfil](../../07-diseno/pantallas/RF-17-perfil.md), fila Isla).
2. **Aviso de textos pendientes** en `/app/*`: no se puede cerrar, no redirige, solo con `rol = cliente` y pendientes de `registro` ([registro y aceptaciones](../../07-diseno/pantallas/RF-17-registro-y-aceptaciones.md#recorrido), punto 3).
3. **El historial enlaza la reserva** por `id_operacion` con `/app/reservas/detalle?id=` (spec del perfil, P3; falta implementarlo: B2).
4. **El lateral del paso 03 no muestra precio** (spec de registro y aceptaciones, Composición).
5. **El estado de menor no tiene barra**: la única acción es "Volver al inicio", dentro del aviso Crítico, y el resumen lateral se mantiene (spec de registro y aceptaciones, Estados).
6. **Publicar versión con resúmenes por paso**: CONTENIDO → RESUMEN POR PASO (un área por contexto) → RESUMEN DE CAMBIOS, conforme al contrato `resumenes` y `resumen_cambios` ([textos legales](../../07-diseno/pantallas/RF-17-textos-legales.md#administrador-textos)).

## Comprobado sin observaciones

- CA-13: `acceso-textos-*` (Primario y Secundario grandes, a todo el ancho y apilados), `reservar-03-*` y `reservar-04-*` ("Anterior" con la misma altura y variante de barra), `pago-resumen-legal-1440` (Lectura, sin casilla) y privacidad (marcar y desmarcar se guardan con el mismo botón). Por código, ninguna isla marca una casilla de aceptación. `Privacidad.astro:163` solo repinta lo que la persona ya eligió.
- Jerarquía: un Primario por vista en todas las capturas. En el estado `version_programada`, "Volver a textos" es el único botón.
- Tamaño táctil: los enlaces del pie, la acción del aviso y los enlaces de contacto llegan a `medida-control-tactil`.
- Copy: títulos, descripciones, casillas, errores y estados coinciden con las specs.
- Tablas en tarjetas por debajo de `punto-quiebre-tableta` (`textos-legales-directorio-390`, `textos-admin-lista-390`, `usuarios-documento-repetido-390`, `perfil-privacidad-390`).

## No revisado

No hay capturas de: la declaración de agrupación antes de aceptarla (A4 con resumen legal), `perfil-agrupacion-390`, `reservar-03-menor-390`, `app-textos-pendientes-390`, `pago-resumen-legal-390`, el 409 `texto_desactualizado` en ningún resumen, ni el éxito "Listo. Ya puedes reservar.". Conviene que `dev-frontend` las añada a la próxima ronda.
