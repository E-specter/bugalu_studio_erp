---
id: pantalla-rf-15-mis-asesorias
titulo: Pantalla — Mis asesorías y su detalle (cliente, etapas B y C)
estado: borrador
depende_de: [RF-15, RF-18, RF-05, RF-17, ADR-015, pantalla-rf-04-mis-reservas, pantalla-rf-18-cancelar, pantalla-rf-18-reprogramar, pantalla-rf-18-creditos, pantalla-rf-15-pagar-y-reprogramar, diseno-brief, patron-tablas-y-tableros, patron-estados-sistema, comp-tabla, comp-panel, comp-etiqueta-tecnica, comp-indicador-estado, comp-aviso, comp-boton, comp-barra-acciones]
---

# Mis asesorías

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-08, CA-09 (lo que ve el cliente), CA-10, CA-11 (elección), CA-12 y CA-13 (lo que ve el cliente), CA-16, CA-17 |
| Actores | Artista/Cliente (las suyas). Profesional y Administrador abren el mismo detalle con sus bloques: [gestión](RF-15-gestion.md) y [cierre](RF-15-cierre.md) |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/asesorias/mias?ver=proximas\|historial` · `/app/asesorias/detalle?id=`. URL: `ver`, `id`, `aviso` |
| Isla | `<bugalu-asesorias vista="mias\|detalle">` (nueva) |

**Decisión del brief:** es [mis reservas](RF-04-mis-reservas.md) con otro objeto, con su propio destino ASESORÍAS (`messages-square`) tras RESERVAS ([navegación](../componentes/navegacion-lateral.md#variantes)). La política se compone con los paneles de [RF-18](RF-18-cancelar.md) **sin redefinirlos**: aquí solo van las diferencias de la asesoría.

## Recorrido

1. Entra por ASESORÍAS o desde "Ver mi asesoría" de [agendar](RF-15-agendar.md). Ve PRÓXIMAS (`Pendiente de pago`, `Confirmada`); HISTORIAL tiene `Realizada`, `Cancelada` y `No asistió`.
2. Abre una: estado, horario, profesional, lugar o enlace, precio y pago.
3. Según el estado: registra el pago, entra a la videollamada, cancela o reprograma con la política, elige tras una cancelación del estudio o abre su constancia.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Lista | `GET /asesorias/mias` → `[AsesoriaResumen]` | PRÓXIMAS por `inicio` ascendente; HISTORIAL descendente. Total "2 asesorías" |
| Asesoría | `GET /asesorias/{id}` → `Asesoria` | — |
| Estado | `estado` | [Etiqueta](../componentes/etiqueta-tecnica.md): PENDIENTE DE PAGO (Aviso) · CONFIRMADA y REALIZADA (Éxito) · CANCELADA y NO ASISTIÓ (Alerta) |
| Profesional | `profesional.{id, nombre, nombre_artistico}` | Artístico o nombre; enlace a su [perfil público](RF-15-perfil-publico.md) |
| Horario y duración | `inicio`, `fin`, `duracion` | `D MMM AAAA` + `HH:mm–HH:mm` · "1 h"; "Horario de Lima" |
| Modalidad | `modalidad` | "Presencial" · "Virtual (Google Meet)" |
| Lugar o enlace | `lugar` · `enlace` | Lugar tal cual (`white-space: pre-line`); enlace como enlace externo "Entrar a la videollamada"; `null` → etiqueta Aviso POR CONFIRMAR |
| Precio | `precio` con IGV | [Tabla](../componentes/tabla.md) Partidas como en R2 de [agendar](RF-15-agendar.md#composición) |
| Cuotas | `cuotas[].{hito, monto, estado, pagado, pagable}` | `al_reservar` → "Pago único"; `al_terminar` (penalización de nivel 2) → "Penalización por reprogramar · {p} %" con "Págala hasta 48 h después de tu asesoría." |
| Política | `cancelacion`, `reprogramaciones`, `eleccion_estudio`, `politica`, `devolucion` | Como en [cancelar](RF-18-cancelar.md#datos) |
| Constancia | `constancia_disponible`, `realizada_en` | Enlace a [constancia](RF-15-cierre.md#constancia) |
| Condiciones | `version_condiciones` | D1 CONDICIONES "versión 0.4.0", enlazada ([aceptaciones](RF-17-registro-y-aceptaciones.md#copy)) |

## Composición

**Lista:** [encabezado](../componentes/encabezado-pantalla.md) App con Primario "Agendar asesoría" (→ `/asesorias/`) → [etiquetas](../componentes/etiqueta-tecnica.md) Filtro PRÓXIMAS · HISTORIAL → [panel](../componentes/panel.md) `ASESORÍAS` + [tabla](../componentes/tabla.md) Directorio: ASESORÍA (folio y profesional debajo) · FECHA · MODALIDAD · ESTADO · "Ver asesoría {folio}" (Secundario como enlace). < `punto-quiebre-escritorio`, tarjetas.

**Detalle** (orden y adaptabilidad de [mis reservas](RF-04-mis-reservas.md#detalle): lateral primero en móvil):

| Región | Componente (variante) | Contenido |
|---|---|---|
| Principal | panel `D1 ASESORÍA {folio}` | `<dl>`: ESTADO · FECHA Y HORARIO · DURACIÓN · PROFESIONAL · MODALIDAD · LUGAR o ENLACE · CONDICIONES |
| Principal | panel `D2 PRECIO` · `D3 CUOTAS` | Los de mis reservas con los formatos de arriba |
| Principal | `D4 CANCELACIÓN` · `D5 REPROGRAMACIONES` | Los de [cancelar](RF-18-cancelar.md#composición), sin columna de TOTAL en D5 (el precio se conserva) |
| Lateral | [indicador](../componentes/indicador-estado.md) Barra | Tabla Estados |
| Lateral | [botón](../componentes/boton.md) | Un Primario según el momento: "Registrar pago" (cuota `pagable`) · "Entrar a la videollamada" (`Confirmada`, virtual, con enlace; `external-link`, pestaña nueva) · "Ver constancia" (`Realizada`) |
| Lateral | Párrafo de lugar | Presencial o virtual sin lugar o enlace: "{Profesional} y el estudio te confirmarán {el lugar / el enlace} antes de la cita. Te avisaremos por correo." Con lugar o enlace: "¿Necesitas cambiarlo? Escríbenos y lo coordinamos con {profesional}:" + contacto del estudio (`GET /contacto-estudio`; vacío → sin línea) |
| Lateral | "Reprogramar" · "Solicitar cancelación" | Las de [cancelar](RF-18-cancelar.md#composición) y [reprogramar](RF-18-reprogramar.md#entrada-desde-el-detalle), del dueño, en `Pendiente de pago` o `Confirmada` y **antes del inicio** (CA-10 c). Reprogramar va a [reprogramar](RF-15-pagar-y-reprogramar.md#reprogramar) |

**Diferencias de copy con RF-18** (el resto, tal cual):

| Texto de RF-18 | En la asesoría |
|---|---|
| Consecuencias, nivel 1 | "Todo lo que pagaste pasa a crédito para otra reserva o asesoría tuya, sin devolución en dinero. El horario se libera al momento y la cancelación no se puede deshacer." |
| Consecuencias, nivel 2 | "Se retiene una penalización del {p} % del total. El resto pasa a crédito para otra reserva o asesoría tuya, sin devolución. El horario se libera al momento y la cancelación no se puede deshacer." |
| Sin pagos | "…tendrás que agendarla de nuevo si sigue libre." |
| "Volver a la reserva" · `CANCELAR RESERVA {folio}` | "Volver a la asesoría" · `CANCELAR ASESORÍA {folio}` |
| Elección tras la cancelación del estudio | "Reprogramar sin costo": "Eliges otro horario libre de {profesional}. Mantienes el precio y lo que pagaste." Al pie, además: "¿Prefieres a otro profesional? Pide la devolución íntegra y agenda una asesoría nueva." |

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lista | Sin asesorías | Vacío: "Aún no tienes asesorías" + "Elige un profesional y agenda una orientación para tu proyecto." + Primario "Ver profesionales" |
| Lista | Filtro sin resultados | "No tienes asesorías próximas." / "Aún no hay asesorías en tu historial." + el otro filtro |
| Lista, detalle | Carga | Panel con "Cargando…", `aria-busy` |
| Detalle | `Pendiente de pago` | Barra Pendiente "PAGA ANTES DEL {vence_pago}" + plazo restante; con pago en validación, "PAGO EN VALIDACIÓN" y el texto de [mis reservas](RF-04-mis-reservas.md#estados) |
| Detalle | `Confirmada` | Barra Correcto "CONFIRMADA" + "Te esperamos el {D MMM}, a las {HH:mm}." Con lugar o enlace pendiente, debajo: "Lugar por confirmar" / "Enlace por confirmar" |
| Detalle | `Confirmada` y pasó `fin` | Barra Neutro "TERMINÓ" + "{Profesional} confirmará tu asistencia y te enviaremos la constancia por correo." |
| Detalle | `Realizada` | Barra Correcto "REALIZADA" + "Tu constancia de asistencia está lista." |
| Detalle | `No asistió` | Barra Problema "NO ASISTIÓ" + "No llegaste en los primeros {t} minutos. Lo pagado no se devuelve." Con excepción: D4 como en RF-18 y "{credito} pasaron a crédito, sin devolución." |
| Detalle | `Cancelada` | Los de [cancelar](RF-18-cancelar.md#estados); caducada: "Caducó sin pago el {vence_pago}. El horario se liberó." |
| Detalle | `eleccion_estudio = pendiente` | La [elección](RF-18-reprogramar.md#elección-tras-una-cancelación-del-estudio) con el copy de arriba |
| Detalle | `?aviso=` | `asesoria-cancelada`, `pago-registrado`, `pagado-con-credito`, `asesoria-reprogramada`, `devolucion-elegida`: los textos de RF-18 y RF-05 con "asesoría" en lugar de "reserva" (lista cerrada) |
| Todas | 401 · 404 · 503 · red · no JSON · sin JS | Como en [mis reservas](RF-04-mis-reservas.md#estados): "Tu sesión no es válida. Inicia sesión para ver tus asesorías." · `[404] ASESORÍA NO ENCONTRADA` "No encontramos esta asesoría." + "Volver a mis asesorías" (una ajena da 404, CA-16) |
| Todas | 403 (rol sin acceso) | `[403] SIN PERMISO` "Esta sección es para artistas." + "Volver al inicio" |

Permisos: el cliente no ve notas internas ni datos de otros clientes; no edita lugar ni enlace (CA-09).

## Créditos

Amplía [créditos](RF-18-creditos.md):


- ORIGEN con `origen.tipo = "asesoria"`: folio `A-…` enlazado a `/app/asesorias/detalle?id=`; tipo debajo con "· asesoría".
- Sin "Pedir devolución" en créditos nacidos de una asesoría (CA-10 a); en su lugar, en la celda: "Sin devolución: nació de una asesoría." Un 409 `devolucion_no_permitida` muestra ese texto en un aviso Información.

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Lista | Inicio / Asesorías · `[P5] ASESORÍAS / MIS ASESORÍAS` | MIS ASESORÍAS | Tus citas con profesionales, su estado y lo que falta pagar. |
| Detalle | Inicio / Asesorías / {folio} | ASESORÍA {folio} | Con {profesional} · {fecha}, {HH:mm}–{HH:mm} |

Columnas: ASESORÍA · FECHA · MODALIDAD · ESTADO.

## Accesibilidad

- `<h1>` del encabezado; cada panel `<section>` con `<h2>`; tabla con `<caption>` y folio como `<th scope="row">`. POR CONFIRMAR dice el estado en texto.
- "Entrar a la videollamada" lleva "(se abre en otra pestaña)" oculto. Región `role="status"` estable: "2 asesorías próximas" y cada resultado; al fallar una acción, foco al aviso.

## Preguntas

1. CA-09 dice que el cliente pide el cambio de lugar al profesional, pero no tiene su contacto. Proponemos el contacto del estudio (arriba). ¿Vale?
2. `AsesoriaResumen` no trae `vence_pago` ni si falta lugar o enlace: la lista no puede decir "Paga antes del…" ni POR CONFIRMAR. ¿Se suman?
