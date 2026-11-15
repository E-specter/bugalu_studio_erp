---
id: patron-formularios
titulo: Patrón — Formularios
estado: borrador
depende_de: [comp-campo, comp-barra-acciones]
---

# Formularios

Origen: brief del proyecto (`141:28788`), accesos (`112:286`, `112:385`), panel de comentario (`145:3617`) y transformación de audio (`161:1750`).

## Composición

1. Un formulario largo se divide en [paneles](../componentes/panel.md) temáticos con código (`A1 DATOS DEL ARTISTA`, `A2 DIRECCIÓN SONORA`…), en el orden en que el usuario tiene los datos.
2. Dentro del panel, [campos](../componentes/campo.md) en filas de 2 o 3 columnas solo cuando los datos son hermanos (nombre + correo; fecha + formato + duración); el resto a ancho completo. En móvil, una columna.
3. Opciones: [casilla](../componentes/casilla.md) para múltiple, [tarjeta de opción](../componentes/tarjeta-opcion.md) para única con explicación, `<select>` para listas largas cerradas, [etiquetas](../componentes/etiqueta-tecnica.md) Filtro para etiquetado rápido (dirección sonora).
4. Adjuntos con [carga de archivos](../componentes/carga-archivos.md).
5. Cierra con [barra de acciones](../componentes/barra-acciones.md).

## Validación

| Momento | Qué se valida | Cómo se muestra |
|---|---|---|
| Al salir del campo | Formato (correo, teléfono, longitud) | Error bajo el campo, solo después de que el usuario lo tocó |
| Al enviar | Todo, también reglas del servidor | [Aviso](../componentes/aviso.md) Error arriba con el número de errores y enlaces a cada campo; foco al aviso |
| En el servidor | Reglas de negocio (disponibilidad, solapamiento) | Igual que al enviar; los datos introducidos se conservan |

- El mensaje dice **qué pasó y cómo corregirlo** ("La fecha debe ser posterior a hoy"), nunca "Campo inválido".
- Los obligatorios se marcan con texto; si casi todos lo son, se marcan los opcionales.
- La validación HTML nativa (`required`, `type`, `pattern`) es la primera capa; la isla no es necesaria para validar.

## Prevención de errores

- Valores por defecto razonables y formatos en la ayuda (`DD/MM/AAAA`).
- Acciones irreversibles (cancelar reserva, rechazar pago, publicar versión) piden confirmación en un paso o página propia con resumen de consecuencias, y usan el botón Peligro.
- Envío protegido contra doble clic (botón en estado Carga).
- Formularios largos guardan avance ([indicador](../componentes/indicador-estado.md) "GUARDADO HACE 1 MIN" en la cabecera).

## Accesos

Formulario de una columna: título técnico, campos con prefijo `//`, "Recordar sesión" + "Recuperar clave" en una fila, botón primario a ancho completo y enlace a registro debajo. Mensaje de error de credenciales genérico ("Correo o contraseña incorrectos"), sin revelar cuál falla.

## Accesibilidad

- Cada grupo en `<fieldset>` + `<legend>`; cada campo con `<label>`.
- Orden de foco = orden visual.
- Sin límite de tiempo; si lo hubiera (pre-reserva), se avisa y se puede ampliar (WCAG 2.2.1).
- No se pide dos veces el mismo dato en un flujo (WCAG 3.3.7): lo ya dado se muestra prellenado.
