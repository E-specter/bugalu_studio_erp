---
id: patron-tablas-y-tableros
titulo: Patrón — Tablas y tableros del panel interno
estado: borrador
depende_de: [comp-tabla, comp-tarjeta-proyecto]
---

# Tablas y tableros del panel interno

Origen: gestión de clientes (`161:842`), tablero de proyectos (`161:1083`), cotización (`141:29356`).

## Directorio (tabla)

```
encabezado-pantalla
métricas (4)
controles: búsqueda ─────────── filtros ── acción
panel: título + ayuda
  tabla
panel de seguimiento (≈70) │ calidad de datos (≈30)
```

1. **Controles** en una fila encima de la tabla: [campo](../componentes/campo.md) Búsqueda (flexible), [etiquetas](../componentes/etiqueta-tecnica.md) Filtro y la acción de crear ([botón](../componentes/boton.md) primario) a la derecha.
2. Búsqueda y filtros son un formulario `GET`: la URL refleja el estado, se puede compartir y funciona sin JS.
3. Filtros aplicados visibles como etiquetas Activa, cada una con su "quitar".
4. [Tabla](../componentes/tabla.md) en un [panel](../componentes/panel.md) con el total ("38 clientes").
5. Paginación al pie: "Anterior / Siguiente" + "1–20 de 38"; sin desplazamiento infinito.

## Tablero de producción

1. Controles: filtros a la izquierda y conmutador de vista (Tablero / Lista) a la derecha, ambos como enlaces.
2. Columnas por etapa (ancho igual, hueco `espacio-3`), cada una con cabecera (nombre + número de proyectos) y [barra de progreso](../componentes/barra-progreso.md) Límite.
3. [Tarjetas de proyecto](../componentes/tarjeta-proyecto.md) Columna, más antigua arriba, y acción "Nuevo proyecto" al pie de la primera columna.
4. **Sin arrastrar y soltar:** el cambio de etapa se hace desde la ficha del proyecto (accesible por teclado, con registro en el historial). El tablero es de lectura.
5. Vista Lista: la misma información como [tabla](../componentes/tabla.md); es la vista por defecto en < `punto-quiebre-escritorio`.

## Partidas (cotización y cobro)

[Tabla](../componentes/tabla.md) Partidas: descripción con detalle, cantidad, precio unitario e importe; subtotal, descuentos e impuestos como filas de pie; total en `fuente-tamano-titulo-sm`. Encima, [etiquetas](../componentes/etiqueta-tecnica.md) de estado de la propuesta y responsable.

## Densidad

| Contexto | Variante de tabla |
|---|---|
| Panel interno, listados de trabajo | Directorio o Compacta |
| Portal del artista | Nunca Compacta; preferir listas de [tarjetas](../componentes/tarjeta-proyecto.md) |
| Reportes ([RF-14](../../03-requerimientos/RF-14.md)) | Métricas arriba + tabla Compacta; exportación como enlace de descarga |
