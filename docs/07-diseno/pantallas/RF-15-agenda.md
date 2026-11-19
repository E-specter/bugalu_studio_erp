---
id: pantalla-rf-15-agenda
titulo: Pantalla — Asesorías agendadas (profesional y Administrador, etapas B y C)
estado: borrador
depende_de: [RF-15, RF-18, pantalla-rf-15-gestion, pantalla-rf-15-cierre, pantalla-rf-15-administracion, pantalla-rf-04-mis-reservas, diseno-brief, patron-tablas-y-tableros, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-etiqueta-tecnica, comp-boton, comp-aviso]
---

# Asesorías agendadas

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-12 ("Por cerrar"), CA-16, CA-17 (Mis asesorías del profesional con "Por cerrar"; el Administrador, todas) |
| Actores | Profesional artístico (las suyas); Administrador (todas). El personal no ve asesorías (CA-16) |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/asesorias/agenda?ver=proximas\|por_cerrar\|historial&mes=AAAA-MM&profesional=` (`mes` solo en HISTORIAL; `profesional` solo para el Administrador) |
| Isla | `<bugalu-asesorias vista="agenda">` (la de [mis asesorías](RF-15-mis-asesorias.md)) |

**Decisión del brief: ruta nueva, sin mover la etapa A.** El profesional suma el destino ASESORÍAS (`messages-square`) → esta ruta ([navegación](../componentes/navegacion-lateral.md#variantes)). El Administrador sigue entrando por ASESORÍAS a [profesionales](RF-15-administracion.md#profesionales), cuyo encabezado suma, primero, Secundario "Asesorías agendadas" → esta ruta (con "{n} por cerrar" en el nombre si hay). Así no cambia ninguna ruta ya probada.

## Recorrido

1. Llega por su destino (profesional) o desde profesionales (Administrador). Ve PRÓXIMAS.
2. Si hay asesorías sin cerrar, el aviso de arriba lo lleva a POR CERRAR.
3. Abre una con "Ver asesoría {folio}" → [detalle](RF-15-gestion.md): lugar o enlace, cliente, cancelación, cierre y notas.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| PRÓXIMAS | `GET /asesorias?desde={ahora}` (+ `id_profesional`), solo `pre_reservada` y `confirmada` | Por `inicio` ascendente; total "4 asesorías próximas" |
| POR CERRAR | `GET /asesorias?por_cerrar=true` | Por `inicio` ascendente (la más antigua arriba) |
| HISTORIAL | `GET /asesorias?desde={1.º del mes}&hasta={fin del mes}`, estados `realizada`, `cancelada`, `no_asistio` | Por `inicio` descendente; barra del mes "Mes anterior" · "Este mes" · "Mes siguiente" como la del [calendario](../componentes/calendario.md#anatomía) |
| Profesionales (Administrador) | `GET /profesionales` | [Campo](../componentes/campo.md) Selector PROFESIONAL: "Todos" + por nombre |
| Fila | `AsesoriaResumen.{folio, estado, inicio, fin, modalidad, profesional, cliente, por_cerrar}` | Folio en `fuente-familia-tecnica`; `D MMM AAAA` + `HH:mm–HH:mm`; cliente: artístico o nombre |
| Estado | `estado` + `por_cerrar` | Etiquetas de [mis asesorías](RF-15-mis-asesorias.md#datos); con `por_cerrar`, además Aviso POR CERRAR |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción (Copy). Administrador: `acciones` "Volver a profesionales" |
| Avisos | [aviso](../componentes/aviso.md) Aviso | Fuera de POR CERRAR, si hay alguna: "Tienes {n} asesorías por cerrar. Marca si se realizaron o si el cliente no asistió." + "Ver por cerrar" (Administrador: "Hay {n} asesorías por cerrar…") |
| Controles | [etiquetas](../componentes/etiqueta-tecnica.md) Filtro PRÓXIMAS · POR CERRAR ({n}) · HISTORIAL; Administrador: Selector PROFESIONAL en la misma fila (`<form method="get">` que cambia `profesional`) | El filtro aplicado con `aria-current="true"` |
| Principal | [panel](../componentes/panel.md) `ASESORÍAS` + [tabla](../componentes/tabla.md) Directorio | ASESORÍA (folio; modalidad debajo) · FECHA · CLIENTE · PROFESIONAL (solo Administrador) · ESTADO · "Ver asesoría {folio}" (Secundario como enlace; en POR CERRAR, "Cerrar asesoría {folio}" al detalle con `?accion=cerrar`) |

Sin lateral. Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md). Adaptabilidad: 1440, tabla completa; < `punto-quiebre-escritorio` (390), tarjetas con `<dl>` (folio como título, FECHA, CLIENTE, ESTADO y la acción a ancho completo, alto `medida-control-tactil`); el Selector baja bajo los filtros.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lista | Sin asesorías (PRÓXIMAS, sin filtro de profesional) | Profesional: "Aún no tienes asesorías agendadas" + "Cuando un artista agende en tus horarios, la verás aquí." + Secundario "Mis horarios". Administrador: "Aún no hay asesorías agendadas" |
| Lista | POR CERRAR vacío | "No tienes asesorías por cerrar." (éxito tranquilo, sin acción) |
| Lista | HISTORIAL vacío | "No hay asesorías en {mes}." + "Mes anterior" |
| Lista | Con PROFESIONAL elegido y vacío | "{Nombre} no tiene asesorías {próximas / por cerrar / en {mes}}." + "Ver todos" |
| Lista | Carga | Panel con "Cargando…", `aria-busy` |
| Todas | `ver`, `mes` o `profesional` inválidos, o 422 | Se aplica el valor por defecto + aviso Información "El filtro del enlace no es válido. Te mostramos las próximas." |
| Todas | 401 | "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=`) |
| Todas | 403 | `[403] SIN PERMISO` "Esta sección es para profesionales de asesoría y el Administrador." + "Volver al inicio" |
| Todas | 503 · red · no JSON | "El servicio no responde. Inténtalo de nuevo en unos minutos." · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal. Inténtalo de nuevo." + "Reintentar" |
| Todas | Sin JS | `<noscript>`: "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: el profesional nunca ve el Selector ni asesorías ajenas (la API filtra; CA-16); no ve pagos ni montos.

