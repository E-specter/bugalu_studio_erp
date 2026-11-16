---
id: pantalla-rf-03-calendario
titulo: Pantalla — Calendario de sala (público, cliente y personal)
estado: borrador
depende_de: [RF-03, RF-04, ADR-009, diseno-brief, patron-estructura-app, patron-estados-sistema, patron-tablas-y-tableros, comp-calendario, comp-tabla, comp-aviso, comp-etiqueta-tecnica]
---

# Calendario de sala

| Campo | Valor |
|---|---|
| Requerimiento | [RF-03](../../03-requerimientos/RF-03.md): CA-05, CA-06, CA-08, CA-09; [RF-04](../../03-requerimientos/RF-04.md): CA-08 |
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
| Periodo | `fecha` → semana de lunes a domingo o mes de 6 semanas (42 días), hora de Lima | "SEMANA DEL 16 AL 22 NOV 2026" · "NOVIEMBRE 2026" |
| Franjas, ocupados, cierres | `GET /disponibilidad?sala=&desde=&hasta=` → `franjas`, `ocupados[].{inicio, fin, propia}`, `cierres[].{inicio, fin, motivo}` | Estados de la [ficha](../componentes/calendario.md#estados-de-la-media-hora). `ocupados` ya incluye el buffer de 30 min |
| Horas libres por día | `dias[].{fecha, minutos_libres}` | [Duración de reserva](../patrones/estructura-app.md#formato-de-datos) + "libres": "3 h 30 min libres"; 0 → "Sin horas libres" |
| Horas libres del periodo | Suma de `dias[].minutos_libres` | Solo en el anuncio |
| Tus reservas (cliente) | `GET /reservas/mias`, casadas con `ocupados[].propia` por `inicio` | TU RESERVA + `folio` |
| Detalle (personal) | `ocupados[].detalle.{id_reserva, cliente, servicio, estado}` | Cliente tal cual; servicio; [etiqueta](../componentes/etiqueta-tecnica.md) según [estados de reserva](../../02-dominio/estados-reserva.md) |
| Lista (personal) | `GET /reservas?desde=&hasta=` → `[Reserva]` | `folio`, `inicio`–`fin` (`D MMM, HH:mm`–`HH:mm`), `cliente`, `servicio`, `estado` |

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
| Periodo sin franjas (`franjas` vacío) | Vacío en el panel: "Aún no hay horarios publicados" + "Publicamos la agenda semana a semana. Mira la siguiente semana o vuelve pronto." + "Ver semana siguiente" (Secundario). Administrador: además "Publicar franjas de esta semana" (Secundario) |
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
| Leyenda | LIBRE · OCUPADO · TU RESERVA · CERRADO · NO RESERVABLE (solo las presentes) |
| Columnas de Lista | FOLIO · FECHA · CLIENTE · SERVICIO · ESTADO; acción "Ver reserva {folio}" |
| Anuncio | "Semana del 16 al 22 nov 2026: 32 horas libres." · "Noviembre 2026: 120 horas libres." · Lista: "8 reservas en este periodo." |

## Accesibilidad

- `/app/agenda`: `<h1>` del encabezado; el panel es `<section>` con `<h2>` = título del periodo. En `/reservar`, el `<h1>` es el del paso ([reservar](RF-04-reservar.md#accesibilidad)).
- Teclado, nombres y anuncios: los de la [ficha](../componentes/calendario.md#accesibilidad). Orden de foco: sala → periodo (anterior, esta semana, siguiente) → vistas → cuadrícula → leyenda (sin foco).
- La Lista sigue la [tabla](../componentes/tabla.md#accesibilidad): `<caption>` con el periodo, folio como `<th scope="row">`.

## Pendientes

- **leader / dev-backend:** `Disponibilidad` no dice desde y hasta cuándo se puede reservar. Proponemos `limites: {desde, hasta}` para marcar NO RESERVABLE por anticipación en cada media hora. Sin él, solo se marca lo pasado y el 422 de `POST /reservas` cubre el resto.
- **leader:** destinos de navegación nuevos: AGENDA (`calendar`) para personal y Administrador; registrar el modo `personal` y la vista `lista` de `<bugalu-calendario>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
