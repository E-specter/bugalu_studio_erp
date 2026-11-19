---
id: pantalla-rf-15-perfil-publico
titulo: Pantalla — Perfil público del profesional y su disponibilidad (etapa A)
estado: borrador
depende_de: [RF-15, RF-17, RF-20, pantalla-rf-15-directorio, pantalla-rf-03-calendario, diseno-brief, patron-estructura-app, patron-estados-sistema, comp-avatar, comp-etiqueta-tecnica, comp-tabla, comp-calendario, comp-boton, comp-aviso, comp-pie-publico]
---

# Perfil público del profesional

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-03, CA-04 (precio con IGV), CA-05 (disponibilidad), CA-16, CA-17 (perfil con "Agendar") |
| Actores | Visitante y Artista/Cliente (con sesión ve sus propias asesorías marcadas) |
| Estructura | Landing (`LayoutPublico`), con [pie público](../componentes/pie-publico.md) Completa |
| Ruta | `/asesorias/profesional/?id=`. URL: `id`, `vista` (`semana` por defecto, `mes`), `fecha` (`AAAA-MM-DD`) |
| Isla | `<bugalu-directorio vista="perfil">` + [`<bugalu-calendario modo="asesoria">`](../componentes/calendario.md#modos) |

## Recorrido

1. Llega desde una tarjeta del [directorio](RF-15-directorio.md) o por un enlace compartido.
2. Lee quién es, qué hace, cuánto cuesta cada duración (con su IGV) y cuándo tiene horas libres; cambia de semana o pasa a MES.
3. **Etapa A:** "Agendar asesoría" se ve pero no agenda (abajo). Vuelve con "Volver al directorio".

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Perfil | `GET /profesionales/{id}` → `Profesional` | — |
| Nombre | `nombre_artistico` o `nombre`; con artístico, `nombre` debajo | Tal cual |
| Foto | `foto_url` | [Avatar](../componentes/avatar.md) Retrato; `null` → iniciales |
| Especialidades | `especialidades[].nombre` | [Etiquetas](../componentes/etiqueta-tecnica.md) Neutra |
| Presentación | `presentacion` (≤ 600) | Prosa tal cual, saltos de línea respetados (`white-space: pre-line`), sin HTML. Vacía: no se pinta |
| Redes | `redes[].{red, valor}` (≤ 5) | `<ul>`: "Instagram · @usuario" (red con su nombre: Instagram, TikTok, Facebook, YouTube, Spotify, Otra). `valor` que empieza por `https://` → enlace a él; si no, texto sin enlace (no se inventan direcciones) |
| Duraciones | `duraciones[].{minutos, precio, igv}` | Tabla (abajo); importe `S/ 80,00`, porcentaje "18 %" |
| Disponibilidad | `GET /profesionales/{id}/disponibilidad?desde=&hasta=` → `DisponibilidadProfesional` | [Calendario](../componentes/calendario.md) modo Asesoría |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Arriba | Enlace con icono `chevron-left` | "Volver al directorio" (`/asesorias/`) |
| Identidad | Dos columnas ≥ `punto-quiebre-escritorio` (lateral `medida-columna-lateral` a la izquierda + resto, hueco `espacio-8`); una columna debajo | Izquierda: avatar Retrato. Derecha: índice `PROFESIONAL` (`fuente-familia-tecnica`, `fuente-tamano-micro`), `<h1>` nombre (`fuente-familia-titulo`, `fuente-tamano-titulo-lg`), nombre completo (`color-texto-secundario`), etiquetas de especialidad, presentación (`fuente-tamano-lectura`, `color-texto-cuerpo`, `medida-linea-lectura`), `<ul>` de redes y "Agendar asesoría" |
| `[ 01 ]` | Sección `<h2>` DURACIONES Y PRECIOS + [tabla](../componentes/tabla.md) Partidas, sin pie | DURACIÓN · PRECIO · INCLUYE IGV ({p} %); con `igv.incluido = false`: DURACIÓN · PRECIO SIN IGV (`base`) · IGV ({p} %) · TOTAL. Las cifras a la derecha |
| `[ 02 ]` | Sección `<h2>` HORARIOS + [panel](../componentes/panel.md) con el calendario | Barra del periodo, cuadrícula o lista y leyenda ([ficha](../componentes/calendario.md#anatomía)); bajo el título, "Horario de Lima" |
| Pie | Pie público Completa | — |

Secciones separadas por `espacio-20` (`espacio-12` < `punto-quiebre-tableta`).

### "Agendar asesoría" en la etapa A

Decisión explícita: en la etapa A **no se puede agendar**. El botón se especifica ya para que la etapa B solo lo active, sin mover la composición:

- [Botón](../componentes/boton.md) Primario grande "Agendar asesoría", con `aria-disabled="true"` (sigue enfocable, aspecto Deshabilitado de los [estados comunes](../componentes/README.md#estados-comunes)) y `aria-describedby` a la ayuda visible debajo: "Disponible pronto: muy pronto podrás agendar en línea desde aquí." Pulsarlo no hace nada.
- **Etapa B (ampliada):** pasa a enlace Primario a `/asesorias/agendar?profesional={id}` y la ayuda desaparece ([agendar](RF-15-agendar.md#entrada)). Para el rol `profesional`, que no agenda (CA-01), no se pinta.

### Disponibilidad (modo Asesoría)

Extiende la [ficha del calendario](../componentes/calendario.md); lo no dicho aquí es igual que en el modo Reserva.

| Estado de la media hora | Cuándo | Texto |
|---|---|---|
| Libre | Dentro de un `horarios[]`, fuera de `ocupados[]` y dentro de `limites` | LIBRE |
| Ocupado | En `ocupados[]` con `propia = false` | OCUPADO (sin datos de quién) |
| Propio | `ocupados[].propia = true` (cliente con sesión) | TU ASESORÍA; etapa B: folio y enlace a su [detalle](RF-15-mis-asesorias.md) (se casa por `inicio` con `GET /asesorias/mias`, como el modo Reserva) |
| Pasado | Ya empezó | PASADO |
| No reservable | Dentro de un horario pero fuera de `limites` (anticipación) | NO RESERVABLE |
| Sin horario | Fuera de todo `horarios[]` | Celda vacía |

- **Solo lectura:** ninguna celda es botón; la semana es una `<table>` normal (sin `role="grid"` ni foco itinerante) y los enlaces del periodo y MES funcionan como en la ficha. En móvil, la lista de días con `<details>` muestra los bloques en texto ("10:00–12:00 · LIBRE"), sin botones de inicio.
- Sin cierres ni margen de preparación: no existen en asesorías. Horas libres por día: `dias[].minutos_libres` ("2 h 30 min libres"). En la etapa A, LIBRE es tiempo del bloque sin asesoría; qué inicio vale para cada duración lo resuelve la etapa B.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Perfil | Carga | Identidad con su tamaño y "Cargando perfil…", `aria-busy`; el calendario espera al perfil |
| Perfil | Sin `id` o 404 (no existe o no está publicado) | En lugar del contenido: `[404] PERFIL NO DISPONIBLE` "Este perfil no existe o ya no está publicado." + "Ver el directorio" |
| Precios | Una sola duración | Una fila; no es un error |
| Horarios | Periodo sin horarios | Bajo la barra del periodo: "Aún no hay horarios publicados" + "{Nombre} publica su agenda semana a semana. Mira la siguiente o vuelve pronto." + Secundario "Ver semana siguiente" |
| Horarios | Con horarios y sin horas libres | Se ve la cuadrícula; anuncio "… 0 horas libres" |
| Horarios | `fecha` inválida o 422 `rango_invalido` | Semana actual + aviso Información "La fecha del enlace no es válida. Te mostramos esta semana." |
| Horarios | 401 con sesión caducada | Se repite sin sesión + aviso Información "Tu sesión caducó. Inicia sesión para ver tus asesorías en el calendario." + "Iniciar sesión" (`?volver=`) |
| Ambos | 503 · red caída · no JSON | Aviso Error del bloque: "El perfil no responde. Inténtalo de nuevo en unos minutos." / "Los horarios no responden…" · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal al cargar {el perfil / los horarios}." + "Reintentar". Si falla solo el calendario, el perfil sigue |
| Todo | Sin JS | `<noscript>`: aviso Información "Este perfil necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: el público solo recibe perfiles publicados y nunca datos de clientes (CA-16). El propio profesional o un Administrador con sesión pueden ver un perfil sin publicar por la API; esta vista no envía su token para el perfil y muestra el 404 público (la vista previa del propio perfil está en su [ficha](RF-15-ficha.md)).

## Copy

| Elemento | Texto |
|---|---|
| Título de la pestaña | {Nombre} · Asesorías · Bugalú Studio |
| Secciones | `[ 01 ] DURACIONES Y PRECIOS` · `[ 02 ] HORARIOS` |
| Tabla | Caption "Precio de una asesoría con {nombre}"; filas "30 min" y "1 h" ([duración](../patrones/estructura-app.md#formato-de-datos)) |
| Bajo la tabla | "Precio fijo por asesoría, presencial o por videollamada." |
| Leyenda | LIBRE · OCUPADO · TU ASESORÍA · PASADO · NO RESERVABLE (solo las presentes) |
| Redes | Enlaces externos con `external-link` y "(se abre en otra pestaña)" oculto |

## Accesibilidad

- Un `<h1>` (el nombre); secciones con `<h2>`. La identidad no es un `<header>` de página.
- Orden de foco: volver → redes → "Agendar asesoría" → tabla (sin foco) → barra del periodo → vistas → cuadrícula (sin paradas en solo lectura).
- Nombres accesibles de las celdas, como en la ficha sin acción: "martes 18 de noviembre, 10:00 a 12:00, libre". La región `role="status"` del calendario anuncia el periodo ("Semana del 16 al 22 nov 2026: 6 horas libres").
- El avatar Retrato lleva `alt=""` (el nombre es el `<h1>` de al lado).

## Pendientes

- **Ampliada por RF-15 B:** "Agendar asesoría" activo y TU ASESORÍA enlazada ([agendar](RF-15-agendar.md)).
- **leader:** registrar `<bugalu-directorio>` y el modo `asesoria` de `<bugalu-calendario>` en [frontend-islas](../../01-arquitectura/frontend-islas.md).
