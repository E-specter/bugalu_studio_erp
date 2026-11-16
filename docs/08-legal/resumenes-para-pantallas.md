---
id: legal-resumenes-pantallas
titulo: Resúmenes de los textos legales para cada aceptación
estado: borrador
version: 0.1.0
vigente_desde: por definir
depende_de: [ADR-012, RF-01, RF-04, RF-05, RF-15, RF-17, RF-18]
---

# Resúmenes para las pantallas de aceptación

> **Borrador para revisión legal. No es asesoría legal ni está vigente.** Debe revisarlo el mismo abogado que revise los textos completos ([ADR-012](../00-proyecto/decisiones/ADR-012-textos-legales-y-consentimientos.md)).

Antes de cada aceptación, la interfaz muestra el resumen de su paso, un enlace al texto completo con su versión y una casilla. Reglas para todas las pantallas:

- Las casillas **nunca vienen marcadas** y rechazar es tan fácil como aceptar (sin presión ni botones engañosos: art. 56.1 h del Código de Protección y Defensa del Consumidor).
- La política de privacidad se **lee**, no se "acepta": informa del tratamiento necesario para el contrato. Solo los consentimientos opcionales (promociones, autorizaciones de imagen) llevan casilla propia.
- La plataforma guarda qué versión aceptó cada quien, cuándo y en qué paso ([README](README.md)).
- Los valores entre corchetes salen de los parámetros vigentes; "[cifra por confirmar]" sigue pendiente en las [Condiciones de contratación](condiciones-de-contratacion.md).

## Registro

**Resumen:** Para crear tu cuenta te pedimos datos verdaderos: documento de identidad, contacto, domicilio y redes. Los usamos para gestionar tus reservas, pagos y avisos, se guardan en un servidor del estudio y solo los compartimos con quienes nos ayudan a prestarte el servicio, como Google para los correos. Puedes ver, corregir o pedir que borremos tus datos cuando quieras.

**Casilla (obligatoria):** "Acepto los [Términos de uso](terminos-de-uso.md) (versión 0.1.0) y he leído la [Política de privacidad](politica-de-privacidad.md) (versión 0.1.0)."

**Si es una agrupación, casilla adicional (obligatoria):** "Declaro que represento a la agrupación, que sus integrantes me autorizaron a contratar por ella y a dar sus datos, y que conocen estos textos."

## Registro de un menor de edad

**Resumen:** Si eres menor de 18 años, tu madre, padre o tutor autoriza tu registro y contrata por ti. Debe subir la autorización firmada con una copia de su documento, y un adulto responsable debe estar contigo en el estudio durante toda la sesión. No usamos tu imagen ni tu voz en promociones sin su permiso expreso.

**Casilla (obligatoria, la marca el adulto):** "Soy la madre, el padre o el tutor del menor, autorizo su registro y acepto los [Términos de uso](terminos-de-uso.md) y las [Condiciones de contratación](condiciones-de-contratacion.md) en su nombre."

## Reserva de sala

**Resumen:** El precio que ves incluye el IGV y queda fijo al reservar. Para confirmar tu reserva pagas el adelanto antes del [fecha y hora límite]; si no registras un pago para entonces, se cancela sola y sin costo. Sin pagos puedes cancelar gratis; con pagos, se aplica una retención o un crédito según la anticipación con que avises. Las grabaciones de tus másteres y entregables pactados son tuyas, y el estudio puede usar fragmentos breves para su promoción, con los límites de las condiciones.

**Casilla (obligatoria):** "Acepto las [Condiciones de contratación](condiciones-de-contratacion.md) (versión 0.1.0), incluida la [propiedad intelectual de las grabaciones](condiciones-propiedad-intelectual.md)."

## Asesoría

**Resumen:** La asesoría tiene un precio fijo con IGV incluido, que pagas por adelantado en un solo pago; queda confirmada cuando validamos tu pago. Si es virtual, recibes el enlace de Google Meet en tu correo. Si no asistes, no hay devolución; si avisas con anticipación, se aplica la política de cancelación por niveles.

**Casilla (obligatoria):** "Acepto las [Condiciones de contratación](condiciones-de-contratacion.md) (versión 0.1.0)."

## Registro de un pago

**Resumen:** Una persona del estudio revisa tu pago a mano antes de confirmarlo y te avisa por correo. Si lo rechazamos, te diremos el motivo y tendrás al menos 1 hora más para registrar otro. Guardamos la captura de forma indefinida y segura, como evidencia del pago; solo tú y el Administrador pueden verla.

**Sin casilla:** el resumen va junto al botón de registrar el pago, con enlace a la [Política de privacidad](politica-de-privacidad.md).

## Promociones

**Resumen:** Es opcional y no cambia nada de tu servicio. Te enviaremos novedades, ofertas y eventos, algunos elegidos según los servicios que usaste, por correo y, si lo marcas, por WhatsApp. Puedes darte de baja cuando quieras desde cualquier correo o desde tu perfil.

**Casillas (opcionales, separadas):** "Quiero recibir promociones por correo." · "Quiero recibir promociones por WhatsApp." [verificar canal: art. 58.1 e del Código del Consumidor]

## Cancelar o reprogramar

**Resumen (se arma con los datos de la reserva):** Faltan [horas] para tu sesión: estás en el nivel [n]. Si cancelas, se retiene [monto] y [monto] pasa a crédito, válido hasta [fecha]; si reprogramas, [costo]. Esta acción no se puede deshacer.

**Confirmación:** botón "Cancelar reserva" o "Reprogramar", con un segundo botón igual de visible "Volver sin cambios".
