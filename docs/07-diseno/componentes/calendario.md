---
id: comp-calendario
titulo: Componente — Calendario (isla)
estado: borrador
depende_de: [diseno-tokens, comp-etiqueta-tecnica, arq-frontend-islas]
---

# Calendario

"Selector de agenda" de la agenda de asesoría (`141:29060`): calendario mensual (cabecera con navegación del mes, días de semana, cuadrícula de días de 82 × 48, leyenda) + panel "Horarios" (opciones de hora y horario seleccionado). Es la base de la agenda de asesoría y de las franjas de sala.

## Anatomía

1. [Panel](panel.md) con título de sección y navegación del mes: dos botones de solo icono (`chevron-left`, `chevron-right`) con aspecto de [etiqueta](etiqueta-tecnica.md).
2. Días de semana: `fuente-familia-tecnica`, `fuente-tamano-micro`.
3. Cuadrícula de 7 columnas, hueco `espacio-1`; día: caja `borde-grosor-fino`, número en `fuente-familia-tecnica`, alto mínimo `medida-control-grande`.
4. Leyenda: etiquetas que explican cada estado de día.
5. Panel lateral de horarios: lista de horas (opciones tipo [casilla](casilla.md) radio con aspecto de botón) y resumen del horario elegido.

## Variantes

| Variante | Selección | Uso |
|---|---|---|
| Asesoría | Un día + una hora + modalidad | [RF-15](../../03-requerimientos/RF-15.md) |
| Franjas | Un día + tramo de franjas consecutivas; muestra el precio simulado del tramo | [RF-02](../../03-requerimientos/RF-02.md), [RF-04](../../03-requerimientos/RF-04.md) |
| Publicación | Administrador o profesional marcan franjas u horarios disponibles (selección múltiple) | [RF-03](../../03-requerimientos/RF-03.md), horarios de [RF-15](../../03-requerimientos/RF-15.md) |

## Estados

Comunes: [catálogo](README.md#estados-comunes). Propios del día y de la franja:

| Estado | Visual |
|---|---|
| Disponible | `color-fondo-superficie`, `borde-grosor-fino` |
| Seleccionado | `color-fondo-invertido`, número `color-texto-invertido` |
| En tramo (franjas) | `color-fondo-destacado` |
| Hoy | Número subrayado `borde-grosor-base` |
| Sin disponibilidad / ocupada | `color-texto-secundario`, patrón de rayas (`efecto-patron-paso`), no seleccionable |
| Pre-reservada (franja retenida) | Etiqueta Aviso "RETENIDA" |
| Pasado o fuera de mes | `color-texto-secundario`, no seleccionable |
| Carga de mes | Cuadrícula con `aria-busy="true"`, mismo tamaño |
| Error | [Aviso](aviso.md) Error sobre la cuadrícula con "Reintentar" |

## Tokens

`color-fondo-superficie`, `color-fondo-invertido`, `color-fondo-destacado`, `color-texto-invertido`, `color-texto-secundario`, `borde-grosor-fino`, `borde-grosor-base`, `espacio-1`, `medida-control-grande`, `efecto-patron-paso`, `fuente-familia-tecnica`, `fuente-tamano-micro`.

## Relaciones

Dentro del [flujo por pasos](../patrones/flujo-por-pasos.md); alimenta al [resumen persistente](resumen-persistente.md).

## Accesibilidad

- **Sin JS:** el servidor entrega la lista de días y horarios disponibles como grupos de radios por día (`<fieldset>`), con navegación de mes por enlaces `?mes=`. La isla mejora esa lista a cuadrícula.
- Con JS: `<table>` con botones de día; foco itinerante (flechas mueven el día, Inicio/Fin la semana, RePág/AvPág el mes); el día seleccionado con `aria-pressed="true"`.
- Cada día tiene nombre completo: "martes 18 de noviembre, 3 horarios disponibles".
- Cambio de mes anunciado en una región `aria-live="polite"` con el nombre del mes.

## Código

Isla `frontend/src/islas/Calendario.astro` que registra `<bugalu-calendario>`; atributos `variante`, `mes`, `endpoint` (disponibilidad desde `servicios/`).
