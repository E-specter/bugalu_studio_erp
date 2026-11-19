---
id: pantalla-rf-15-cierre
titulo: Pantalla — Cerrar la asesoría, notas internas y constancia (etapa C)
estado: borrador
depende_de: [RF-15, RF-18, RF-16, ADR-015, pantalla-rf-15-gestion, pantalla-rf-15-mis-asesorias, pantalla-rf-18-acciones-administrador, pantalla-rf-16-confirmacion-y-constancia, diseno-brief, patron-formularios, patron-estados-sistema, comp-panel, comp-campo, comp-boton, comp-barra-acciones, comp-aviso, comp-etiqueta-tecnica, comp-indicador-estado]
---

# Cerrar la asesoría, notas y constancia

| Campo | Valor |
|---|---|
| Requerimiento | [RF-15](../../03-requerimientos/RF-15.md): CA-12, CA-13, CA-16, CA-17 ("Por cerrar", notas, constancia) |
| Actores | Profesional artístico (las suyas) y Administrador cierran y escriben notas; el cliente, el profesional y el Administrador ven la constancia |
| Estructura | App; cerrar y notas **amplían** el [detalle de gestión](RF-15-gestion.md); la constancia tiene ruta propia |
| Ruta | `/app/asesorias/detalle?id=&accion=cerrar` · `/app/asesorias/constancia?id=` |
| Isla | `<bugalu-asesorias vista="detalle\|constancia">` |

## Cerrar la asesoría

Una `Confirmada` no avanza sola: queda POR CERRAR hasta que la marquen (decisión 6). Los paneles siguen la regla de [gestión](RF-15-gestion.md).

