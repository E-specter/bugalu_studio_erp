# Contratación, pagos y decisiones base (D-01..D-04) — Diseño

> Estado: aprobado por el usuario (2026-11-15; builder check hecho, respuestas incorporadas) · Trabajo 2 de la hoja de ruta (fase 1). Cierra D-01..D-04 y rediseña el dominio de contratación a partir de cómo opera hoy el estudio.

## 1. Intención

El flujo de contratación de los docs (catálogo → cotización → reserva → anticipo) salió del informe; el de Figma (servicio → brief → agenda de asesoría → cotización → proyecto) salió del diseño. Ninguno describe cómo opera el estudio. Este trabajo fija el flujo real, contado por el usuario, y las cuatro decisiones de infraestructura que bloquean el esqueleto (fase 3).

Por qué importa: es un **piloto** ante el cliente. El flujo tiene que reconocerse como el del estudio y transmitir confianza (la asesoría existe para eso: claridad, convenios, fidelidad).

## 2. Objetivos, no-objetivos y anti-objetivos

**Objetivos**
- ADR-003..ADR-006 cierran D-01..D-04.
- Reglas de negocio, estados y RF reescritos para el flujo real: franjas publicadas por el estudio, reserva de sala (grabación y ensayo), asesoría, simulación de precio, cotización a medida con plan de cuotas y validación manual de pagos.
- La brecha de Figma queda documentada como pantallas a especificar desde el brief (fase 2), no como trabajo en Figma.

**No-objetivos**
- Criterios de aceptación de cada RF (fase 7).
- Cerrar D-05, D-06, D-07, D-08, D-10, D-11, D-12, ni la parte de impuestos y facturación de D-09.
- Migraciones o código (fases 3 y 7).

**Anti-objetivos** (fallaría aunque "funcione")
- Que el cliente vea un calendario libre de salas: solo ve lo que el estudio abre.
- Que un pago cambie de estado sin que un administrador lo valide.
- Que la descarga del máster quede sin un cobro que la proteja.

## 3. Restricciones

- Supabase **local** (CLI + Docker), sin suscripción ni hosting (D-08 abierta): nada puede depender de una URL pública.
- Perú, moneda **PEN**.
- Docs en español, identificadores ASCII ([convenciones](../../01-arquitectura/convenciones.md)); cada archivo ≤ límite de líneas del validador.

## 4. Enfoques considerados

| Tema | Opciones | Elegida (usuario, 2026-11-15) |
|---|---|---|
| Infraestructura (D-01, D-03, D-04) | Supabase de punta a punta · mezclar S3 / auth propia / claves enteras | **Supabase de punta a punta**: lo demás suma código sin servir a ningún RF |
| Pasarela (D-02) | A. Sin pasarela: registro + captura + validación manual · B. Pasarela peruana (Culqi, Izipay, Niubiz, Mercado Pago) | **A**: es como opera hoy; B exige cuenta de comercio y URL pública para webhooks, y el usuario exige validación manual igual |
| Modelo de contratación | Una "reserva" para todo con tipo · entidades separadas | **Mixto**: grabación y ensayo son una sola `reserva` de sala (mismo espacio); la **asesoría es otra entidad** (profesional, presencial en lugar acordado o virtual por videollamada) |

## 5. Decisiones de infraestructura (contenido de los ADR)

| ADR | Decisión | Consecuencias clave |
|---|---|---|
| ADR-003 (D-01) | Supabase Storage, buckets **privados**: `entregables` (WAV) y `comprobantes` (capturas de pago) | API compatible con S3: migrar a S3 es cambiar el adaptador, no el dominio. Descarga del máster por URL firmada de 7 días (RN-07). Actor "Almacenamiento Cloud" = Supabase Storage |
| ADR-004 (D-02) | Sin pasarela en v1. Pago = registro manual (método, monto PEN, n.º de operación, captura) + validación del Administrador | Puerto `PasarelaPagos` en `pagos/dominio` con un único adaptador manual; una pasarela real es otro adaptador. Actor "Pasarela de Pagos / Banco" pasa a "Banco / billetera" externo sin integración |
| ADR-005 (D-03) | Supabase Auth; perfil en `usuario` con `id` = `auth.users.id`; rol en el perfil, aplicado por RLS y por el backend | Sin `password_hash` propio. FastAPI valida el JWT de Supabase |
| ADR-006 (D-04) | UUID en todas las tablas | Alineado con `auth.users`. Los folios y códigos legibles (`PRJnn`, folio de reserva) siguen como columnas aparte |

## 6. Flujo de contratación

