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
| `usuario` | `id` (uuid, = `auth.users.id`), `nombre`, `telefono` (`^\+?[0-9]{9,15}$` o nulo), `nombre_artistico`, `rol` (`cliente`/`personal`/`administrador`, por defecto `cliente`), `especialidad`, `correo_verificado_en` (nulo = sin verificar), `creado_en` | `id` → `auth.users` con borrado en cascada ([ADR-005](../00-proyecto/decisiones/ADR-005-supabase-auth.md)); el correo vive en `auth.users`. RLS: cada usuario lee su perfil y edita solo `nombre`, `telefono` y `nombre_artistico` (`rol` y `especialidad` los asigna el administrador); el administrador lee todos (`public.es_administrador()`); sin insert ni delete por la API. Un trigger en `auth.users` crea el perfil `cliente` con `nombre`, `telefono` (si es válido) y `nombre_artistico` de `raw_user_meta_data`, nunca rol ni especialidad. Un trigger impide dejar el sistema sin administradores (SQLSTATE `BG001`, el backend lo traduce a 409 `ultimo_administrador`); toma `pg_advisory_xact_lock(20261119)` y recuenta dentro del bloqueo, así dos cambios cruzados concurrentes no dejan cero administradores. Otro trigger en `auth.users` (`after update of email`) pone `correo_verificado_en` en nulo cuando el correo cambia. Supabase confirma el correo al registrar (ADR-008), así que la verificación propia vive en `correo_verificado_en`, sin privilegio de escritura para `authenticated`; solo la fija `public.marcar_correo_verificado()` (`security definer`): exige que `amr` del token incluya `otp`, `magiclink` u `oauth` (si no, SQLSTATE `BG002`, el backend lo traduce a 409 `verificacion_no_valida`). `public.correo_confirmado()` lee `correo_verificado_en` de `auth.uid()`. `public.asignar_rol(id_usuario, rol, especialidad)` (`security definer`, solo `authenticated` y solo si `es_administrador()`, si no `42501`) es la única vía para cambiar `rol` y `especialidad`; respeta el trigger del último administrador (`BG001`) y lanza `P0002` si el usuario no existe. `public.correo_de_usuario(id_usuario)` (`security definer`) devuelve el correo de `auth.users` al propio usuario o a un administrador (`42501` a otros); el backend la usa para `Perfil.correo` y `Solicitud.correo` de terceros. Todas con `search_path` vacío, `revoke` a `public`/`anon`. El backend conecta como `bugalu_api` (`login`, `noinherit`, miembro solo de `anon` y `authenticated`, sin acceso directo a `usuario`); cada transacción asume `authenticated`. PostgREST no expone `public` |
| `solicitud_acceso` | `id`, `especialidad`, `mensaje`, `estado` (`pendiente`/`aprobada`/`rechazada`, por defecto `pendiente`), `motivo`, `creada_en`, `revisada_en` | `id_usuario` → usuario (cascada) · `id_revisor` → usuario ([ADR-008](../00-proyecto/decisiones/ADR-008-acceso-y-roles-v1.md)). Índice único parcial: una sola `pendiente` por usuario. RLS: el dueño lee las suyas e inserta solo con su `id_usuario`, `estado` `pendiente` y sin `motivo` ni `id_revisor` (privilegio de columna y política); el administrador lee todas y actualiza `estado`, `motivo`, `id_revisor` y `revisada_en`; nadie borra por la API; `anon` nada |
| `sala_tecnica` | `id`, `nombre`, `sede`, `activa` (único `nombre`+`sede`) | — (hoy una, "Sala principal" en La Molina, [ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md)). RLS común del catálogo, abajo |
| `servicio` | `id`, `nombre` (único), `categoria` (`grabacion`/`ensayo`/`live`/`posproduccion`), `ocupa_sala`, `tarifa_hora`, `monto_fijo` (≥ 0, por defecto 0) (`numeric(10,2)` ≥ 0), `activo` | — (motor de precio, [RN-15](../02-dominio/reglas-negocio.md)). Iniciales: voces, instrumentos, banda en vivo, ensayo, live session, mezcla y masterización (estas dos con `ocupa_sala = false`) |
| `especialista` | `id`, `nombre` (único), `monto_fijo`, `monto_variable` (≥ 0), `unidad` (`hora`/`lapso_30`), `activo` | — (ingeniero de sonido, ejecutante, audiovisual, productor o arreglista) |
| `servicio_especialista` | clave compuesta `id_servicio`, `id_especialista` | ambos con borrado en cascada; especialistas por defecto (ingeniero de sonido en grabación y live) |
| `recargo` | `tipo` (clave: `noche`/`fin_de_semana`/`feriado`), `porcentaje` (0–300), `desde`, `hasta` (`time`; obligatorios solo en noche, puede cruzar medianoche) | — |
| `feriado` | `fecha` (clave), `nombre` | — |
| `parametro` | `clave` (clave; lista cerrada: `dias_limite_pago`, `horas_limite_pago`, `anticipacion_minima_horas`, `anticipacion_maxima_semanas`), `valor` (entero > 0) | plazos de caducidad y anticipación ([RN-17](../02-dominio/reglas-negocio.md), [RN-18](../02-dominio/reglas-negocio.md)). Solo el administrador lee y escribe |

