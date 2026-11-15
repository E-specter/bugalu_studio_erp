---
id: glosario
titulo: Glosario
estado: borrador
depende_de: []
---

# Glosario

## Salas técnicas

| Sala | Uso |
|---|---|
| Sala A | Grabación |
| Sala B | Mezcla / Masterización |
| Sala C | Cabina / Posproducción |

## Servicios del catálogo

Grabación acústica · Mezcla · Masterización · Live sessions.

## Términos

| Término | Definición |
|---|---|
| Anticipo | Cuota `al_reservar` (50%) que, validada, confirma una reserva de sala ([RN-03](../02-dominio/reglas-negocio.md)). |
| Liquidación | Cuota final: al terminar la sesión o el ensayo ([RN-13](../02-dominio/reglas-negocio.md)), o al aprobar la mezcla o el máster en posproducción ([RN-05](../02-dominio/reglas-negocio.md)). |
| Franja | Ventana de disponibilidad de una sala que publica el estudio cada semana ([RN-12](../02-dominio/reglas-negocio.md)). |
| Tramo | Parte de una franja que reserva un cliente, en múltiplos de 30 min. |
| Cuota | Parte de un pago con monto y fecha o hito (`al_reservar`, `al_terminar`, `al_encargar`, `al_aprobar_version`); se paga con un comprobante validado ([RN-04](../02-dominio/reglas-negocio.md)). |
| Asesoría | Cita de precio fijo con un profesional artístico, presencial o virtual, para orientar la producción y acordar precio o convenio ([RN-14](../02-dominio/reglas-negocio.md)). |
| Simulación de precio | Estimación pública y no vinculante del costo de una reserva ([RN-15](../02-dominio/reglas-negocio.md)). |
| Cotización a medida | Cotización formal posterior a una asesoría, con plan de cuotas propio que reemplaza el 50/50 ([RN-16](../02-dominio/reglas-negocio.md)). |
| Visitante | Persona sin cuenta que consulta franjas y simula precios. |
| Buffer técnico | Bloqueo automático de 30 min tras cada reserva para desinfección y calibración ([RN-02](../02-dominio/reglas-negocio.md)). |
| Folio | Identificador de reserva que se entrega al cliente. |
| Multipistas / stems | Pistas WAV de alta resolución separadas por instrumento o fuente. |
| Máster | Versión final aprobada del audio, descargable tras validar la cuota final de posproducción ([RN-06](../02-dominio/reglas-negocio.md)). |
| Ronda de corrección | Ciclo de observaciones del cliente sobre una versión; cada proyecto tiene un límite pactado ([RN-10](../02-dominio/reglas-negocio.md)). |
| Observación técnica | Comentario del cliente anclado a un instante (`marca_tiempo_ms`) de una versión de audio. |
| CUS | Caso de uso del sistema (informe RUP). |
| BCE | Análisis Boundary–Control–Entity del informe RUP. |
| RF / RN / D | Requerimiento funcional / regla de negocio / decisión abierta. |
| ADR | Registro de decisión de arquitectura, en [decisiones/](decisiones/README.md). |

Los estados de reserva están en [estados-reserva](../02-dominio/estados-reserva.md).