```
Visitante ─► ve franjas de sala y simula precio (público, sin cuenta)
          ├─► reserva franja de sala ──► crea cuenta ──► Pre-reservada ──► paga 50% + captura
          │                                                     └─► Admin valida ─► Confirmada ─► En curso ─► Finalizada ─► paga 50% restante
          └─► agenda asesoría con un profesional (precio fijo, pago único) ─► Admin valida ─► Confirmada ─► Realizada
                                                                                   └─► Cotización formal a medida (plan de cuotas) ─► cliente acepta
Posproducción (mezcla/máster): 50% al encargar ─► ... ─► 50% al aprobar la versión ─► Admin valida ─► descarga del máster (7 días)
```

### 6.1 Reglas de negocio (reemplazan o se suman a [reglas-negocio](../../02-dominio/reglas-negocio.md))

| ID | Regla | Cambio |
|---|---|---|
| RN-01 | Dos reservas de la misma sala no se solapan (incluido su buffer). | Igual |
| RN-02 | Toda reserva de sala genera un buffer de 30 min posterior que bloquea la sala. No aplica a asesorías. | Precisa alcance |
| RN-03 | Una reserva de sala pasa a `Confirmada` cuando el Administrador valida el pago del 50% (o la cuota que fije su cotización). | Precisa |
| RN-04 | Todo pago se registra con método (`transferencia`, `yape`, `plin`, `tarjeta`), monto en PEN, n.º de operación y captura; queda `Pendiente de validacion` hasta que el Administrador lo aprueba o rechaza (con motivo). | Reescrita |
| RN-05 | La posproducción (mezcla/máster) tiene precio propio: 50% al encargarla y 50% al aprobar el cliente la versión (salvo cotización a medida). | Reescrita |
| RN-06, RN-07, RN-08, RN-09, RN-10, RN-11 | — | Igual |
| RN-12 | El estudio publica franjas semanales de disponibilidad por sala, de duración y cantidad variables. El cliente reserva un tramo dentro de una franja, en múltiplos de 30 min (mínimo 30 min); el resto de la franja sigue disponible. El tramo más su buffer debe caber en la franja. | Nueva |
| RN-13 | Reserva de sala, tipo `grabacion` o `ensayo`: 50% al reservar, 50% al terminar la sesión. El ensayo solo lo reserva un cliente con al menos un servicio previo `Confirmada` (reserva de grabación o asesoría). | Nueva |
| RN-14 | Asesoría: precio fijo, pago único al agendarla, con un profesional concreto según su horario, en múltiplos de 30 min (mínimo 30 min); modalidad `presencial` (lugar acordado) o `virtual` (enlace de videollamada). Un profesional no tiene dos asesorías solapadas. | Nueva |
| RN-15 | La simulación de precio es una estimación sin valor de cotización. | Nueva |
| RN-16 | Tras una asesoría, el estudio puede emitir una cotización formal con precio y plan de cuotas (monto + fecha o hito) que reemplaza el 50/50 por sesión. El costo de la asesoría no se descuenta salvo que la cotización lo indique. | Nueva |

### 6.2 Estados

- **Reserva de sala:** se mantiene `Pre-reservada → Confirmada → En curso → Finalizada` (+ `Cancelada`). El saldo pendiente vive en la cuota, no en el estado de la reserva.
- **Asesoría (nueva):** `Pendiente de pago → Confirmada → Realizada` (+ `Cancelada`).
- **Pago (comprobante):** `Pendiente de validacion → Aprobado | Rechazado`. Un rechazo deja la cuota pendiente y el cliente puede subir otro.

### 6.3 Modelo de datos (cambios a [modelo-datos](../../01-arquitectura/modelo-datos.md))

| Tabla | Cambio |
|---|---|
| `franja_sala` (nueva) | `id_sala`, `inicio`, `fin`, publicada por el Administrador |
| `reserva` | + `tipo` (`grabacion`/`ensayo`), + `id_franja`, + `id_cotizacion` (opcional), + `id_proyecto` (opcional) |
| `horario_profesional` (nuevo) | `id_profesional` → usuario, `inicio`, `fin` |
| `asesoria` (nueva) | `id_cliente`, `id_profesional`, `inicio`, `fin`, `modalidad`, `lugar` o `enlace`, `precio`, `estado` |
| `servicio` (catálogo, ya propuesto) | + tarifa usada por la simulación |
| `cotizacion` + `detalle_cotizacion` | + `id_asesoria` (opcional); el plan va en `cuota` |
| `cuota` (nueva) | `monto`, `vence` (fecha) o `hito` (`al_reservar`, `al_terminar`, `al_encargar`, `al_aprobar_version`), `estado`; pertenece a una reserva, una asesoría, una cotización o un proyecto |
| `comprobante_pago` | se cuelga de `cuota`; + `metodo`, `numero_operacion`, `ruta_captura`, `estado`, `motivo_rechazo`, `id_validador` |

