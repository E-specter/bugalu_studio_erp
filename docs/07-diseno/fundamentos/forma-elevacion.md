---
id: fund-forma-elevacion
titulo: Fundamento — Forma y elevación
estado: borrador
depende_de: [diseno-tokens, diseno-brief]
---

# Forma y elevación

Principio "Brutalismo técnico" (`86:63`): estructuras explícitas, bordes marcados de alta definición y **sombras planas sin difuminar**, inspiradas en racks analógicos y consolas. Valores en [tokens](../tokens.md#medidas-quiebres-y-forma).

## Bordes

| Uso | Grosor | Color |
|---|---|---|
| Contorno de componente (botón, campo, panel, tarjeta, etiqueta) | `borde-grosor-base` | `color-borde-fuerte` |
| Reglas bajo encabezados, divisores de fila, celdas | `borde-grosor-fino` | `color-borde-fuerte` |
| Líneas técnicas y bordes parciales decorativos | `borde-grosor-fino` a `borde-grosor-base` | `color-borde-tecnico` |
| Escuadras de registro (esquinas de paneles de acceso) | `borde-grosor-grueso` | `color-borde-tecnico` |

1. **Grosor constante** por nivel: un componente no mezcla grosores en su contorno (`88:341`).
2. El borde de error **sustituye** al borde normal con `color-texto-alerta` y el mismo grosor; no se añade un segundo borde.
3. Bordes discontinuos o parciales (efecto 10, `88:344`) solo en paneles de control y tarjetas de datos, nunca en controles interactivos (se confunden con deshabilitado).

## Esquinas

- `borde-radio-ninguno` en todo: botones, campos, paneles, tarjetas, avatares (cuadrados), tablas.
- `borde-radio-etiqueta` solo en la [etiqueta técnica](../componentes/etiqueta-tecnica.md) (`86:184`), para distinguirla de un botón.
- Excepciones circulares: la señal de estado (`medida-senal`) y el control de radio nativo.

## Elevación

No hay sombras difusas. La profundidad se expresa con tres recursos, en este orden de preferencia:

1. **Borde + contraste de superficie:** superficie blanca sobre lienzo, o navy sobre lienzo.
2. **Sombra plana:** desplazada, sin desenfoque, en `color-borde-fuerte`.
   - `sombra-plana-sm`: controles en reposo (botón, tarjeta-opción).
   - `sombra-plana-md`: panel o tarjeta que se debe leer "por encima" (tarjeta de proyecto arrastrable, resumen persistente).
3. **Transparencias superpuestas** (efecto 13, `88:409`): 2–3 capas lavanda a `efecto-opacidad-capa`, para fondos de panel; nunca bajo texto sin superficie opaca.

| Nivel | Recurso | Ejemplos |
|---|---|---|
| 0 | Plano, sin borde | Lienzo, texto suelto |
| 1 | Borde base | Panel, campo, tabla, métrica |
| 2 | Borde + `sombra-plana-sm` | Botón, tarjeta-opción, tarjeta de proyecto |
| 3 | Borde + `sombra-plana-md` | Tarjeta en arrastre, resumen persistente, menú abierto |

## Interacción física

La sombra plana se comporta como una tecla de consola: en `:active` el elemento se desplaza lo que mide su sombra (`translate`) y la sombra pasa a 0. Con `prefers-reduced-motion: reduce` el desplazamiento se elimina y solo cambia el color.

## Por qué

- La guía habla de "sombras planas sin difuminar" pero no da el desplazamiento: **inferido** 2 px y 4 px, coherentes con el grosor de borde de 2 px.
- La sección de componentes de la guía pide "esquinas rectas y bordes sutiles" y evitar el contraste extremo (`88:341`): por eso los divisores internos son de 1 px y solo el contorno es de 2 px.
