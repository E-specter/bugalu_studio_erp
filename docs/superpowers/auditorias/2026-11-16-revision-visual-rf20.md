# Revisión visual · RF-20 (cambios sensibles, impuestos, registro de cambios, parámetros P3 y desglose de IGV)

> `disenador-ui` · 2026-11-16 · TAREA-RF20-6 sobre `aac3a24` · Capturas de `frontend/pruebas/capturas/` (`cambio-sensible-*`, `impuestos-*`, `registro-cambios-*`, `parametros-p3-*`, `parametros-revision-*`, `desglose-*` y, por contexto, `tarifas-servicio-1440`) y código de `frontend/src/islas/{CambioSensible,RegistroCambios,Tarifas,Franjas}.astro`, `componentes/Tabla.astro`, `servicios/campos-cambio.js` y `servicios/formatos.js` (`filasPrecio`, `partidasPrecio`), contra el [brief](../../07-diseno/brief.md) y las specs [cambios sensibles](../../07-diseno/pantallas/RF-20-cambios-sensibles.md) y [registro de cambios](../../07-diseno/pantallas/RF-20-registro-cambios.md). Sin Figma ni capturas nuevas.

**Dictamen:** 1 bloqueante y 4 no bloqueantes. Las cinco decisiones de implementación y los dos cambios de especificidad de `Tabla` quedan **aceptados**. El bloqueante viene de un error de mi propia spec ("Más IGV" bajo el total), que ya está corregido. Lo aceptado ya está en las specs y fichas.

## Bloqueantes

