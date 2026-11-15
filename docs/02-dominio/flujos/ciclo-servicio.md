---
id: flujo-ciclo-servicio
titulo: Ciclo de servicio
estado: borrador
depende_de: [reglas-negocio, estados-reserva]
---

# Ciclo de servicio

1. **Contratación:** catálogo → cotización → reserva (`Pre-reservada`) → anticipo 50% → `Confirmada`.
2. **Producción:** asignación de personal → calibración en buffer → sesión → respaldo de multipistas.
3. **Posproducción y cierre:** carga de versión → auditoría del cliente con observaciones por timestamp → aprobación → liquidación 50% → descarga del máster (7 días) → evaluación de satisfacción.

Flujos críticos detallados: [registrar-reserva](registrar-reserva.md) · [versionado-feedback](versionado-feedback.md).
