---
id: pantalla-rf-03-calendario
titulo: Pantalla — Calendario de sala (público, cliente y personal)
estado: borrador
depende_de: [RF-03, RF-04, RF-06, ADR-009, ADR-010, diseno-brief, patron-estructura-app, patron-estados-sistema, patron-tablas-y-tableros, comp-calendario, comp-tabla, comp-aviso, comp-etiqueta-tecnica]
---

# Calendario de sala

| Campo | Valor |
|---|---|
| Requerimiento | [RF-03](../../03-requerimientos/RF-03.md): CA-05, CA-06, CA-08, CA-09, CA-11; [RF-04](../../03-requerimientos/RF-04.md): CA-08; [RF-06](../../03-requerimientos/RF-06.md): CA-05 |
| Actores | Visitante y Artista/Cliente (`/reservar`); Personal interno y Administrador (`/app/agenda`) |
| Estructura | Flujo en `/reservar` (paso 01 de [reservar](RF-04-reservar.md)); App en `/app/agenda` ([estructura de app](../patrones/estructura-app.md)) |
| Ruta | `/reservar` y `/app/agenda`. URL: `vista` (`semana` por defecto, `mes`; `lista` solo en la agenda), `fecha` (`AAAA-MM-DD`), `sala` (solo si hay más de una) |
| Isla | [`<bugalu-calendario>`](../componentes/calendario.md): `modo="reserva"` en `/reservar`, `modo="personal"` en `/app/agenda` |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)); se extiende el "Selector de agenda" (`141:29060`) |

Esta spec fija el bloque del calendario en los dos contextos. El resto del paso 01 (duración, resumen, continuar) está en [reservar](RF-04-reservar.md).

## Recorrido

