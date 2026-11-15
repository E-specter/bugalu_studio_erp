---
id: patron-estados-sistema
titulo: Patrón — Estados vacío, carga, error y éxito
estado: borrador
depende_de: [comp-aviso, comp-indicador-estado]
---

# Estados vacío, carga, error y éxito

Figma solo dibuja el estado "con datos". Este patrón es **inferido** y obligatorio: toda vista y todo bloque que muestra datos del servidor especifica sus cuatro estados en su spec de pantalla.

## Vacío

[Panel](../componentes/panel.md) con el mismo título, y en el cuerpo:

1. Título corto en `fuente-familia-titulo`: qué no hay ("Aún no hay versiones").
2. Una frase: por qué y qué pasará ("El ingeniero publicará la primera versión al terminar la mezcla").
3. Acción solo si el usuario puede resolverlo ([botón](../componentes/boton.md) primario: "Registrar cliente").

Sin ilustraciones ([iconografía e imagen](../fundamentos/iconografia-imagen.md#ilustración)); como mucho, un icono `medida-icono-md`. Distinguir **vacío** de **sin resultados** de un filtro: este último ofrece "Quitar filtros".

## Carga

- La primera carga de una página la resuelve el servidor (Astro): no hay pantalla de carga global.
- Bloques que cargan después (islas): conservan su tamaño final y muestran "Cargando…" en `fuente-familia-tecnica` con `aria-busy="true"`; nada de esqueletos animados.
- Acciones: el [botón](../componentes/boton.md) pasa a Carga; procesos largos (subida, validación) usan [barra de progreso](../componentes/barra-progreso.md).
- Si tarda más de 10 s, se añade texto que lo explica ("Validando el WAV, puede tardar un minuto").

## Error

| Alcance | Forma |
|---|---|
| Campo | Mensaje bajo el campo ([formularios](formularios.md#validación)) |
| Bloque | [Aviso](../componentes/aviso.md) Error dentro del panel, con "Reintentar"; el resto de la vista sigue usable |
| Página (404, 403, 500) | Estructura de la sección + encabezado con código técnico (`[404] RUTA NO ENCONTRADA`), explicación y enlace a inicio |
| Conexión | [Indicador](../componentes/indicador-estado.md) de sincronización en Problema: "SIN CONEXIÓN" |

Los mensajes dicen qué pasó, si se perdió algo y qué hacer. No muestran trazas ni códigos internos al artista.

## Éxito

- Resultado de una acción: [aviso](../componentes/aviso.md) Éxito arriba de la vista de destino (patrón enviar → redirigir → mostrar), con `role="status"`.
- Cambios de estado de objeto: la [etiqueta](../componentes/etiqueta-tecnica.md) cambia y la [lista de eventos](../componentes/lista-eventos.md) registra el hecho.
- Sin notificaciones emergentes que desaparecen solas.

## Permisos

Lo que el rol no puede hacer no se muestra. Si la acción existe pero está bloqueada por estado (descarga antes del pago), se muestra deshabilitada con el motivo.