**RLS del catálogo** (migración `20261120100000_rf02_rf03_catalogo_tarifas`): `anon` y `authenticated` leen sala, servicio, especialista, servicio_especialista, recargo y feriado; solo el administrador (`public.es_administrador()`) inserta y actualiza (`servicio_especialista` solo inserta); nadie borra por la API salvo el administrador en `feriado`. `parametro` no es legible por `anon` ni clientes. Los montos y porcentajes iniciales son **provisionales** (ejemplo) hasta que el estudio los defina.

## Disponibilidad, reservas y asesorías

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `franja_sala` | `id`, `inicio`, `fin` (`fin > inicio`, múltiplos de 30 min; exclusión de solapes por sala con `btree_gist`) | `id_sala` → sala_tecnica · `id_publicador` → usuario (nulo si se borra) ([RN-12](../02-dominio/reglas-negocio.md)) |
| `cierre_sala` | `id`, `inicio`, `fin` (`fin > inicio`), `motivo` | `id_sala` → sala_tecnica · `id_autor` → usuario (nulo si se borra) |
| `reserva` | `id`, `inicio`, `fin`, `fin_buffer`, `estado` (`pre_reservada`/`confirmada`/`en_curso`/`finalizada`/`cancelada`, por defecto `pre_reservada`), `motivo_cancelacion` (`cliente`/`caducada`/`administrador`; presente si y solo si `cancelada`), `folio` (único, `R-AAAA-NNNNN` desde la secuencia `reserva_folio_seq`), `precio` (jsonb, desglose), `total` (`numeric(10,2)`), `vence_pago` (nulo = no caduca), `detalle`; `inicio` y `fin` en múltiplos de 30 min, duración de 30 min a 8 h; `fin_buffer = fin + 30 min` lo fija el trigger `before insert`; exclusión `btree_gist` de solapes de `[inicio, fin_buffer)` por sala entre reservas no canceladas (SQLSTATE `23P01`) | `id_cliente` → usuario · `id_sala` → sala_tecnica · `id_servicio` → servicio · `id_franja` → franja_sala (opcional; que el tramo quepa en la franja aún lo valida el backend) · `id_cotizacion` → cotizacion (opcional) · `id_proyecto` → proyecto_musical (opcional) · `id_ingeniero` → usuario (D-12) |
| `horario_profesional` | `id`, `inicio`, `fin` | `id_profesional` → usuario (rol `personal`, especialidad `asesoria`) |
| `asesoria` | `id`, `inicio`, `fin`, `modalidad` (`presencial`/`virtual`), `lugar` o `enlace`, `precio`, `estado` | `id_cliente` → usuario · `id_profesional` → usuario ([RN-14](../02-dominio/reglas-negocio.md)) |