1. **Visitante o cliente** llega a `/reservar` desde "Reservar" de la landing, desde "Reservar sala" de [mis reservas](RF-04-mis-reservas.md) o por un enlace compartido. Ve la semana de `fecha` o la actual.
2. Pasa de semana con "Anterior" / "Siguiente", vuelve con "Esta semana" o cambia a MES; en el mes, un día abre su semana.
3. Elige una media hora libre: sigue el paso 01 de [reservar](RF-04-reservar.md). Con sesión, sus reservas se ven como TU RESERVA y abren su detalle.
4. **Personal y Administrador** entran por "AGENDA" (`calendar`). Ven quién reservó, qué servicio y en qué estado; cada reserva abre `/app/reservas/detalle?id=` ([mis reservas](RF-04-mis-reservas.md#detalle)). LISTA muestra el mismo periodo como tabla.
5. Administrador ante una semana sin franjas: "Publicar franjas de esta semana" lleva a [franjas](RF-03-franjas.md) con `?semana=`.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Sala | `GET /salas` → `Sala.nombre` | Una sola: [etiqueta](../componentes/etiqueta-tecnica.md) Neutra "SALA · LA MOLINA"; varias: [campo](../componentes/campo.md) Selector SALA |
| Periodo | `fecha` → semana de lunes a domingo o mes de 6 semanas (42 días), hora de Lima | "SEMANA DEL 16 AL 22 NOV 2026" · cruza mes: "SEMANA DEL 30 NOV AL 6 DIC 2026" · cruza año: "SEMANA DEL 28 DIC 2026 AL 3 ENE 2027" (cada extremo con su año) · "NOVIEMBRE 2026". Igual en [franjas](RF-03-franjas.md) |
| Franjas, ocupados, cierres | `GET /disponibilidad?sala=&desde=&hasta=` → `franjas`, `ocupados[].{inicio, fin, propia}`, `cierres[].{inicio, fin, motivo}` | Estados de la [ficha](../componentes/calendario.md#estados-de-la-media-hora). `ocupados` ya incluye el buffer de 30 min |
| Horas libres por día | `dias[].{fecha, minutos_libres}` | [Duración de reserva](../patrones/estructura-app.md#formato-de-datos) + "libres": "3 h 30 min libres"; 0 → "Sin horas libres" |
| Horas libres del periodo | Suma de `dias[].minutos_libres` | Solo en el anuncio |
| Tus reservas (cliente) | `GET /reservas/mias`, casadas con `ocupados[].propia` por `inicio` | TU RESERVA + `folio` |
| Detalle (personal) | `ocupados[].detalle.{id_reserva, cliente, servicio, estado, pago_por_validar}` | Cliente tal cual; servicio; [etiqueta](../componentes/etiqueta-tecnica.md) según [estados de reserva](../../02-dominio/estados-reserva.md) (PRE-RESERVADA, CONFIRMADA, EN CURSO, FINALIZADA). Con `pago_por_validar`, en lugar de la etiqueta de estado: Aviso PAGO POR VALIDAR (RN-23: la `Pre-reservada` no caduca ni avanza) |
| Lista (personal) | `GET /reservas?desde=&hasta=` → `[Reserva]` | `folio`, `inicio`–`fin` (`D MMM, HH:mm`–`HH:mm`), `cliente`, `servicio`, `estado`. En ESTADO, debajo de la etiqueta: PAGO POR VALIDAR (Aviso) si `pago_por_validar`; "Resto: S/ 225,00" si la cuota `al_terminar` sigue `pendiente` en `En curso` o `Finalizada` |

## Composición

| Contexto | Región | Componente (variante) | Contenido |
|---|---|---|---|
| `/reservar` | Principal | [panel](../componentes/panel.md) `01 ELIGE TU HORARIO` + [calendario](../componentes/calendario.md) Reserva | Barra del periodo, tabla, leyenda; sala en la ranura `acciones` |
| `/app/agenda` | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título y descripción; sin acción principal |
| `/app/agenda` | Principal | panel `AGENDA` + calendario Personal | Igual; en LISTA, [tabla](../componentes/tabla.md) Directorio en lugar de la cuadrícula |

Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md) (Lista), [estados del sistema](../patrones/estados-sistema.md). Adaptabilidad: la de la [ficha](../componentes/calendario.md#adaptabilidad); en `/app/agenda`, < `punto-quiebre-escritorio` sin `vista` en la URL abre LISTA, como el tablero ([tablas y tableros](../patrones/tablas-y-tableros.md#tablero-de-producción)).

## Estados

| Situación | Forma y texto |
|---|---|
| Carga | La de la ficha: "Cargando semana…" / "Cargando mes…" |
| Periodo sin franjas (`franjas` vacío) | Vacío en el panel, **bajo la barra del periodo** (sigue visible para moverse de semana; decisión TAREA-RF04-6): "Aún no hay horarios publicados" + "Publicamos la agenda semana a semana. Mira la siguiente semana o vuelve pronto." + "Ver semana siguiente" (Secundario). Administrador: además "Publicar franjas de esta semana" (Secundario) |
| Con franjas y sin horas libres | No es vacío: se ve la cuadrícula; anuncio "… 0 horas libres" |
| Lista sin reservas | "No hay reservas en este periodo." Sin acción |
| `?fecha` inválida o 422 `rango_invalido` | Muestra la semana actual + [aviso](../componentes/aviso.md) Información "La fecha del enlace no es válida. Te mostramos esta semana." |
| 404 (sala) | Aviso Error "No encontramos esa sala." + "Ver la sala de La Molina" (enlace sin `sala`) |
| 401 en `/reservar` (sesión caducada) | Se repite la consulta sin sesión + aviso Información "Tu sesión caducó. Inicia sesión para ver tus reservas en el calendario." + "Iniciar sesión" (`?volver=` con la URL actual) |
| 401 en `/app/agenda` | Aviso "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=`) |
| 403 (cliente en `/app/agenda` o Lista) | En lugar del bloque: `[403] SIN PERMISO` "La agenda es solo para el equipo del estudio." + "Volver al inicio" |
| 503 | Aviso Error "El calendario no responde. Inténtalo de nuevo en unos minutos." + "Reintentar" |
| Red caída | Aviso Error "Sin conexión. Revisa tu red y vuelve a intentarlo." + "Reintentar" |
| No JSON u otro | Aviso Error "Algo salió mal al cargar el calendario." + "Reintentar" |
| Sin JS | `<noscript>`: aviso Información "El calendario necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Tras "Reintentar", el foco va al título del panel. Permisos: el visitante y el cliente nunca reciben datos de otros (`detalle` no llega); "AGENDA" solo se pinta para `personal` y `administrador`; "Publicar franjas de esta semana", solo para `administrador`.

## Copy

| Elemento | Texto |
|---|---|
| Agenda: ruta e índice | Inicio / Agenda · `[R1] SALA / AGENDA` |
| Agenda: título y descripción | AGENDA DE SALA · "Reservas y horas libres de la sala. Abre una reserva para ver su detalle." |
| Periodo | "Semana anterior" · "Semana siguiente" · "Esta semana"; "Mes anterior" · "Mes siguiente" · "Este mes"; bajo el título "Horario de Lima" |
| Vistas | SEMANA · MES · LISTA |
| Leyenda | LIBRE · OCUPADO · TU RESERVA · CERRADO · PASADO · NO RESERVABLE (solo las presentes) |
| Columnas de Lista | FOLIO · FECHA · CLIENTE · SERVICIO · ESTADO; acción "Ver reserva {folio}" |
| Anuncio | "Semana del 16 al 22 nov 2026: 32 horas libres." · "Noviembre 2026: 120 horas libres." · Lista: "8 reservas en este periodo." |

## Accesibilidad

- `/app/agenda`: `<h1>` del encabezado; el panel es `<section>` con `<h2>` = título del periodo. En `/reservar`, el `<h1>` es el del paso ([reservar](RF-04-reservar.md#accesibilidad)).
- Teclado, nombres y anuncios: los de la [ficha](../componentes/calendario.md#accesibilidad). Orden de foco: sala → periodo (anterior, esta semana, siguiente) → vistas → cuadrícula → leyenda (sin foco).
- La Lista sigue la [tabla](../componentes/tabla.md#accesibilidad): `<caption>` con el periodo, folio como `<th scope="row">`.

## Ampliación aforo (RF-03 CA-10 a CA-13)

| Dato | Origen | Formato |
|---|---|---|
| Aforo de la sala | `GET /salas` (el mismo de SALA) → `aforo`, `itse.certificado` de la sala mostrada | "Aforo máximo: 6 personas · Certificado ITSE 0123-2026" (1 → "1 persona"; certificado tal cual) |

- **Dónde:** `<p>` de ayuda del panel ([anatomía](../componentes/panel.md#anatomía)), junto a la sala, en `fuente-tamano-pequeno` y `color-texto-secundario`; en los dos contextos (`/reservar` y `/app/agenda`). Con varias salas cambia con el selector SALA. En 390 va bajo la sala y se parte en líneas, sin truncar; en 1440, en una línea.
- **Sin aforo** (`aforo: null`): no se pinta la línea ni su hueco. Con aforo y sin `itse` (CA-10 no lo permite): solo "Aforo máximo: 6 personas".
- **Decisión del brief (vencimiento):** el público y el personal ven el número del certificado, nunca su fecha de vencimiento ni la palabra "vigente": la línea es la misma con el certificado vigente o vencido, así nunca afirma una vigencia que no hay. Los avisos de vencimiento son del Administrador, en [franjas](RF-03-franjas.md#ampliación-aforo-rf-03-ca-10-a-ca-13).
- **Estados:** mientras carga `GET /salas`, sin línea; si falla, rigen 503, red y no JSON de [Estados](#estados). La línea no tiene estados propios.
- **Accesibilidad:** texto estático, leído tras la sala y antes del periodo; no se anuncia con `aria-live`. ITSE en `<abbr title="Inspección Técnica de Seguridad en Edificaciones">`.

## Pendientes

- **leader / dev-backend:** `Disponibilidad` no dice desde y hasta cuándo se puede reservar. Proponemos `limites: {desde, hasta}` para marcar NO RESERVABLE por anticipación en cada media hora. Sin él, solo se marca lo pasado y el 422 de `POST /reservas` cubre el resto.
- **dev-backend:** `ocupados[].detalle` no trae `pago_por_validar` ([RF-06](../../03-requerimientos/RF-06.md) CA-05 lo pide en la agenda); propuesta: añadirlo. Sin él, la cuadrícula no lo marca y solo lo muestra LISTA. El saldo no va en la cuadrícula (no cabe): está en LISTA y en el detalle.
- **leader:** destinos de navegación nuevos: AGENDA (`calendar`) para personal y Administrador; registrar el modo `personal` y la vista `lista` de `<bugalu-calendario>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
- **Ampliada por RF-18:** etiqueta NO ASISTIÓ en la cuadrícula y en LISTA, y la acción "Marcar no asistió · {folio}" en LISTA ([acciones del Administrador](RF-18-acciones-administrador.md#composición)).