| Acción | Botón en el lateral | Panel |
|---|---|---|
| Realizada | Primario "Marcar realizada", en `Confirmada` desde el `inicio`, sin límite. Antes: `aria-disabled="true"` (enfocable) y ayuda "Podrás marcarla desde las {HH:mm}, cuando empiece." | `MARCAR REALIZADA · {folio}`: "{Cliente} tuvo su asesoría de {duración} el {D MMM}, a las {HH:mm}." → consecuencias → "Volver a la asesoría" + Primario "Marcar realizada" → `POST /asesorias/{id}/realizada` |
| No asistió | Peligro "Marcar no asistió", en `Pendiente de pago` o `Confirmada` desde `inicio + {t}` min, sin límite (CA-12). Antes: `aria-disabled` y "Podrás marcarlo desde las {HH:mm}, {t} minutos después del inicio." | `MARCAR INASISTENCIA · {folio}` (el de [RF-18](RF-18-acciones-administrador.md#composición)): "{Cliente} no llegó en los primeros {t} minutos." → consecuencias → "Volver a la asesoría" + Peligro "Marcar no asistió" → `POST /reservas/{id}/inasistencia` |

`{t}` sale de `politica.minutos_tolerancia_inasistencia`. Orden en el lateral: [indicador](../componentes/indicador-estado.md) → "Marcar realizada" → "Marcar no asistió" → lugar o enlace → cancelar (Administrador). Desde `fin`, la Barra es Pendiente "POR CERRAR · Marca si se realizó o si {cliente} no asistió."; entre `inicio` y `fin`, Neutro "EN HORARIO DE LA ASESORÍA". `?accion=cerrar` (desde POR CERRAR de la [agenda](RF-15-agenda.md)) lleva el foco a "Marcar realizada".

## Notas internas

| Región | Contenido |
|---|---|
| Principal, tras D5 | [Panel](../componentes/panel.md) `N1 NOTAS INTERNAS` (solo profesional y Administrador): `<form>` con NOTAS ([campo](../componentes/campo.md) Área, 0–5000, `maxlength="5000"`, contador "{n} / 5000" en `aria-live="polite"` cada 500 caracteres y al pasar 4500) → Secundario "Guardar notas" |
| Envío | `PUT /asesorias/{id}/notas {texto}` → 200 `Asesoria` (texto vacío borra las notas) |

Se escriben antes o después de la cita; no se envían a nadie. El Primario del detalle sigue siendo la acción de cierre.

## Constancia

Ruta `/app/asesorias/constancia?id=`, para el dueño, su profesional y el Administrador. Dato: `GET /asesorias/{id}/constancia` → `Constancia`. Se entra desde "Ver constancia" del detalle ([mis asesorías](RF-15-mis-asesorias.md#composición)), desde el detalle de gestión (Secundario "Ver constancia" en `Realizada`) y desde el correo.

| Región | Componente (variante) | Contenido |
|---|---|---|
| Encabezado | [encabezado-pantalla](../componentes/encabezado-pantalla.md) App | Ruta y título (Copy); sin acción |
| Principal | [panel](../componentes/panel.md) Destacado `CONSTANCIA DE ASISTENCIA` | Línea técnica "N.º {folio}" (`fuente-familia-tecnica`) → párrafo "Bugalú Studio deja constancia de que {cliente} asistió a una asesoría artística con {profesional}." (nombres: artístico y, entre paréntesis, el nombre; sin artístico, el nombre) → `<dl>` CLIENTE · PROFESIONAL · ESPECIALIDADES · FECHA (`D MMM AAAA`) · HORARIO (`HH:mm–HH:mm`, hora de Lima) · DURACIÓN · MODALIDAD · EMITIDA EL (`D MMM AAAA, HH:mm`) |
| Acciones | Botones en fila (hueco `espacio-3`; apilados en móvil) | Primario "Imprimir o guardar en PDF" (`<button>`, `window.print()`) + Secundario como enlace "Volver a la asesoría" |

**Impresión** (como la de [RF-16](RF-16-confirmacion-y-constancia.md#impresión)): se imprime **solo el panel**, con fondo blanco, sin sombra, en una hoja A4 y sin partir el `<dl>`; se ocultan cabecera, navegación, encabezado, avisos y botones; al pie, "Constancia impresa desde la plataforma de Bugalú Studio el {fecha y hora}". "Guardar en PDF" es el destino del diálogo del navegador; no hay PDF en el servidor. La constancia es inmutable: la vista no tiene nada editable.

## Estados

| Bloque | Situación | Forma y texto |
|---|---|---|
| Realizada | Pulsado antes del inicio · 409 `antes_del_inicio` | Bajo el botón: "La asesoría aún no empieza. Podrás marcarla desde las {HH:mm}." |
| No asistió | Antes de tiempo · 409 `tolerancia_no_cumplida` | "Aún no pasaron {t} minutos desde el inicio. Podrás marcarlo desde las {HH:mm}." |
| Cerrar | 409 `no_aplicable` | Panel cerrado, detalle recargado; aviso Información "Esta asesoría ya está cerrada: está {estado}." (quizá desde otra sesión) |
| Cerrar | Enviando | "Marcando…"; "Volver a la asesoría" deshabilitado |
| Cerrar | Éxito | `?aviso=asesoria-realizada` "Asesoría marcada como realizada. Enviamos la constancia a {cliente}." · `?aviso=inasistencia-marcada` "Inasistencia registrada. Avisamos a {cliente} por correo." |
| Notas | Guardando · éxito | "Guardando…"; aviso Éxito en N1 "Notas guardadas." |
| Notas | 422 · 409 `no_editable` | "Las notas admiten hasta 5000 caracteres." · aviso Información "Ya no se pueden editar las notas de esta asesoría." (texto conservado para copiarlo) |
| Notas | 503 · red · no JSON | Textos de [gestión](RF-15-gestion.md#estados): "Tus notas siguen aquí; inténtalo de nuevo." |
| Constancia | Carga | Panel con "Cargando constancia…", `aria-busy` |
| Constancia | 409 `constancia_no_disponible` | En lugar del panel: aviso Información "La constancia estará lista cuando {el profesional / tú} marque la asesoría como realizada." + "Volver a la asesoría" |
| Constancia | 404 · 401 · 503 · red · sin JS | Los de [mis asesorías](RF-15-mis-asesorias.md#estados) |

## Lo que ve el cliente

Los estados TERMINÓ, REALIZADA y NO ASISTIÓ del [detalle del cliente](RF-15-mis-asesorias.md#estados); "Ver constancia" es su Primario en `Realizada`. Nunca ve las notas (CA-13): la isla no pinta N1 y la API no las envía. El correo de la constancia: [correos](RF-15-correos.md).

## Copy

| Elemento | Texto |
|---|---|
| Consecuencias de realizada | "Se emite la constancia de asistencia y se la enviamos a {cliente} por correo. No se puede deshacer." |
| Consecuencias de no asistió | Profesional: "La asesoría queda como No asistió y lo pagado no se devuelve. Avisamos a {cliente} por correo. No se puede deshacer." Administrador: el de [RF-18](RF-18-acciones-administrador.md#copy), más "Solo tú puedes tratarla después como nivel 1." |
| Ayuda de notas | "Solo las ven {profesional} y el Administrador. {Cliente} nunca las ve. Útiles para la cotización: qué necesita, qué acordaron." |
| Constancia | Ruta: Inicio / Asesorías / {folio} / Constancia · Título: CONSTANCIA {folio} |

## Accesibilidad

- Botones deshabilitados enfocables con su ayuda en `aria-describedby`; la hora no se actualiza sola: al pulsar se vuelve a comprobar.
- N1 es `<section>` con `<h2>`; el contador no se anuncia en cada tecla.
- Constancia: un `<h1>`; el panel es `<article aria-labelledby>`; el `<dl>` se lee completo. En impresión, contraste de texto principal sobre blanco.

## Preguntas

1. ¿En qué estados devuelve `PUT …/notas` el 409 `no_editable`? La spec las deja editables en todo estado salvo lo que diga la API.
2. Con un menor (adulto responsable, [condiciones](../../08-legal/condiciones-de-contratacion.md#menores-de-edad)), ¿la constancia nombra al adulto? El contrato no lo trae; v1 sin él.
