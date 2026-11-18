---
id: pantalla-rf-16-correos
titulo: Pantalla — Correos del Libro de Reclamaciones (contenido)
estado: aprobado
depende_de: [RF-16, ADR-016, correo-plantilla, correo-avisos, pantalla-rf-16-bandeja]
---

# Correos del Libro de Reclamaciones

| Campo | Valor |
|---|---|
| Requerimiento | [RF-16](../../03-requerimientos/RF-16.md): CA-05 (copia y aviso), CA-07 (respuesta por correo), CA-08 (plazos) |
| Envoltorio | [Plantilla de marca](../correos/plantilla.md) sin cambios; aquí solo asunto, cuerpo, botón y pie de cada aviso. El cuerpo es el texto de `redactar()` y la plantilla lo convierte con las [reglas de siempre](../correos/avisos.md#del-texto-al-html) |
| Evento de calendario | Ninguno de estos avisos lo lleva |

## Por tipo

Nombres de tipo propuestos para `notificacion` (los fija dev-backend). Etiqueta de todos: `// LIBRO DE RECLAMACIONES`.

| Tipo | Para | Cuándo | Pie | Botón: texto → destino |
|---|---|---|---|---|
| `reclamacion_registrada` | Correo del consumidor | Al registrar una hoja web (y transcrita con correo, ver Preguntas) | Reclamo (abajo) | Con cuenta: "Ver mi hoja" → `{url}/app/reclamos/detalle?id={id}` · sin cuenta: "Escribirnos por WhatsApp" → `https://wa.me/51925530800` |
| `reclamacion_recibida` | Cada Administrador | Al registrar una hoja web | Administración | "Revisar la hoja" → `{url}/app/reclamos/detalle?id={id}` |
| `reclamacion_respondida` | Correo del consumidor | Al responder con medio correo | Reclamo | Como `reclamacion_registrada` |
| `reclamaciones_por_vencer` | Cada Administrador | Cada día hábil, solo si hay hojas | Administración | "Ver hojas pendientes" → `{url}/app/reclamos/?estado=pendiente` |

**Pie Reclamo (nuevo):** el Cuenta dice "porque tienes una cuenta", y quien reclama puede no tenerla. Igual que Cuenta salvo: enlaces útiles sin "Mis reservas"; motivo "Te enviamos este correo porque presentaste una hoja en el Libro de Reclamaciones de Bugalú Studio." (ver Preguntas).

## Formato de los valores

Fechas `D MMM AAAA` y fecha y hora `D MMM AAAA, HH:mm` en hora de Lima; importes `S/ 1 250,00`; opcional vacío "—". Los valores de una línea `Clave: valor` van en una sola línea (los saltos del consumidor se cambian por espacios); DETALLE, PEDIDO y la respuesta van como párrafo propio y conservan sus saltos. `{tipo}` es "reclamo", "queja" u "hoja" (sin marcar).

## `reclamacion_registrada`

Asunto: "Hoja de reclamación N.º {numero}". Cuerpo (la copia de la hoja que pide CA-05, en el orden del Anexo I):

```
Registramos tu {tipo} en el Libro de Reclamaciones de Bugalú Studio. Esta es la copia de tu hoja. Te responderemos por {correo electrónico | carta a tu domicilio} a más tardar el {vence_respuesta}.

Hoja N.º: {numero}
Fecha y hora: {creada_en}
Proveedor: Aural Perú E.I.R.L.
RUC: 20615656128
Domicilio del proveedor: Av. Javier Prado Este 5920, La Molina, Lima

1. Identificación del consumidor reclamante

Nombre: {nombre}
Documento: {DNI | CE | Pasaporte} {documento}
Domicilio: {domicilio}
Teléfono: {telefono | —}
Correo: {correo}
Menor de edad: {Sí | No}

Madre, padre o tutor                     ← solo si es menor, con su tabla:
Nombre / Domicilio / Teléfono / Correo

2. Identificación del bien contratado

Producto o servicio: {Producto | Servicio}
Monto reclamado: {monto | No indicado}
Descripción: {descripcion | —}

3. Detalle de la reclamación y pedido del consumidor

Tipo: {Reclamo | Queja | Sin marcar}
Medio para la respuesta: {Correo electrónico | Carta al domicilio}
Adjuntos: {nombres separados por coma | Ninguno}

Detalle:
{detalle}

Pedido:
{pedido}

RECLAMO: Disconformidad relacionada a los productos o servicios.
QUEJA: Disconformidad no relacionada a los productos o servicios; o, malestar o descontento respecto a la atención al público.

La formulación del reclamo no impide acudir a otras vías de solución de controversias ni es requisito previo para interponer una denuncia ante el INDECOPI.
El proveedor deberá dar respuesta al reclamo o queja en un plazo no mayor a quince (15) días hábiles improrrogables.
```

Las definiciones y leyendas son las del [formulario](RF-16-formulario.md#textos-del-anexo-i): si el abogado las cambia, cambian aquí.

## `reclamacion_recibida`

Asunto: "Nueva hoja de reclamación N.º {numero}".

```
Llegó una hoja al Libro de Reclamaciones. Respóndela a más tardar el {vence_respuesta}: el plazo de 15 días hábiles no se prorroga.

Hoja N.º: {numero}
Tipo: {Reclamo | Queja | Sin marcar}
Consumidor: {nombre}
Presentada: {creada_en}
Medio para la respuesta: {Correo electrónico | Carta al domicilio}
Adjuntos: {cantidad | Ninguno}
```

Solo el nombre: el resto de datos personales se lee en la plataforma.

## `reclamacion_respondida`

Asunto: "Respuesta a tu hoja de reclamación N.º {numero}".

```
Respondimos tu {tipo} N.º {numero}, presentado el {creada_en, solo fecha}.

Nuestra respuesta:
{texto}

Hoja N.º: {numero}
Fecha de la respuesta: {enviada_en}

La formulación del reclamo no impide acudir a otras vías de solución de controversias ni es requisito previo para interponer una denuncia ante el INDECOPI.
```

Con medio carta no hay correo: la respuesta va por carta (CA-07).

## `reclamaciones_por_vencer`

Asunto: "{n} hojas de reclamación por responder" (1: "1 hoja de reclamación por responder").

```
Estas hojas vencen en 5 días hábiles o menos, o ya vencieron. Respóndelas en la plataforma.

- N.º {numero} · {Reclamo | Queja | Sin marcar} · fuera de plazo desde el {vence_respuesta}
- N.º {numero} · {tipo} · vence hoy
- N.º {numero} · {tipo} · vence el {vence_respuesta} (en {N} días hábiles)
```

Orden: fuera de plazo primero y luego por `vence_respuesta`. Sin hojas en esa ventana, no se envía.

## Preguntas para leader

Resueltas (leader, 2026-11-17): la 1 ya está en avisos y en la plantilla; la 2, sí (Precisión 8).

1. **documentador:** sumar las cuatro filas a [avisos](../correos/avisos.md#por-tipo) y el pie Reclamo a la [plantilla](../correos/plantilla.md#pie-copy-fijo); la tarea solo permite escribir en `pantallas/` y `componentes/`.
2. **Hoja transcrita con correo:** ¿se envía `reclamacion_registrada`? Propuesta: sí; el consumidor recibe el número de la app. No se avisa al Administrador (la registró él).
