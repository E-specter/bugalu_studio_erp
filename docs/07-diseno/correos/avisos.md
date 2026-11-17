---
id: correo-avisos
titulo: Correo — Bloques por tipo de aviso
estado: borrador
depende_de: [correo-plantilla, correo-evento-calendario]
---

# Bloques por tipo de aviso

Cómo usa la [plantilla](plantilla.md) cada tipo de aviso de `notificaciones/dominio/redaccion.py` y `redaccion_rf18.py`. El asunto y el cuerpo **no cambian**: salen de `redactar()` y aquí solo se decide el envoltorio.

## Por tipo

Todos usan cabecera, etiqueta y título (el asunto), saludo, cuerpo, botón y pie. `{url}` es la URL pública de la plataforma. "Tabla" y "lista" indican qué produce hoy su cuerpo con las [reglas de abajo](#del-texto-al-html).

| Tipo | Para | Pie | Etiqueta | Cuerpo produce | Botón: texto → destino | Evento |
|---|---|---|---|---|---|---|
| `reserva_creada` | Cliente | Cuenta | RESERVA | Tabla y lista (datos para pagar) | Ver mi reserva → `{url}/app/reservas/detalle?id={id_reserva}` | No |
| `reserva_caducada` | Cliente | Cuenta | RESERVA | Párrafos | Reservar otro horario → `{url}/reservar/` | No |
| `pago_registrado` | Administrador | Administración | PAGO | Tabla | Revisar el pago → `{url}/app/pagos/revisar?id={id_pago}` | No |
| `pago_aprobado` | Cliente | Cuenta | PAGO | Párrafos | Ver mi reserva → detalle | `REQUEST` si `reserva_confirmada` |
| `pago_rechazado` | Cliente | Cuenta | PAGO | Párrafos | Ver mi reserva → detalle | No |
| `reserva_finalizada_saldo` | Cliente | Cuenta | RESERVA | Párrafos y lista | Ver mi reserva → detalle | No |
| `reserva_cancelada_estudio` | Cliente | Cuenta | RESERVA | Párrafos | Ver mi reserva → detalle | `CANCEL` si tiene evento |
| `reserva_cancelada_cliente` | Administrador | Administración | RESERVA | Tabla | Ver la reserva → detalle | No |
| `reserva_cancelada_con_pagos` | Cliente | Cuenta | RESERVA | Tabla | Ver mi reserva → detalle | `CANCEL` si tiene evento |
| `reserva_reprogramada` | Cliente | Cuenta | RESERVA | Tabla (si hay costo) | Ver mi reserva → detalle | `REQUEST` si tiene evento |
| `inasistencia_marcada` | Cliente | Cuenta | RESERVA | Párrafos | Ver mi reserva → detalle | No |
| `eleccion_estudio_resuelta` | Administrador | Administración | RESERVA | Párrafos | Ver la reserva → detalle | No |
| `credito_por_vencer` | Cliente | Cuenta | CRÉDITO | Párrafos | Ver mis créditos → `{url}/app/reservas/creditos` | No |
| `devolucion_solicitada` | Administrador | Administración | DEVOLUCIÓN | Párrafos | Revisar la devolución → `{url}/app/pagos/devoluciones/revisar?id={id_devolucion}` | No |
| `devolucion_decidida` | Cliente | Cuenta | DEVOLUCIÓN | Párrafos | Ver mis créditos → `{url}/app/reservas/creditos` | No |
| `devolucion_realizada` | Cliente | Cuenta | DEVOLUCIÓN | Párrafos | Ver mis créditos → `{url}/app/reservas/creditos` | No |
| `texto_legal_nuevo` | Toda cuenta | Cuenta | TEXTOS LEGALES | Párrafos | Leer el texto → `{url}/legal/{ruta}/` | No |

- "Detalle" es `{url}/app/reservas/detalle?id={id_reserva}`; el personal y el Administrador también lo abren ([mis reservas](../pantallas/RF-04-mis-reservas.md)).
- `texto_legal_nuevo`, `{ruta}` según `tipo`: `terminos_uso` → `terminos-de-uso`, `politica_privacidad` → `privacidad`, `condiciones_contratacion` → `condiciones-de-contratacion`, `declaracion_agrupacion` → `declaracion-de-agrupacion` ([textos legales](../pantallas/RF-17-textos-legales.md)).
- "Tiene evento" y el contenido del bloque de calendario: [evento de calendario](evento-calendario.md#qué-avisos-lo-llevan).
- La etiqueta se pinta como `// RESERVA` en el HTML y en el texto plano.
- Un tipo nuevo de aviso añade su fila aquí antes de implementarse; sin fila, usa etiqueta AVISO, botón "Ir a la plataforma" → `{url}/app` y pie Cuenta.

## Del texto al HTML

El cuerpo de `redactar()` es texto plano. La plantilla lo convierte de forma mecánica, sin cambiar palabras:

1. Escapa todo el texto con `html.escape`.
2. Separa bloques por líneas en blanco.
3. Dentro de cada bloque, agrupa líneas consecutivas del mismo tipo:
   - **Lista:** líneas que empiezan por `- ` → un `<ul>` con un `<li>` por línea (sin el guion).
   - **Tabla de datos:** dos o más líneas seguidas de la forma `Clave: valor`, con una clave de 1 a 40 caracteres, sin `:` y que empieza por mayúscula → una tabla clave-valor (`<th scope="row">` con la clave, `<td>` con el valor).
   - **Párrafo:** el resto, incluida una línea `Clave: valor` aislada ("Motivo: …", "Qué cambia: …") y la que termina en `:` ("Datos para pagar:"); líneas seguidas se unen con `<br>`.
4. La lista tiene prioridad sobre la tabla ("- Yape: …" es un elemento de lista).
5. La previsualización usa el primer bloque de párrafo.

Ejemplos con los avisos actuales: `reserva_creada` da párrafo, tabla (Folio, Servicio, Fecha y hora, Total), párrafo (fecha límite y caducidad), párrafo "Datos para pagar:" y lista; `pago_registrado` da párrafo, tabla de seis filas y el párrafo de verificación del monto.

El texto plano no se convierte: va tal cual.