### 6.4 Requerimientos

| RF | Cambio |
|---|---|
| RF-02 | "Simular precio y emitir cotización a medida": catálogo + simulación pública (RN-15) + cotización formal con plan de cuotas tras asesoría (RN-16) |
| RF-03 | "Publicar y consultar franjas de sala": el Administrador publica; el visitante consulta (RN-12) |
| RF-04 | "Registrar reserva de sala": tipo grabación o ensayo, sobre una franja (RN-01, RN-02, RN-13) |
| RF-05 | "Registrar y validar pagos": cualquier cuota, captura y validación manual (RN-04); deja de ser solo el anticipo |
| RF-11 | "Cobrar posproducción": cuotas `al_encargar` y `al_aprobar_version` del proyecto, por el mismo mecanismo de RF-05; la segunda habilita la descarga (RN-06) |
| RF-15 (nuevo) | "Agendar asesoría artística": horarios del profesional, modalidad, pago único (RN-14). Módulo `asesorias` |

Actores ([actores-roles](../../02-dominio/actores-roles.md)): + **Visitante** (sin cuenta: ve franjas y simula); + **Profesional artístico** (personal interno que da asesorías). Flujos: se reescribe [registrar-reserva](../../02-dominio/flujos/registrar-reserva.md) y [ciclo-servicio](../../02-dominio/flujos/ciclo-servicio.md); se añade `agendar-asesoria`.

### 6.5 Conciliación con Figma

El flujo diseñado (servicio → brief → agenda de asesoría → cotización → revisión → proyecto activado) es la **rama de asesoría** del flujo real; se conserva. Faltan pantallas para: franjas y reserva de sala con simulación, registro y validación de pagos, ensayos, y lo que ya faltaba (RF-07, RF-14). Se especifican desde el brief en la fase 2; se anota en [figma](../../07-diseno/figma.md#brecha-detectada).

D-09 queda **parcialmente cerrada**: moneda PEN; impuestos y facturación electrónica siguen abiertos.

## 7. Decisiones del diseñador (leader), corregibles

- La asesoría se paga completa al agendarla (RN-14).
- La simulación y las franjas son públicas; la cuenta se crea al reservar (Visitante).
- "Profesional artístico" es personal interno con especialidad, no un rol nuevo de sistema.
- Las asesorías no generan buffer (no ocupan sala); se agendan en múltiplos de 30 min, igual que la sala (usuario).
- La validación de pagos la hace el Administrador.
- Agendar una asesoría exige cuenta (se crea antes de pagar, igual que al reservar sala).
- "Profesional artístico" = usuario con rol de sistema `personal` y la especialidad `asesoria`; RLS se aplica por rol, la especialidad solo filtra quién publica horarios.
- Cuotas: una reserva sin cotización genera sus dos cuotas (`al_reservar`, `al_terminar`). Si la reserva cuelga de una cotización aceptada, **no** genera cuotas propias: manda el plan de la cotización. La asesoría genera una cuota `al_reservar`.
- `proyecto_musical` lo abre el Administrador (o nace al aceptar una cotización); una reserva de grabación puede colgar de un proyecto (`id_proyecto` opcional). Las cuotas de posproducción cuelgan del proyecto.
- La simulación usa horas × tarifa de la sala según tipo (`grabacion`/`ensayo` pueden tener tarifa distinta) + servicios del catálogo elegidos. Los valores son datos, no reglas.
- Sin caducidad automática en v1: el Administrador cancela a mano una `Pre-reservada` o una asesoría `Pendiente de pago`. La caducidad automática y los reembolsos siguen en D-06 y D-11.

## 8. Lo que queda al constructor

- Redacción de cada archivo y orden de commits.
- Reparto de RN/RF entre archivos para respetar el límite de líneas.
- Cerrar la fila de cada D en [decisiones](../../00-proyecto/decisiones/README.md) y actualizar [stack](../../01-arquitectura/stack.md), [entornos](../../06-operacion/entornos.md) si aplica, y la hoja de ruta del índice.

## 9. Entregables

ADR-003..006 · `decisiones/README.md` · `stack.md` · `modelo-datos.md` · `reglas-negocio.md` · `estados-reserva.md` (+ estados de asesoría y pago) · `actores-roles.md` · flujos `registrar-reserva`, `ciclo-servicio`, `agendar-asesoria` (nuevo) · RF-02, RF-03, RF-04, RF-05, RF-11, RF-15 (nuevo) · `backend-hexagonal.md` (módulo `asesorias`) · `figma.md` (brecha) · índice `docs/README.md`.
