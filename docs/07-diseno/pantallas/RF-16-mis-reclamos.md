---
id: pantalla-rf-16-mis-reclamos
titulo: Pantalla — Mis reclamos (lista y detalle del cliente)
estado: aprobado
depende_de: [RF-16, pantalla-rf-16-formulario, diseno-brief, patron-estructura-app, patron-tablas-y-tableros, patron-estados-sistema, comp-hoja-reclamacion, comp-tabla, comp-panel, comp-etiqueta-tecnica, comp-aviso, comp-boton, comp-encabezado-pantalla]
---

# Mis reclamos

| Campo | Valor |
|---|---|
| Requerimiento | [RF-16](../../03-requerimientos/RF-16.md): CA-10, CA-13 |
| Actores | Artista/Cliente (solo las suyas) |
| Estructura | App, portal ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/reclamos/` y `/app/reclamos/detalle?id=`. URL: `id`. Las mismas rutas son la [bandeja](RF-16-bandeja.md) del Administrador: la isla elige la vista por el rol |
| Isla | `<bugalu-reclamos vista="lista\|detalle">` (nueva) |

**Decisión del brief: entrada en el menú de la [cabecera](../componentes/cabecera-app.md), no destino nuevo.** Casi siempre estará vacía y la [navegación táctil](../componentes/navegacion-tactil.md) solo tiene cinco plazas. Se llega por "Mis reclamos" del menú (solo cliente), por "Ver mis reclamos" de la [constancia](RF-16-confirmacion-y-constancia.md) y por el botón de los [correos](RF-16-correos.md).

## Recorrido

1. El cliente abre "Mis reclamos": ve sus hojas, la más reciente arriba, con su estado.
2. "Ver hoja {numero}" abre el detalle: la hoja completa y, cuando existe, la respuesta del estudio.
3. Puede imprimirla o guardarla en PDF. Para presentar otra, "Presentar un reclamo" lleva al [formulario](RF-16-formulario.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Hojas | `GET /reclamaciones/mias` → `[HojaResumen]` | Por `creada_en` descendente. Total en la región de estado: "2 hojas" |
| Número | `numero` | `fuente-familia-tecnica`, `tabular-nums` |
| Presentada | `creada_en` | `D MMM AAAA, HH:mm` (documento legal: con año) |
| Tipo | `tipo` | "Reclamo" · "Queja" · `null` "Sin marcar" |
| Estado | `estado`, `vence_respuesta` | [Etiqueta](../componentes/etiqueta-tecnica.md) Aviso EN TRÁMITE + "Respuesta hasta el {D MMM AAAA}" debajo · Éxito RESPONDIDA |
| Hoja | `GET /reclamaciones/{id}` → `Hoja` | [Hoja](../componentes/hoja-reclamacion.md) Consulta (sin `respondida_por`; adjuntos sin enlace: solo el Administrador los descarga) |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Lista | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción; acción Primario como enlace "Presentar un reclamo" (`/libro-de-reclamaciones/`) |
| Lista | Principal | [panel](../componentes/panel.md) `HOJAS` + [tabla](../componentes/tabla.md) Directorio | HOJA (número) · PRESENTADA · TIPO · ESTADO · "Ver hoja {numero}" (Secundario como enlace) |
| Detalle | Encabezado | encabezado-pantalla App | Ruta, índice, título "HOJA N.º {numero}", descripción; acción Secundario "Imprimir o guardar en PDF" |
| Detalle | Principal | hoja Consulta | La hoja y la sección 4 (respuesta o "SIN RESPUESTA AÚN" con el plazo) |

Sin columna lateral: la hoja es el contenido. Adaptabilidad: tabla en tarjetas < `punto-quiebre-escritorio` ([tabla](../componentes/tabla.md#adaptabilidad)). Impresión del detalle: [ficha](../componentes/hoja-reclamacion.md#impresión).

## Estados

| Vista | Situación | Forma y texto |
|---|---|---|
| Lista | Vacío | Panel con "Aún no tienes hojas" + "Aquí verás los reclamos y quejas que presentes con tu sesión iniciada, y nuestra respuesta." La acción del vacío es "Presentar un reclamo" (Primario); el encabezado no repite la acción ([estados del sistema](../patrones/estados-sistema.md#vacío)) |
| Ambas | Carga | Panel "Cargando…", `aria-busy="true"` |
| Lista | Error | Aviso Error en el panel + "Reintentar" |
| Detalle | 404, `id` no válido o 403 (hoja ajena) | Panel `[404] HOJA NO ENCONTRADA` + aviso Información "No encontramos esta hoja en tu cuenta." + "Volver a mis reclamos". El 403 se pinta igual: no se revela que la hoja existe (CA-10) |
| Ambas | 401 · 503 · red · no JSON · sin JS | Como en [solicitudes](RF-01-solicitudes.md#estados), con "Ir al acceso" (`/acceso/?volver=`) en 401 |
| Lista | Personal | Ve el 403 de la sección: `[403] SIN PERMISO` "Esta sección es para clientes y el Administrador." + "Volver al inicio" |

## Copy

| Elemento | Texto |
|---|---|
| Lista: ruta e índice | Inicio / Mis reclamos · `[P4] CUENTA / RECLAMOS` |
| Lista: título y descripción | MIS RECLAMOS · "Las hojas del Libro de Reclamaciones que presentaste con tu sesión iniciada y nuestra respuesta. Te respondemos en un máximo de 15 días hábiles." |
| Detalle: ruta y descripción | Inicio / Mis reclamos / {numero} · "{Reclamo \| Queja \| Hoja} presentado el {D MMM AAAA}." |
| Columnas | HOJA · PRESENTADA · TIPO · ESTADO |
| Nota bajo la tabla | "¿No ves una hoja? Las que presentaste sin iniciar sesión no aparecen aquí; su copia está en tu correo." |

## Accesibilidad

- `<h1>` del encabezado; panel `<section>` con `<h2>`; tabla con `<caption>` "Tus hojas de reclamación" y el número como `<th scope="row">`; en el detalle, la hoja empieza en `<h2>`.
- Acciones de fila con el número en el nombre accesible ("Ver hoja 000000001-2026").
- Región `role="status"` estable para "Cargando…" y el total; el estado se dice en texto, nunca solo con color.
