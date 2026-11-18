---
id: pantalla-rf-15-directorio
titulo: Pantalla — Directorio público de profesionales (etapa A)
estado: borrador
depende_de: [RF-15, RF-20, diseno-brief, patron-estructura-app, patron-estados-sistema, comp-tarjeta-profesional, comp-avatar, comp-etiqueta-tecnica, comp-aviso, comp-boton, comp-pie-publico]
---

# Directorio de profesionales

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-02 (filtro), CA-03 (lo público), CA-16 (lectura anónima), CA-17 (directorio) |
| Actores | Visitante y Artista/Cliente, con o sin sesión (la vista es la misma) |
| Estructura | Landing (`LayoutPublico`, [estructura de app](../patrones/estructura-app.md#landing)), con [pie público](../componentes/pie-publico.md) Completa |
| Ruta | `/asesorias/`. URL: `especialidad` (id; sin él, todas) |
| Isla | `<bugalu-directorio vista="lista">` (nueva; la vista `perfil` es el [perfil público](RF-15-perfil-publico.md)) |
| Origen Figma | Ninguno ([brecha](../figma.md#brecha-detectada)); tono de la sección "servicios" de la landing |

## Recorrido

1. Llega por un enlace a `/asesorias/` (portada, redes, un enlace compartido; ver Pendientes) y ve a todos los profesionales publicados.
2. Filtra por especialidad con un clic: el filtro cambia la URL (`?especialidad=`) y se puede compartir. "Todas" lo quita.
3. Abre una tarjeta y va al [perfil público](RF-15-perfil-publico.md) (`/asesorias/profesional/?id=`), donde ve precios y horarios.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Especialidades del filtro | `GET /especialidades-asesoria` → `[Especialidad]` (solo activas) | Tal cual, en el orden de la API |
| Profesionales | `GET /profesionales?especialidad=` → `[ProfesionalResumen]` (solo publicados) | Una [tarjeta de profesional](../componentes/tarjeta-profesional.md) cada uno, en el orden de la API |
| Nombre que se muestra | `nombre_artistico` o, si es `null`, `nombre` | Tal cual; con nombre artístico, el nombre completo debajo |
| Foto | `foto_url` | [Avatar](../componentes/avatar.md) Miniatura; `null` → iniciales |
| Especialidades | `especialidades[].nombre` | [Etiqueta](../componentes/etiqueta-tecnica.md) Neutra |
| Precios | `duraciones[].{minutos, precio}` | "30 MIN" o "1 H" · `S/ 80,00` ([formato](../patrones/estructura-app.md#formato-de-datos)) |
| Nota de IGV | `duraciones[0].igv.incluido` y `porcentaje` | "Precios en soles con IGV incluido (18 %)." · sin incluir: "Precios en soles; el IGV (18 %) se suma al total." El navegador no calcula nada |
| Total | Largo de la lista | "6 profesionales" · "1 profesional" (solo en el anuncio y bajo los filtros) |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Cabecera | La de `LayoutPublico` | Logotipo enlazado a inicio |
| Encabezado | Sección de la landing: índice `[ 01 ] ASESORÍAS` (`fuente-familia-tecnica`), `<h1>` (`fuente-familia-titulo`, `fuente-tamano-titulo-lg`) y descripción (`fuente-tamano-lectura`, `color-texto-cuerpo`, ancho `medida-linea-lectura`) | Copy |
| Controles | [Etiquetas](../componentes/etiqueta-tecnica.md) Filtro en una `<ul>` que se ajusta (hueco `espacio-2`) | "Todas" + una por especialidad; enlaces `?especialidad={id}`; la aplicada en Activa + `check` |
| Controles | Línea técnica bajo los filtros | Total + nota de IGV, `fuente-tamano-pequeno`, `color-texto-secundario` |
| Principal | Lista `<ul>` de [tarjetas de profesional](../componentes/tarjeta-profesional.md) | Retícula de la ficha (1, 2 o 3 columnas) |
| Pie | [Pie público](../componentes/pie-publico.md) Completa | — |

Separación: encabezado → controles `espacio-8`; controles → lista `espacio-6`. Sin acción primaria en la etapa A: el directorio solo lleva a los perfiles (el "Agendar" vive en el perfil). Sin búsqueda ni paginación: el estudio tiene pocos profesionales y el contrato no las ofrece. Adaptabilidad: la de la [ficha](../componentes/tarjeta-profesional.md#anatomía); los filtros se ajustan en varias líneas, nunca con desplazamiento horizontal.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Lista | Carga | El espacio de la lista con "Cargando profesionales…" (`fuente-familia-tecnica`), `aria-busy="true"`; los filtros ya visibles si llegaron |
| Lista | Vacío (sin filtro, nadie publicado) | Panel de vacío ([estados](../patrones/estados-sistema.md#vacío)): "Aún no hay profesionales publicados" + "Estamos preparando el equipo de asesorías. Vuelve pronto." Sin acción; sin fila de filtros |
| Lista | Sin resultados del filtro | "Nadie ofrece {especialidad} por ahora." + Secundario "Ver todas las especialidades" (`/asesorias/`). Los filtros siguen |
| Filtros | Catálogo vacío o error al cargarlo | No se pintan los filtros; la lista carga igual (un fallo del filtro no tapa el directorio) |
| Todo | `?especialidad=` desconocida, inactiva o 422 | Se muestra todo + [aviso](../componentes/aviso.md) Información "Esa especialidad ya no está disponible. Te mostramos todos los profesionales." y la URL pasa a `/asesorias/` con `history.replaceState` |
| Lista | 503 | Aviso Error "El directorio no responde. Inténtalo de nuevo en unos minutos." + "Reintentar" |
| Lista | Red caída · no JSON | "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal al cargar el directorio." + "Reintentar" |
| Foto | No carga | Iniciales ([avatar](../componentes/avatar.md#estados)); sin aviso |
| Todo | Sin JS | `<noscript>`: aviso Información "El directorio necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: la API solo devuelve perfiles publicados y especialidades activas a quien no es Administrador; un Administrador con sesión ve aquí lo mismo que el público (la isla no envía el token: el directorio es la vista del cliente). Ningún dato de clientes aparece (CA-16).

## Copy

| Elemento | Texto |
|---|---|
| Título de la pestaña | Asesorías · Bugalú Studio |
| Índice y título | `[ 01 ] ASESORÍAS` · PROFESIONALES DEL ESTUDIO |
| Descripción | Conversa con un profesional antes de producir: te orienta, escucha tu idea y te ayuda a definir el siguiente paso. Precio fijo, presencial o por videollamada. |
| Filtro | `<nav>` "Filtrar por especialidad" (oculto) · "Todas" · {especialidad} |
| Tarjeta | La de la [ficha](../componentes/tarjeta-profesional.md): "Ver perfil" |
| Anuncio | "6 profesionales." · "2 profesionales en Producción." · "Nadie ofrece Coros por ahora." |

## Accesibilidad

- `<main>` con un `<h1>`; cada tarjeta, `<h2>` con el nombre. La lista es `<ul>` con `aria-label="Profesionales"`.
- Filtros: `<nav aria-label="Filtrar por especialidad">` con enlaces; el aplicado con `aria-current="true"` ([etiqueta](../componentes/etiqueta-tecnica.md#estados)). La isla intercepta el clic (`history.pushState` y carga), el foco se queda en el filtro pulsado y la región `role="status"` anuncia el resultado. Con la URL copiada se abre el mismo filtro.
- Orden de foco: logotipo → filtros → tarjetas (una parada por tarjeta) → pie.
- Tras "Reintentar", el foco va al `<h1>`.

## Pendientes

- **leader:** entrada al directorio: la portada aún no tiene enlaces; proponemos "Asesorías" en la sección de servicios cuando se construya y, para el cliente, un destino en la etapa B (con "Mis asesorías").
- **leader / dev-backend:** forma de `duraciones[].igv`; proponemos la de `Simulacion.impuesto` de [RF-20](../../03-requerimientos/RF-20.md) (`{porcentaje, incluido, base, monto}`). Orden de `GET /profesionales`: proponemos por nombre que se muestra.
