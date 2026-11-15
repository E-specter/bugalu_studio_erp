---
id: arq-modelo-datos
titulo: Modelo de datos inicial
estado: borrador
depende_de: [ADR-005, ADR-006, D-12]
---

# Modelo de datos inicial

Todas las claves primarias son `uuid` ([ADR-006](../00-proyecto/decisiones/ADR-006-claves-uuid.md)). Los montos son `numeric(10,2)` en PEN. Asignación de personal pendiente (D-12, ver [decisiones](../00-proyecto/decisiones/README.md)).

## Identidad y catálogo

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `usuario` | `id` (uuid, = `auth.users.id`), `nombre`, `rol` (`cliente`/`personal`/`administrador`, por defecto `cliente`), `especialidad`, `creado_en` | `id` → `auth.users` con borrado en cascada ([ADR-005](../00-proyecto/decisiones/ADR-005-supabase-auth.md)); el correo vive en `auth.users`. RLS: cada usuario lee y edita (`nombre`, `especialidad`) solo su perfil, nunca `rol`; el administrador lee todos (`public.es_administrador()`); sin insert ni delete por la API. Un trigger en `auth.users` crea el perfil `cliente` |
| `sala_tecnica` | `id`, `nombre`, `tarifa_hora_grabacion`, `tarifa_hora_ensayo`, `estado_operativo` | — |
| `servicio` | `id`, `nombre`, `tipo`, `tarifa` | — (catálogo usado por la simulación, [RN-15](../02-dominio/reglas-negocio.md)) |

## Disponibilidad, reservas y asesorías

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `franja_sala` | `id`, `inicio`, `fin` | `id_sala` → sala_tecnica · publicada por un administrador ([RN-12](../02-dominio/reglas-negocio.md)) |
| `reserva` | `id`, `tipo` (`grabacion`/`ensayo`), `inicio`, `fin`, `fin_buffer`, `estado`, `folio` (único) | `id_cliente` → usuario · `id_sala` → sala_tecnica · `id_franja` → franja_sala · `id_cotizacion` → cotizacion (opcional) · `id_proyecto` → proyecto_musical (opcional) · `id_ingeniero` → usuario (D-12) |
| `horario_profesional` | `id`, `inicio`, `fin` | `id_profesional` → usuario (rol `personal`, especialidad `asesoria`) |
| `asesoria` | `id`, `inicio`, `fin`, `modalidad` (`presencial`/`virtual`), `lugar` o `enlace`, `precio`, `estado` | `id_cliente` → usuario · `id_profesional` → usuario ([RN-14](../02-dominio/reglas-negocio.md)) |

## Cotizaciones y pagos

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `cotizacion` | `id`, `subtotal`, `descuento`, `total`, `fecha_vigencia`, `estado` | `id_cliente` → usuario · `id_asesoria` → asesoria (opcional) ([RN-16](../02-dominio/reglas-negocio.md)) |
| `detalle_cotizacion` | `id`, `cantidad`, `precio_unitario` | `id_cotizacion` → cotizacion · `id_servicio` → servicio |
| `cuota` | `id`, `monto`, `vence` (fecha) o `hito` (`al_reservar`/`al_terminar`/`al_encargar`/`al_aprobar_version`), `estado` | exactamente una de: `id_reserva`, `id_asesoria`, `id_cotizacion`, `id_proyecto` |
| `comprobante_pago` | `id`, `metodo` (`transferencia`/`yape`/`plin`/`tarjeta`), `monto`, `numero_operacion`, `ruta_captura`, `estado`, `motivo_rechazo` | `id_cuota` → cuota · `id_validador` → usuario ([RN-04](../02-dominio/reglas-negocio.md)) |

Las capturas van al bucket privado `comprobantes` ([ADR-003](../00-proyecto/decisiones/ADR-003-almacenamiento-supabase-storage.md)).

## Proyectos y entregables

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `proyecto_musical` | `id`, `codigo` (PRJnn, único), `genero`, `tomas_pactadas`, `fecha_entrega`, `fase`, `rondas_pactadas`, `rondas_consumidas` | `id_cliente` → usuario · `id_cotizacion` → cotizacion (opcional). Lo abre el Administrador o nace al aceptar una cotización |
| `version_audio` | `id`, `nombre_archivo`, `numero_version`, `ruta_almacenamiento`, `tamano_bytes`, `formato`, `estado_revision` | `id_proyecto` → proyecto_musical · `id_ingeniero` → usuario |
| `observacion_tecnica` | `id`, `marca_tiempo_ms`, `categoria`, `texto`, `ronda` | `id_version` → version_audio |

## Entidades faltantes para cubrir los RF

| Tabla propuesta | Requerimiento |
|---|---|
| `asignacion_sesion` (reserva × personal × función) | [RF-07](../03-requerimientos/RF-07.md) — una reserva admite varios técnicos |
| `evaluacion_servicio` | [RF-13](../03-requerimientos/RF-13.md) |
| `notificacion` (registro de envíos) | [RF-06](../03-requerimientos/RF-06.md) |

Las migraciones versionadas viven en `supabase/` (ver [herramientas-mcp](../06-operacion/herramientas-mcp.md)); este archivo se actualiza en la misma tarea que la migración.
