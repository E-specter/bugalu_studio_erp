---
id: comp-hoja-reclamacion
titulo: Componente — Hoja de reclamación
estado: borrador
depende_de: [diseno-tokens, RF-16, comp-panel, comp-etiqueta-tecnica, comp-archivo, comp-indicador-estado]
---

# Hoja de reclamación

Hoja del Libro de Reclamaciones en **modo lectura**, con el orden y los rótulos del Anexo I ([RF-16](../../03-requerimientos/RF-16.md) CA-02). Figma no la dibuja: es **decisión del brief** (TAREA-RF16-1). Se repite en cuatro vistas (confirmación, constancia, detalle del cliente y del Administrador), por eso es ficha y no composición suelta. El formulario que la llena es la [spec del formulario](../pantallas/RF-16-formulario.md); esta ficha solo la muestra e imprime.

## Anatomía

1. Contenedor `<article>`: `color-fondo-superficie`, `borde-grosor-base` `color-borde-fuerte`, relleno `espacio-5`; ocupa el ancho de su columna (principal en App, `medida-contenedor-max` en Landing).
2. **Encabezado de hoja** (fila con regla inferior `borde-grosor-base`):
   - Antetítulo técnico "LIBRO DE RECLAMACIONES" (`fuente-familia-tecnica`, `fuente-tamano-micro`).
   - Título `<h2>` "HOJA DE RECLAMACIÓN N.º {numero}" (`fuente-familia-titulo`, `fuente-tamano-titulo-sm`); el número en `fuente-familia-tecnica` con `tabular-nums`. Sin número (confirmación): "HOJA DE RECLAMACIÓN" + línea "N.º Se asigna al enviar".
   - A la derecha (debajo en móvil): FECHA "18 nov 2026, 14:30" (`D MMM AAAA, HH:mm`, hora de Lima; en confirmación, la fecha de hoy sin hora: "18 nov 2026 · la hora se fija al enviar").
   - [Etiqueta](etiqueta-tecnica.md) Neutra "TRANSCRITA DEL LIBRO FÍSICO · HOJA {numero_hoja_fisica}" si `origen = libro_fisico`; entonces FECHA es `fecha_original`.
