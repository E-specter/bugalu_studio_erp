---
id: fund-movimiento
titulo: Fundamento — Movimiento
estado: borrador
depende_de: [diseno-tokens, diseno-brief]
---

# Movimiento

Figma no define animación (no hay prototipos ni duraciones). Este fundamento es **inferido** desde los principios de la guía: "Rigor sonoro" (`86:66`, medición precisa, sin ornamentos) y "Strokes dinámicos" (`88:491`, movimiento ondulado en elementos de acción). Valores en [tokens](../tokens.md#movimiento-y-efectos).

## Principios

1. **Mecánico, no orgánico.** El movimiento imita equipo de estudio: teclas que bajan, vúmetros que suben, cabezales que avanzan. Nada rebota ni flota.
2. **Funcional.** Solo se anima lo que informa: cambio de estado, progreso, posición de reproducción, aparición de un panel. Nada se anima por decoración en el panel interno.
3. **Breve.** Ninguna transición de interfaz supera `movimiento-duracion-base`.

## Catálogo

| Evento | Propiedad | Duración | Curva |
|---|---|---|---|
| Hover y foco de control | `background-color`, `color`, `border-color` | `movimiento-duracion-rapida` | `movimiento-curva-estandar` |
| Pulsación (tecla) | `transform`, `box-shadow` ([forma](forma-elevacion.md#interacción-física)) | `movimiento-duracion-rapida` | `movimiento-curva-estandar` |
| Apertura de menú o panel, cambio de paso | `opacity`, `transform` (≤ `espacio-2`) | `movimiento-duracion-base` | `movimiento-curva-estandar` |
| Progreso de carga y avance | `inline-size` de la barra | Continuo, según el dato real | Lineal |
| Cabezal de reproducción | Posición sincronizada con el audio | Continuo | Lineal |
| Señal de sincronización activa | `opacity` 1 → `efecto-opacidad-capa` en bucle | `movimiento-duracion-bucle` | Lineal |

## Reglas

1. Solo se animan `opacity`, `transform`, colores y `box-shadow`; nunca dimensiones de diseño (provoca saltos de retícula).
2. **`prefers-reduced-motion: reduce`:** se anulan desplazamientos, parpadeos y bucles; quedan los cambios de color instantáneos y el progreso (que es dato, no decoración). Regla global en `base.css`.
3. Nada parpadea más de 3 veces por segundo (WCAG 2.3.1).
4. Los efectos de imagen (glitch, separación RGB, `88:197`–`88:217`) son **estáticos**: se aplican al asset, no se animan en la interfaz.
5. Un cambio de estado que el usuario debe notar (pago validado, versión publicada) se anuncia con texto y región `aria-live`, no solo con movimiento.
