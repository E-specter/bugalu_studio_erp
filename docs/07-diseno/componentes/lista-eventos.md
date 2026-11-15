---
id: comp-lista-eventos
titulo: Componente — Lista de eventos
estado: borrador
depende_de: [diseno-tokens, comp-panel]
---

# Lista de eventos

Filas cronológicas: "Registro de actividad" (`161:609`: indicador + mensaje + hora), "Próximas entregas" y "Alertas" (`161:609`), "Próximos hitos" (`169:4267`: hito destacado + hitos) e "Historial técnico / Terminal" (`161:1750`).

## Anatomía

1. Fila: indicador (icono `medida-icono-sm` o [señal](indicador-estado.md)), mensaje (`fuente-tamano-base`) y marca de tiempo a la derecha (`fuente-familia-tecnica`, `fuente-tamano-micro`, `color-texto-secundario`).
2. Filas separadas por `borde-grosor-fino`, relleno `espacio-3`.
3. Elemento destacado opcional arriba: [panel](panel.md) Destacado con fecha grande y descripción.
4. Acción al pie opcional ("Ver todo").

## Variantes

| Variante | Diferencia | Uso |
|---|---|---|
| Actividad | Pasado, del más reciente al más antiguo | Actividad reciente |
| Agenda | Futuro, del más próximo al más lejano, con destacado | Próximas entregas, hitos, sesiones |
| Alertas | Indicador `alert-triangle` en `color-texto-alerta` | Pendientes que requieren acción |
| Terminal | Fondo `color-fondo-invertido`, texto `color-texto-invertido` en `fuente-familia-tecnica`, prefijo de hora `[14:02:11]` | Historial técnico de validación de audio |

## Estados

Estático; una fila que enlaza cumple los [estados comunes](README.md#estados-comunes). Vacío: "Sin actividad registrada" ([estados del sistema](../patrones/estados-sistema.md)).

## Tokens

`medida-icono-sm`, `borde-grosor-fino`, `espacio-3`, `color-texto-secundario`, `color-texto-alerta`, `color-fondo-invertido`, `color-texto-invertido`, `fuente-familia-tecnica`, `fuente-tamano-micro`, `fuente-tamano-base`.

## Relaciones

Dentro de [panel](panel.md). Las fechas siguen el formato de [estructura de app](../patrones/estructura-app.md#formato-de-datos).

## Accesibilidad

- `<ol>` (el orden importa) con `<time datetime>` en cada marca.
- Terminal que se actualiza en vivo: `role="log"` con `aria-live="polite"`.

## Código

`frontend/src/componentes/ListaEventos.astro`, props `variante`, `eventos` (indicador, mensaje, fecha, href), `destacado`.
