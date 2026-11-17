---
id: pantalla-rf-16-bandeja
titulo: Pantalla — Libro de Reclamaciones del Administrador (bandeja, detalle, respuesta y CSV)
estado: borrador
depende_de: [RF-16, pantalla-rf-16-mis-reclamos, pantalla-rf-18-devoluciones, diseno-brief, patron-tablas-y-tableros, patron-formularios, patron-estados-sistema, comp-hoja-reclamacion, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-barra-acciones, comp-indicador-estado, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Bandeja del Libro de Reclamaciones

| Campo | Valor |
|---|---|
| Requerimiento | [RF-16](../../03-requerimientos/RF-16.md): CA-06 (descarga), CA-07, CA-11, CA-13 |
| Actores | Administrador |
| Estructura | App, panel interno ([estructura de app](../patrones/estructura-app.md#app)) |
| Ruta | `/app/reclamos/?estado=pendiente\|respondida&desde=&hasta=` (sin `estado`: todas) · `/app/reclamos/detalle?id=`. URL: `estado`, `desde`, `hasta`, `id`, `aviso` |
| Isla | `<bugalu-reclamos vista="lista\|detalle">`; destino RECLAMOS (`book-open`) de la [navegación](../componentes/navegacion-lateral.md) |

## Recorrido

1. El Administrador abre RECLAMOS (o el botón del correo): primero las pendientes, la que vence antes arriba.
2. "Revisar hoja {numero}": lee la hoja y abre los adjuntos.
3. Escribe la respuesta, elige correo o carta, la revisa y la envía una sola vez → el detalle vuelve con `?aviso=respuesta-enviada` o `respuesta-registrada`.
4. Si Indecopi pide las hojas, filtra por fechas y "Exportar CSV". Las del libro físico entran por [transcribir](RF-16-transcribir.md).

## Datos

| Dato | Origen | Formato |
|---|---|---|
| Hojas | `GET /reclamaciones?estado=&desde=&hasta=` → `[HojaResumen]` | Pendientes por `vence_respuesta` ascendente y luego respondidas por `creada_en` descendente. Total: "12 hojas · 3 pendientes" |
| Número, presentada, tipo | `numero`, `creada_en`, `tipo` | Como en [mis reclamos](RF-16-mis-reclamos.md#datos); `null` "Sin marcar" |
| Consumidor | `consumidor.nombre` | Tal cual |
| Plazo | `vence_respuesta` (+ días hábiles, ver Preguntas) | Pendiente: [etiqueta](../componentes/etiqueta-tecnica.md) Aviso "VENCE EN {N} DÍAS HÁBILES" ("1 DÍA HÁBIL", "VENCE HOY") con "hasta el {D MMM AAAA}" debajo; pasado: Alerta "FUERA DE PLAZO" + "Venció el {D MMM AAAA}". Respondida: Éxito RESPONDIDA. Siempre texto, nunca solo color |
| Hoja | `GET /reclamaciones/{id}` → `Hoja` | [Hoja](../componentes/hoja-reclamacion.md) Consulta con `respondida_por` |
| Adjunto | `GET /reclamaciones/{id}/adjuntos/{n}` | La isla lo pide con el token, crea un `blob:` y lo abre en pestaña nueva ([archivo](../componentes/archivo.md) Lectura "Abrir {nombre}") |
| Responder | `POST /reclamaciones/{id}/respuesta {texto, medio, referencia_carta?, enviada_en?}` → 200 `Hoja` | Ver formulario |
| CSV | `GET /reclamaciones/exportar?desde=&hasta=` | Descarga `blob:` como `reclamaciones-{desde}-{hasta}.csv` |

## Composición

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Lista | Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta, índice, título, descripción; acciones Secundario: "Transcribir hoja del libro físico" (enlace) y "Exportar CSV" (botón) |
| Lista | Controles | [etiquetas](../componentes/etiqueta-tecnica.md) Filtro + formulario `GET` | TODAS · PENDIENTES · RESPONDIDAS; DESDE y HASTA ([campo](../componentes/campo.md) `date`, fecha de presentación) + "Filtrar" (Secundario) + "Quitar fechas" (enlace, si hay fechas) |
| Lista | Principal | [panel](../componentes/panel.md) `HOJAS` + [tabla](../componentes/tabla.md) Directorio | HOJA (número; debajo, etiqueta Neutra TRANSCRITA si `origen = libro_fisico`) · PRESENTADA · CONSUMIDOR · TIPO · PLAZO · "Revisar hoja {numero}" (Secundario como enlace) |
| Detalle | Principal | hoja Consulta | Hoja completa con adjuntos y sección 4 |
| Detalle | Lateral | panel Lateral `R1 RESPUESTA` (pendiente) | Plazo (etiqueta de la lista) → MEDIO ([casillas](../componentes/casilla.md) Radio: Correo electrónico · Carta al domicilio; marcado el que pidió el consumidor) → RESPUESTA (Área, obligatoria, 10 a 5000) → con carta: REFERENCIA DE LA CARTA (Texto, obligatoria) y FECHA DE ENVÍO (`date`, obligatoria, `max` = hoy) → Primario "Revisar respuesta" |
| Detalle | Lateral | panel Lateral `R1 REVISA LA RESPUESTA` (en lugar del anterior) | El texto en lectura (`pre-line`), medio, destino (correo del consumidor o domicilio y referencia), consecuencias → [barra](../componentes/barra-acciones.md) Móvil: "Corregir respuesta" (Secundario) + Primario "Enviar respuesta" (correo) o "Registrar respuesta" (carta) |
| Detalle | Lateral | [indicador](../componentes/indicador-estado.md) Barra (respondida) | Correcto "RESPONDIDA" + `enviada_en`; la respuesta se lee en la sección 4 de la hoja |

**Decisión del brief:** la respuesta es irreversible (CA-07), así que lleva revisión propia, sin palabra escrita, como publicar un [texto legal](RF-17-textos-legales.md#administrador-textos). "Corregir respuesta" conserva lo escrito. Adaptabilidad: la de [pagos](RF-05-pagos.md#composición) (tarjetas en móvil, lateral después de la hoja).

## Estados

| Vista | Situación | Forma y texto |
|---|---|---|
| Lista | Vacío (todas, sin fechas) | "Aún no hay hojas" + "Cuando alguien presente un reclamo o una queja, aparecerá aquí y te avisaremos por correo." Sin acción; las del encabezado siguen |
| Lista | Sin resultados | "No hay hojas {pendientes \| respondidas} {entre el {desde} y el {hasta}}." + "Quitar filtros" (Secundario) |
| Ambas | Carga | Panel "Cargando…", `aria-busy` |
| Lista | 422 de fechas | Bajo HASTA: "La fecha final debe ser igual o posterior a la inicial." |
| Detalle | 404 o `id` no válido | Panel `[404] HOJA NO ENCONTRADA` + aviso Información "No encontramos esta hoja." + "Volver a reclamos" |
| Detalle | Adjunto 404 · 503 · red | Aviso Error bajo el archivo: "No pudimos abrir {nombre}. Inténtalo de nuevo." |
| Responder | Validación local / 422 | "Escribe la respuesta con al menos 10 caracteres." · "La respuesta admite hasta 5000 caracteres." · "Escribe la referencia de la carta." · "Elige la fecha en que enviaste la carta." · "La fecha de envío no puede ser futura." |
| Responder | Enviando | Primario en Carga ("Enviando…", "Registrando…"); "Corregir respuesta" deshabilitado |
| Responder | 409 `ya_respondida` | Aviso Información "Esta hoja ya tiene respuesta, quizá desde otra sesión." y la hoja se recarga |
| Exportar | Sin fechas | Error bajo DESDE: "Elige DESDE y HASTA para exportar." y foco ahí. Enviando: "Exportando…". 422 `rango_invalido`: el texto de 422 de fechas |
| Ambas | 401 · 403 · 503 · red · no JSON · sin JS | Como en [pagos](RF-05-pagos.md#estados) (403: "Esta sección es solo para el Administrador."); al enviar, sin "Reintentar" y con lo escrito conservado |
| Detalle | Éxito | `respuesta-enviada` "Respuesta enviada al correo del consumidor." · `respuesta-registrada` "Respuesta registrada con la carta {referencia}." · `hoja-transcrita` (de [transcribir](RF-16-transcribir.md)) |

Claves `aviso` (lista cerrada): las tres de la tabla. Permisos: solo `administrador`; personal no ve RECLAMOS y, por URL, ve el 403; el cliente ve [mis reclamos](RF-16-mis-reclamos.md) en las mismas rutas.

## Copy

| Elemento | Texto |
|---|---|
| Lista: ruta e índice | Inicio / Reclamos · `[A12] CONTROL / RECLAMOS` |
| Lista: título y descripción | LIBRO DE RECLAMACIONES · "Hojas presentadas en la web o transcritas del libro físico. Responde cada una dentro de 15 días hábiles; las respuestas no se editan." |
| Detalle: ruta, título y descripción | Inicio / Reclamos / {numero} · HOJA N.º {numero} · "{consumidor} · {tipo} presentado el {D MMM AAAA}." |
| Ayudas | Respuesta: "La verá el consumidor tal cual. Si el tipo marcado no corresponde, trátala según su contenido y dilo aquí. Puedes proponer una solución." · Medio: "El consumidor pidió {medio}." · Referencia: "Número de guía o de cargo de la carta." |
| Consecuencias | Correo: "Enviamos esta respuesta a {correo} y queda registrada con tu nombre. No se puede editar ni borrar." · Carta: "Queda registrada la carta {referencia} enviada el {fecha}, con tu nombre. No se puede editar ni borrar." |
| Columnas | HOJA · PRESENTADA · CONSUMIDOR · TIPO · PLAZO |

## Accesibilidad

- `<h1>` del encabezado; hoja desde `<h2>`; paneles `<section>` con `<h2>`; tabla con `<caption>` y número como `<th scope="row">`; filtros con `aria-current="true"`.
- MEDIO es `<fieldset>`; REFERENCIA y FECHA aparecen tras su opción, que lleva `aria-controls`. Al revisar, foco al `<h2>` de R1; al corregir, a RESPUESTA.
- Región `role="status"` estable para la carga, el total y la exportación; al fallar un envío, foco al aviso.

## Preguntas para leader

1. **dev-backend:** "Vence en N días hábiles" pide contar hábiles con feriados. Propuesta: `dias_habiles_restantes` (entero, negativo si venció) en `HojaResumen` y `Hoja`. Sin él, la isla lo cuenta con `GET /feriados?anio=`.
2. **dev-backend:** adjunto y CSV devuelven el archivo y piden el token: la isla usa `blob:`. Alternativa coherente con RF-05: `{url, expira_en}` firmada.
3. ¿El Administrador puede cambiar el medio que pidió el consumidor? El contrato lo permite; aquí se ofrece marcado el pedido y se avisa.
