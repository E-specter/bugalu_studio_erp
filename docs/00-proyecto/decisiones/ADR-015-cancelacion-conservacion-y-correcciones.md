---
id: ADR-015
titulo: Cancelación y reprogramación por niveles, conservación de datos y rondas de corrección
estado: aprobado
depende_de: [D-05, D-11, ADR-010, ADR-012]
---

# ADR-015: Cancelación y reprogramación por niveles, conservación de datos y rondas de corrección

## Contexto

Quedaban abiertas la política de cancelación y devolución (D-11), las rondas de corrección (D-05) y las cifras que los borradores legales dejaron por confirmar ([docs/08-legal](../../08-legal/README.md)).

## Decisión

Usuario, 2026-11-16:

| Tema | Decisión |
|---|---|
| Adelanto | 50 % (configurable con barreras, [ADR-013](ADR-013-impuestos-y-parametros-sensibles.md)) |
| Nivel 1 (> 48 h) | Hasta 2 reprogramaciones por reserva sin cargo; todo lo pagado queda como crédito. La devolución se solicita en la app con motivo y la decide el Administrador (total, parcial o rechazo con motivo); el dinero se devuelve fuera de la app |
| Nivel 2 (24–48 h) | Una sola reprogramación, que también cobra la penalización; penalización del 25 % del valor de la reserva, que el adelanto del 50 % siempre cubre; crédito = lo pagado − la penalización; sin devolución |
| Nivel 3 (< 24 h) | Sin reprogramación gratuita; se retiene lo pagado |
| Inasistencia | 15 min de tolerancia; luego se retiene lo pagado, sin crédito ni cobro adicional. El tiempo no usado por llegar tarde no se recupera |
| Crédito | Vigencia de 30 días con aviso 7 días antes; se pierde al vencer; solo para el mismo cliente, en cualquier reserva de sala o asesoría |
| Cancelación del estudio | Nueva fecha sin costo o devolución íntegra en 7 días hábiles |
| En la app | Botón "solicitar cancelación" que aplica la política (evita obligar a pedirlo por fuera) |
| Plazos | 48 h y 24 h configurables con barreras |
| Pago en validación al llegar la hora | La sesión empieza si el estudio verifica el pago en ese momento; si no puede verificarlo, no empieza y, pasados 15 min, aplica la inasistencia (usuario, 2026-11-17) |
| Saldo | Se paga hasta 48 h después de la sesión; los entregables se retienen hasta entonces |
| Asesorías | Solo de 30 o 60 min; misma política de reprogramación por niveles sin devolución; sin pagar caducan como la sala (RN-18) |
| Comprobantes | Boletas y facturas fuera de la app; la app anota el número |
| Validación de pagos | Lunes a sábado de 9:00 a 20:00; fuera de horario, al día siguiente |
| Conservación | Capturas de pago: 5 años y luego se borran solo las capturas. Archivos de proyecto: se borran de producción a los 12 meses de la última entrega, con aviso, y se conservan en una copia de respaldo fuera de producción. Aceptaciones y autorizaciones de menores: 12 meses en producción (el abogado confirma si basta) y archivadas en respaldo fuera de producción. Cuenta cerrada: anonimizada a los 90 días salvo obligación legal. Registros técnicos: 90 días |
| Registro | Agrupación con responsable titular e integrantes (nombre y rol); DNI, CE o pasaporte antes de la primera reserva; obligatorios nombre, documento, teléfono y correo; opcionales domicilio y redes |
| Menores | El tutor registra sus datos y documento, acepta en la app y sube el documento firmado; la reserva no se confirma sin validarlo; sin el adulto responsable, la sesión no empieza y tras 15 min aplica la inasistencia |
| Propiedad intelectual | Multipistas WAV de la sesión incluidos y de propiedad del artista (usuario, 2026-11-17); másteres solo con posproducción; fragmentos promocionales de hasta 30 s; fotos y videos solo con autorización aparte (casilla sin marcar); exclusión desde el inicio; retiro de una publicación en 10 días hábiles |
| Textos legales | Cambios avisados 15 días antes; un cambio mayor exige volver a aceptar |
| Correos | Solo los de la plataforma, con `.ics` y una plantilla con el diseño de la marca e información útil de la empresa (sin invitación propia de Google). Meet gratuito |
| Cotización | Vigencia de 15 días |
| Rondas de corrección (D-05) | Máximo 3 cambios grandes de mezcla y 3 de máster |

## Consecuencias

- D-11 y D-05 quedan cerradas. [RF-18](../../03-requerimientos/RF-18.md) implementa la política; RN-20 se reescribe con ella.
- Los borradores de `docs/08-legal/` sustituyen sus "[cifra por confirmar]" por estas cifras.
- Operaciones recibe la lista de requisitos empresariales (marca en Indecopi, banco de datos ante la Autoridad de Protección de Datos y demás).
