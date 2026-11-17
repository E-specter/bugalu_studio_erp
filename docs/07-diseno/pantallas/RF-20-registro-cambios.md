---
id: pantalla-rf-20-registro-cambios
titulo: Pantalla — Registro de cambios (Administrador)
estado: borrador
depende_de: [RF-20, ADR-013, diseno-brief, patron-estructura-app, patron-tablas-y-tableros, patron-estados-sistema, comp-tabla, comp-panel, comp-campo, comp-boton, comp-aviso, comp-etiqueta-tecnica]
---

# Registro de cambios

| Campo | Valor |
|---|---|
| Requerimiento | [RF-20](../../03-requerimientos/RF-20.md): CA-08, CA-09 (pantalla "Registro de cambios"), CA-10 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/cambios?desde=AAAA-MM-DD&hasta=AAAA-MM-DD&recurso=` (por defecto, los últimos 30 días y todos los recursos) |
| Isla | `<bugalu-registro-cambios>` (nueva) |
| Origen Figma | Ninguno; tabla del [directorio](../patrones/tablas-y-tableros.md#directorio-tabla) (`161:842`) |

## Recorrido

1. Entra por CAMBIOS (`history`), que solo se pinta para `administrador`, o desde "Ver en el registro de cambios" tras aplicar un [cambio sensible](RF-20-cambios-sensibles.md) (llega con `recurso`).
2. Ve los cambios del periodo, del más reciente al más antiguo.
3. Ajusta DESDE, HASTA y RECURSO y pulsa "Filtrar": es un formulario `GET`, así que el filtro vive en la URL y se puede compartir.
4. Solo consulta: no hay acciones de editar ni borrar.

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Cambios | `GET /registro-cambios?desde=&hasta=&recurso=` → `[CambioRegistrado]` | Total visible en la ayuda del panel ("12 cambios del 17 oct al 16 nov.", como pide [tablas y tableros](../patrones/tablas-y-tableros.md)); orden de la API (más reciente primero) |
| Fecha | `cambiado_en` | `<time datetime>`. Relativa < 7 días ("hace 2 h", "hace 3 días") con la absoluta en `title`; si no, `D MMM AAAA, HH:mm` ([formato](../patrones/estructura-app.md#formato-de-datos)). El `title` es un extra para el ratón: la relativa basta sola |
| Autor | `autor.nombre` | Tal cual |
| Recurso | `recurso`, `nombre_recurso` | `nombre_recurso` en la celda principal ("Grabación de voces"); debajo, [etiqueta](../componentes/etiqueta-tecnica.md) Neutra IMPUESTOS · SERVICIO · ESPECIALISTA · RECARGOS · PARÁMETROS |
| Campo, antes, después | `campo`, `anterior`, `nuevo` | Etiqueta y formato de la tabla de campos de [cambios sensibles](RF-20-cambios-sensibles.md#flujo-con-barreras); valor desconocido, tal cual |
| Filtros | Consulta de la URL | DESDE y HASTA: [campo](../componentes/campo.md) `date`; RECURSO: Selector (Todos, Impuestos, Servicios, Especialistas, Recargos, Parámetros) |

## Composición

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título y descripción; sin acción |
| Controles | `<form method="get">` | DESDE · HASTA · RECURSO en fila (una columna en móvil) + "Filtrar" ([botón](../componentes/boton.md) Secundario) y, si el filtro no es el de por defecto, enlace "Ver los últimos 30 días" |
| Principal | [panel](../componentes/panel.md) `CAMBIOS` + [tabla](../componentes/tabla.md) Compacta | FECHA · AUTOR · RECURSO · CAMPO · ANTES · DESPUÉS. Ayuda del panel: "{n} cambios del {desde} al {hasta}. Nadie puede editar ni borrar este registro." (sin el total cuando está vacío) |

Patrones: [tablas y tableros](../patrones/tablas-y-tableros.md), [estados del sistema](../patrones/estados-sistema.md). Sin acción primaria: es una vista de consulta. Adaptabilidad: < `punto-quiebre-escritorio`, cada fila pasa a tarjeta (`<dl>`). Sin paginación: el contrato limita el rango a 366 días y el volumen es bajo.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Tabla | Carga | Panel con "Cargando…" y `aria-busy="true"` |
| Tabla | Sin cambios en el periodo por defecto | Vacío: "No hay cambios en los últimos 30 días" + "Aquí aparece cada cambio de impuestos, tarifas, recargos y plazos, con quién lo hizo." Controles visibles (hay periodos que consultar) |
| Tabla | Sin resultados con filtro | "No hay cambios con estos filtros." + "Ver los últimos 30 días" (Secundario) |
| Filtros | Validación local o 422 `rango_invalido` | Error bajo HASTA: "Elige una fecha final igual o posterior a la inicial, con hasta 366 días de diferencia." Resumen de errores al enviar |
| Filtros | `recurso` o fechas desconocidas en la URL | Se ignoran y se usa el valor por defecto; aviso Información "El enlace traía un filtro no válido. Te mostramos los últimos 30 días." |
| Todas | 401 | Aviso "Tu sesión no es válida. Inicia sesión para continuar." + "Ir al acceso interno" (`?volver=` con la URL) |
| Todas | 403 | En lugar de la vista: `[403] SIN PERMISO` "Esta sección es solo para el Administrador." + "Volver al inicio" |
| Todas | 503 · red · no JSON | "El servicio no responde. Inténtalo de nuevo en unos minutos." · "Sin conexión. Revisa tu red y vuelve a intentarlo." · "Algo salió mal. Inténtalo de nuevo." + "Reintentar" |
| Todas | Sin JS | `<noscript>`: aviso Información "Esta sección necesita JavaScript. Actívalo en tu navegador y recarga la página." |

Permisos: solo `administrador`; el destino no se pinta a otros roles.

## Copy

| Elemento | Texto |
|---|---|
| Ruta e índice | Inicio / Cambios · `[A9] CONTROL / CAMBIOS` |
| Título | REGISTRO DE CAMBIOS |
| Descripción | Quién cambió impuestos, tarifas, recargos y plazos, cuándo, y qué valor tenían antes. |
| Filtros | DESDE · HASTA · RECURSO · Filtrar |

## Accesibilidad

- `<h1>` del encabezado; el panel es `<section>` con `<h2>`; la tabla con `<caption>` "Cambios del {desde} al {hasta}" y la fecha como `<th scope="row">`.
- Los filtros son un `<form>` con `<label>` visibles; "Filtrar" es `type="submit"`.
- La región `role="status"` de la isla anuncia "12 cambios del 17 oct al 16 nov" al cargar.

## Pendientes

Ninguno.