| # | Dónde | Qué pasa | Qué cambiar | Referencia |
|---|---|---|---|---|
| B1 | `servicios/formatos.js:94-99`, `filasPrecio` (resumen persistente del paso 02 y Listo 05, `islas/Reserva.astro:406` y `:773`) | Con precios sin IGV, el resumen muestra TOTAL S/ 150,00 → MÁS IGV (18 %) S/ 22,88 → ANTICIPO (`desglose-reservar-02-neto-390`). Leído de arriba abajo, parece que hay que pagar S/ 150,00 **más** S/ 22,88, aunque el total ya incluye el IGV (CA-02: `total = base + igv`). Es información de dinero engañosa para el cliente. Lo pedía mi spec, que ya está corregida | Mismo orden que la tabla Partidas: el IGV va entre el subtotal y el total cuando no está incluido. Ver el código bajo la tabla. y actualizar el comentario de la línea 94. Así se cumple CA-09 ("más IGV" sin incluir) sin falsear el total. `pruebas/formatos.spec.js:61` sigue pasando (el índice 1 sigue siendo "Más IGV"). `dev-frontend` debe comprobar `desglose-igv.spec.js` si mira el orden | [Cambios sensibles, desglose](../../07-diseno/pantallas/RF-20-cambios-sensibles.md#desglose-de-igv) (corregida), RF-20 CA-02 y CA-09 |

Código de B1 (`servicios/formatos.js`):

```js
export const filasPrecio = (precio, adelanto = precio.porcentaje_adelanto) => {
  const i = precio.impuesto;
  const igv = i && [`${i.incluido ? 'Incluye' : 'Más'} IGV (${porcentaje(i.porcentaje)})`, soles(i.monto)];
  return [
    ...(i && !i.incluido ? [['Subtotal', soles(i.base)], igv] : []),
    ['Total', soles(precio.total)],
    ...(i?.incluido ? [igv] : []),
    [etiquetaAnticipo(adelanto), soles(precio.anticipo)],
  ];
};
```

## No bloqueantes

| # | Dónde | Qué cambiar y por qué | Referencia |
|---|---|---|---|
| N1 | `islas/CambioSensible.astro:20` y su `<style>` | En C2, el aviso "Se aplica solo a reservas nuevas…" va pegado a la tabla, y su borde se junta con el borde inferior grueso de la tabla (`cambio-sensible-revision-1440`, `parametros-revision-1440`). Además, `texto=" "` deja un `<p class="aviso-texto">` vacío que la isla nunca rellena. Cambio: `<Aviso variante="informacion" titulo=" " />` y `.cs :global(.tabla + .aviso) { margin-block-start: var(--espacio-4); }` | [Cambios sensibles, composición](../../07-diseno/pantallas/RF-20-cambios-sensibles.md#composición-de-la-revisión) (ampliada), [espaciado](../../07-diseno/fundamentos/espaciado-reticula.md) |
| N2 | `islas/RegistroCambios.astro`, `pintar()` | El total ("12 cambios") solo se anuncia en la región viva y no se ve en pantalla. El patrón de tablas pide el total en el panel (`registro-cambios-1440`). En `pintar()`, poner en `[data-resultados] .panel-ayuda` el texto ``${plural(lista.length, 'cambio', 'cambios')} ${periodo}. Nadie puede editar ni borrar este registro.`` y, si la lista está vacía, solo "Nadie puede editar ni borrar este registro." | [Tablas y tableros](../../07-diseno/patrones/tablas-y-tableros.md) paso 4, [registro de cambios, composición](../../07-diseno/pantallas/RF-20-registro-cambios.md#composición) (ampliada) |
| N3 | `islas/Pagos.astro:348`, V2 PAGO | En la misma línea del dato van "S/ 6,82 · base S/ 68,18" y la nota "Informativo: el comprobante se emite fuera de la app.", con el mismo tamaño (`desglose-revisar-10-1440`). Se lee como parte del importe. Cambio, como ya se hace con la ayuda del monto (línea 339): ``dd.textContent = `${soles(p.impuesto.monto)} · base ${soles(p.impuesto.base)}`;`` y después añadir a la `<dd>` un elemento `gestion-ayuda` con la nota | [Cambios sensibles, desglose](../../07-diseno/pantallas/RF-20-cambios-sensibles.md#desglose-de-igv) (ampliada) |
| N4 | `pages/app/franjas/parametros.astro:13` | La descripción no menciona P3, que ahora es el panel más largo de la vista. Texto nuevo: "Cuánto tiempo tiene el cliente para pagar, con cuánta anticipación puede reservar y qué pasa si cancela o reprograma." | [Franjas, copy](../../07-diseno/pantallas/RF-03-franjas.md#copy) (cambiada) |

Sin hallazgos en:
- **Jerarquía:** la revisión se lee en una columna de arriba abajo (C1 → C2 → C3). Los paneles de la vista se ocultan y el encabezado (EDITAR SERVICIO, PARÁMETROS DE RESERVA) se conserva como contexto. En DESPUÉS, la negrita y la propia columna marcan la diferencia, no solo el color. En Impuestos, I2 va en el lateral y en 390 baja después de I1.
- **Tokens:** `CambioSensible`, `RegistroCambios` y la regla nueva de `Tabla` solo usan `var(--…)`. No hay valores escritos a mano.
- **Contraste:** solo se usan pares verificados. "Aplicar cambio" con `aria-disabled` usa el estilo de Inactivo del botón: está exento de 1.4.3 y explica su bloqueo con `aria-describedby` hacia la ayuda del campo.
- **Objetivos táctiles:** "Cancelar" y "Aplicar cambio" son Grande y tienen el mismo peso en la barra Formulario (CA-09). En 390 la barra pasa a Móvil con la acción principal arriba. Filtros, selector y "Filtrar" miden `medida-control-tactil`.
- **Estados no solo por color:** los errores llevan icono y texto con resumen enlazado (`parametros-p3-errores-1440`, `registro-cambios-error-rango-1440`). El recurso del registro lleva etiqueta con texto y el IGV va en una fila con su nombre.
- **Consistencia con tarifas y pagos:** hay ayudas bajo "Guardar servicio / especialista / recargos" y "Guardar parámetros", "Impuestos" (Secundario) junto a "Recargos y feriados", "Ver en el registro de cambios" en el éxito, y el desglose de la tabla Partidas es igual en reservar, mis reservas y el detalle (`desglose-detalle-*`).
- **C2 a 390:** el concepto ocupa hasta 5 líneas ("Vence el pago de una reserva a 36 h") porque las cifras no se parten. Se acepta: se lee bien y es lo que la ficha prevé para Partidas.

Ajenos al diseño:
- Las fechas de DESDE / HASTA salen como `10/17/2026` porque Playwright usa el idioma `en-US` y el control `date` es nativo del navegador. Con `es-PE` se ve `17/10/2026`.
- En `parametros-revision-1440`, "Cancelar" sale en naranja porque el puntero de la prueba está encima (hover, como manda el brief). "Saltar al contenido" aparece porque tiene el foco.
- Los datos de prueba no son coherentes en los ejemplos: Grabación S/ 240,00 con subtotal S/ 127,12, el ejemplo "Ajuste uno / otro", "30 días → 1 día" y el comprobante de un punto. No representan casos reales.

## Decisiones de implementación

| # | Decisión | Dictamen | Dónde queda |
|---|---|---|---|
| 1 | C1 con `Tabla` Partidas en vez de Compacta | **Aceptada.** Compacta pasa a tarjetas por debajo de escritorio y ahí se perdería la cabecera ANTES / DESPUÉS, que es justo la comparación. Con tres columnas, Partidas cabe a 320 px (`cambio-sensible-revision-390`). El `<tfoot>` vacío no pinta nada | [Cambios sensibles, composición](../../07-diseno/pantallas/RF-20-cambios-sensibles.md#composición-de-la-revisión), [tabla, código](../../07-diseno/componentes/tabla.md#código) |
| 2 | "Incluye IGV (p %)" en registrar pago también con precios sin IGV | **Aceptada.** La cuota sale del total, y el total siempre suma el IGV (CA-02), así que la cuota lo incluye en los dos casos. "Más IGV" ahí sería falso. Este mismo razonamiento lleva a B1 | [Cambios sensibles, desglose](../../07-diseno/pantallas/RF-20-cambios-sensibles.md#desglose-de-igv) |
| 3 | Ayudas de P3 escritas por el implementador, el orden (adelanto primero) y los campos de ADR-015 | **Aceptadas.** Las ayudas son cortas, dicen el efecto y siguen la forma de P1 y P2. La de LÍMITE DEL NIVEL 2 adelanta la regla de validación. Con ADELANTO primero, la vista queda pago → anticipación → cancelación. Los parámetros de ADR-015 ya tienen nombre en el contrato y en `campos-cambio.js`, así que se cierra ese pendiente. Condición: N4 | [Franjas, copy](../../07-diseno/pantallas/RF-03-franjas.md#copy), [cambios sensibles, integración](../../07-diseno/pantallas/RF-20-cambios-sensibles.md#integración-sin-rehacer-las-pantallas) |
| 4 | Fecha relativa en el registro (< 7 días) con la absoluta en `title` | **Aceptada** (ya estaba en la spec). Va en un `<time datetime>` y el texto relativo basta solo. El `title` es un extra para el ratón y no esconde información imprescindible | [Registro de cambios, datos](../../07-diseno/pantallas/RF-20-registro-cambios.md#datos) |
| 5 | Fila del IGV en peso regular | **Aceptada** (ya estaba en la spec). `.tabla-partidas tfoot .tabla-igv > *` gana a la regla del pie por especificidad (`desglose-detalle-neto-390`: Subtotal y Total en negrita, IGV en regular) | [Tabla, código](../../07-diseno/componentes/tabla.md#código) (`tabla-igv`) |
| 6 | `Tabla.astro`: `:not(.tabla-partidas)` en el `content: none` de escritorio | **Aceptado.** Iguala la especificidad con la regla móvil que crea el rótulo. Sin el cambio, la regla de escritorio nunca ganaba (`registro-cambios-1440` ya no muestra rótulos dentro de las celdas) | Sin cambio en la ficha |

## Specs y fichas actualizadas

- `pantallas/RF-20-cambios-sensibles.md`: C1 y C2 con Partidas sin pie y el aviso separado; P3 con sus 8 campos y su orden; ayuda de Impuestos; resumen con SUBTOTAL → MÁS IGV → TOTAL; nota de registrar pago; nota de V2 en su propia línea; pendientes cerrados (`tipo` del impacto, `campo` de recargos, `porcentaje_adelanto` y nombres de ADR-015).
- `pantallas/RF-20-registro-cambios.md`: total visible en la ayuda del panel y fecha en `<time>`.
- `pantallas/RF-03-franjas.md`: descripción de Parámetros y ayudas de P3.
- `componentes/tabla.md`: la fila `tabla-igv` y Partidas sin pie para comparar antes y después.
- `componentes/README.md`: `<bugalu-cambio-sensible>` y `<bugalu-registro-cambios>` como Implementado, con los ajustes de esta revisión pendientes.

No hay componentes ni tokens nuevos. `python scripts/validar_docs.py docs --ids-desde docs/superpowers/specs/PROYECTO-v0.2.md` → ver la ENTREGA.
