---
id: arq-modelo-datos
titulo: Modelo de datos inicial
estado: borrador
depende_de: [D-04, D-12]
---

# Modelo de datos inicial

Tipo de clave primaria pendiente (D-04) y asignación de personal pendiente (D-12): ver [decisiones](../00-proyecto/decisiones/README.md).

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `usuario` | `id`, `correo` (único), `rol`, `especialidad` | — |
| `sala_tecnica` | `id`, `nombre`, `tipo`, `tarifa_hora`, `estado_operativo` | — |
| `reserva` | `id`, `inicio`, `fin`, `fin_buffer`, `estado`, `folio` | `id_cliente` → usuario · `id_sala` → sala_tecnica · `id_ingeniero` → usuario |
| `proyecto_musical` | `id`, `codigo` (PRJnn), `genero`, `tomas_pactadas`, `fecha_entrega`, `fase`, `rondas_pactadas`, `rondas_consumidas` | `id_cliente` → usuario |
| `version_audio` | `id`, `nombre_archivo`, `numero_version`, `ruta_almacenamiento`, `tamano_bytes`, `formato`, `estado_revision` | `id_proyecto` → proyecto_musical · `id_ingeniero` → usuario |
| `observacion_tecnica` | `id`, `marca_tiempo_ms`, `categoria`, `texto`, `ronda` | `id_version` → version_audio |
| `comprobante_pago` | `id`, `tipo` (anticipo/liquidacion), `monto`, `metodo`, `codigo_operacion`, `estado` | `id_reserva` → reserva (opcional) · `id_proyecto` → proyecto_musical (opcional) |
| `cotizacion` | `id`, `subtotal`, `descuento`, `total`, `fecha_vigencia`, `estado` | `id_cliente` → usuario |

## Entidades faltantes para cubrir los RF

| Tabla propuesta | Requerimiento |
|---|---|
| `servicio` (catálogo) y `detalle_cotizacion` | [RF-02](../03-requerimientos/RF-02.md) |
| `asignacion_sesion` (reserva × personal × función) | [RF-07](../03-requerimientos/RF-07.md) — una reserva admite varios técnicos |
| `evaluacion_servicio` | [RF-13](../03-requerimientos/RF-13.md) |
| `notificacion` (registro de envíos) | [RF-06](../03-requerimientos/RF-06.md) |

Las migraciones versionadas viven en `supabase/` (ver [herramientas-mcp](../06-operacion/herramientas-mcp.md)); este archivo se actualiza en la misma tarea que la migración.