3. **Proveedor**: `<dl>` en una fila (tres columnas desde `punto-quiebre-tableta`): RAZÓN SOCIAL · RUC · DOMICILIO, con los datos de `proveedor` (o los fijos de CA-02 antes de registrar).
4. **Secciones 1 a 3**: `<section>` con `<h3>` numerado como el Anexo I ("1. IDENTIFICACIÓN DEL CONSUMIDOR RECLAMANTE", "2. IDENTIFICACIÓN DEL BIEN CONTRATADO", "3. DETALLE DE LA RECLAMACIÓN Y PEDIDO DEL CONSUMIDOR"), regla superior `borde-grosor-fino`, separación `espacio-5`. Datos en `<dl>`: rótulo `fuente-familia-tecnica` `fuente-tamano-micro` `color-texto-secundario`; valor `fuente-tamano-base` `color-texto-principal`. Pares hermanos en 2 columnas desde `punto-quiebre-tableta`. DETALLE y PEDIDO a ancho completo, `color-texto-cuerpo`, `white-space: pre-line` (conservan los saltos del consumidor) y `overflow-wrap: anywhere`.
5. Adjuntos (en la sección 3): lista de [archivo](archivo.md) Lectura; en el Administrador, con "Abrir {nombre}".
6. **Sección 4** "4. OBSERVACIONES Y ACCIONES ADOPTADAS POR EL PROVEEDOR" (solo hojas registradas): con respuesta, FECHA DE COMUNICACIÓN DE LA RESPUESTA (`enviada_en`), MEDIO, REFERENCIA DE LA CARTA (si carta), RESPONDIÓ (`respondida_por.nombre`, solo Administrador) y el texto (`pre-line`). Sin respuesta: [indicador](indicador-estado.md) En línea Pendiente "SIN RESPUESTA AÚN" + "Plazo de respuesta: hasta el {vence_respuesta en D MMM AAAA}".
7. **Pie de la hoja** (`fuente-tamano-pequeno`, `color-texto-cuerpo`): las definiciones de reclamo y queja como notas y las dos leyendas del Anexo I, con el texto de la [spec del formulario](../pantallas/RF-16-formulario.md#textos-del-anexo-i).

Valores: "—" si un opcional no vino (teléfono, monto, descripción). Monto: `S/ 1 250,00`. Documento: "DNI 12345678". Tipo `null`: "Sin marcar". Medio: "Correo electrónico" · "Carta al domicilio". Bien: "Producto" · "Servicio".

## Variantes

| Variante | Número y fecha | Sección 4 | Adjuntos | Uso |
|---|---|---|---|---|
| Confirmación | "Se asigna al enviar" · hoy | No | Nombre y metadato, sin acción | Paso de confirmación del [formulario](../pantallas/RF-16-confirmacion-y-constancia.md) |
| Constancia | Los registrados | No (la hoja acaba de nacer) | Ídem | Respuesta del registro |
| Consulta | Los registrados | Sí | Cliente: sin acción · Administrador: "Abrir {nombre}" | [Mis reclamos](../pantallas/RF-16-mis-reclamos.md), [bandeja](../pantallas/RF-16-bandeja.md) |

## Estados

Estática. Carga, error y 404 los pone la vista que la contiene ([estados del sistema](../patrones/estados-sistema.md)).

## Impresión

"Imprimir o guardar en PDF" llama a `window.print()`; el diálogo del navegador ofrece guardar en PDF. Reglas `@media print` (en la ficha porque toda vista con la hoja las necesita):

1. **Se imprime solo la hoja.** Se ocultan (`display: none`) la cabecera, la navegación, el enlace "Saltar al contenido", el pie público, el encabezado de pantalla, los avisos, los botones, la barra de acciones y todo lo que la vista marque con `data-no-imprimir`. La regla vive en el layout con `@media print` sobre esos elementos; la hoja no se mueve de su sitio.
2. Fondos fuera (`background: none`, los navegadores no los imprimen por defecto y el lavanda se perdería igual); texto y reglas conservan `color-texto-principal`, `color-texto-cuerpo` y `color-borde-fuerte` (navy y tinta se leen en blanco y negro). Etiquetas e indicadores llevan su texto, así que no dependen del color.
3. Ancho completo de la página (sin `max-inline-size`), sin sombras; `break-inside: avoid` en el encabezado de hoja, el proveedor y cada `<dl>`; DETALLE, PEDIDO y RESPUESTA sí pueden partirse entre páginas.
4. Tamaños: los mismos tokens; nada de unidades nuevas. Márgenes de página: los del navegador (sin `@page`).
5. Al pie, solo en impresión: "Copia impresa desde bugalu.studio el {D MMM AAAA, HH:mm}" (`fuente-tamano-micro`), para distinguirla del original. El dominio sale de `location.host`.

## Tokens

`color-fondo-superficie`, `color-borde-fuerte`, `color-texto-principal`, `color-texto-cuerpo`, `color-texto-secundario`, `borde-grosor-base`, `borde-grosor-fino`, `espacio-5`, `fuente-familia-tecnica`, `fuente-familia-titulo`, `fuente-tamano-micro`, `fuente-tamano-pequeno`, `fuente-tamano-base`, `fuente-tamano-titulo-sm`, `punto-quiebre-tableta`.

## Relaciones

Usa [etiqueta-tecnica](etiqueta-tecnica.md), [archivo](archivo.md) e [indicador-estado](indicador-estado.md). No es un [panel](panel.md): no lleva código de sección propio porque sus títulos son los del Anexo I.

## Accesibilidad

- `<article aria-labelledby>` al `<h2>` de la hoja; secciones con `<h3>`; datos en `<dl>` (`<dt>`/`<dd>`), nunca en tabla.
- La fecha va en `<time datetime>` con el ISO del servidor.
- Las notas de reclamo y queja son texto normal al pie (no superíndices sueltos): el lector las encuentra en orden.
- En impresión no hay nada interactivo; en pantalla, "Abrir {nombre}" sigue la ficha de [archivo](archivo.md#accesibilidad).

## Código

`frontend/src/componentes/HojaReclamacion.astro`: `<template>` de la hoja que llena `frontend/src/servicios/hoja-reclamacion.js` con `pintarHoja(nodo, hoja, {variante, administrador})`, como el [resumen legal](resumen-legal.md). Una función, cuatro vistas.