## Copy

| Vista | Ruta e índice | Título | Descripción |
|---|---|---|---|
| Profesional | Inicio / Asesorías · `[E3] ASESORÍAS / AGENDA` | MIS ASESORÍAS | Tus citas agendadas, el lugar o enlace de cada una y las que te falta cerrar. |
| Administrador | Inicio / Asesorías / Agendadas · `[A15] ASESORÍAS / AGENDA` | ASESORÍAS AGENDADAS | Todas las citas de asesoría: lugar, cancelaciones y cierre. |

Columnas: ASESORÍA · FECHA · CLIENTE · PROFESIONAL · ESTADO. Filtros: PRÓXIMAS · POR CERRAR · HISTORIAL. Modalidad: "Presencial" · "Virtual".

## Accesibilidad

- `<h1>` del encabezado; panel `<section>` con `<h2>`; tabla con `<caption>` ("Asesorías próximas") y folio como `<th scope="row">`.
- Filtros como enlaces; el Selector tiene `<label>` visible y botón "Filtrar" (sin envío al cambiar). POR CERRAR dice el estado en texto y su número va en el nombre del filtro.
- Región `role="status"` estable: "4 asesorías próximas" al cargar o cambiar de filtro.

## Pendientes

- **leader / dev-backend:** `GET /asesorias?estado=` ¿admite varios estados (`estado=realizada,cancelada,no_asistio`)? Si no, HISTORIAL filtra en la isla lo que trae el mes.
- **leader / dev-backend:** ¿`por_cerrar` empieza en el `inicio` o en el `fin`? La spec asume el `fin` (la asesoría aún puede estar en curso).
- **dev-frontend:** con dos destinos ASESORÍAS para roles distintos, el destino actual se calcula entre los visibles para el rol (hoy, el más largo de todos).