**RLS de franjas y reservas** (migración `20261121100000_rf03_rf04_franjas_reservas`): `franja_sala` y `cierre_sala`, lectura pública y escritura solo del administrador. `reserva`: el cliente lee e inserta solo las suyas (`id_cliente = auth.uid()`, `estado = 'pre_reservada'`, sin `motivo_cancelacion`); no tiene privilegio sobre `folio` ni `fin_buffer` al insertar ni update alguno; `estado`, `motivo_cancelacion`, `vence_pago` y `detalle` los actualiza solo el administrador (o funciones `security definer`); `personal` y `administrador` leen todas (`public.es_personal()`); nadie borra. `reserva_especialista` y `cuota` se ven con su reserva y las inserta su dueño o el administrador. `anon` no accede a `reserva`: la ocupación pública sale de `public.ocupacion_sala(id_sala, desde, hasta)` (`security definer`), que devuelve solo `inicio` y `fin_buffer` de las reservas vigentes; una `pre_reservada` vencida sin pagos cuenta como libre. **Caducidad (RN-18):** `public.caducar_reservas()` (`security definer`, sin acceso para clientes) cancela con motivo `caducada` las `pre_reservada` con `vence_pago < now()` sin pagos y encola `reserva_caducada` en `notificacion`; `pg_cron` la corre cada minuto (job `caducar_reservas`) y el trigger `before insert` la corre sobre el tramo a ocupar. `public.tiene_pagos(id_reserva)` es el punto de extensión: hoy cuenta cuotas `pagada`; al crear `comprobante_pago` debe incluir los comprobantes registrados.

**Lecturas de RF-03** (migración `20261123100000_rf03_lectura_disponibilidad`): `public.limites_reserva()` (`security definer`, `anon` y `authenticated`) devuelve solo `minima_horas` y `maxima_semanas` de `parametro`; `public.nombres_de_clientes(uuid[])` (`security definer`, solo `authenticated`) devuelve `id` y `nombre` únicamente si quien llama es personal o administrador (si no, sin filas).

## Cotizaciones y pagos

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `cotizacion` | `id`, `subtotal`, `descuento`, `total`, `fecha_vigencia`, `estado` | `id_cliente` → usuario · `id_asesoria` → asesoria (opcional) ([RN-16](../02-dominio/reglas-negocio.md)) |
| `detalle_cotizacion` | `id`, `cantidad`, `precio_unitario` | `id_cotizacion` → cotizacion · `id_servicio` → servicio |
| `cuota` | `id`, `monto`, `vence` (fecha) o `hito` (`al_reservar`/`al_terminar`/`al_encargar`/`al_aprobar_version`), `estado` (`pendiente`/`pagada`) | exactamente una de: `id_reserva`, `id_asesoria`, `id_cotizacion`, `id_proyecto`. **Hoy** existe solo con `id`, `id_reserva` (cascada), `hito`, `monto`, `estado`; `vence` y las demás relaciones llegan con sus RF. RLS: visible con su reserva; la inserta el dueño de la reserva o el administrador; solo el administrador cambia `estado` |
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

## Tablas de reservas ya creadas

| Tabla | Campos clave | Relaciones |
|---|---|---|
| `reserva_especialista` | `monto_fijo`, `monto_variable`, `unidad` (`hora`/`lapso_30`) aplicados a la reserva | clave `id_reserva` (cascada) + `id_especialista` ([RF-04](../03-requerimientos/RF-04.md)) |
| `notificacion` | `id`, `tipo` (`reserva_creada`/`reserva_caducada`), `destinatario` (correo), `datos` (jsonb), `creada_en`, `enviada_en`, `intentos`, `error` | Bandeja de salida ([ADR-009](../00-proyecto/decisiones/ADR-009-reservas-tarifas-y-caducidad.md), [RF-04](../03-requerimientos/RF-04.md), [RF-06](../03-requerimientos/RF-06.md)). Sin acceso para `anon` ni `authenticated`: solo `select`, `insert` y `update` del rol `bugalu_api` (política propia) y las funciones `security definer`. Índice parcial de pendientes (`enviada_en` nulo) |

`servicio_especialista`: el administrador puede borrar filas (quitar especialistas por defecto).

Las migraciones versionadas viven en `supabase/` (ver [herramientas-mcp](../06-operacion/herramientas-mcp.md)); este archivo se actualiza en la misma tarea que la migración.
