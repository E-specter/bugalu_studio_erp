---
id: flujo-ciclo-servicio
titulo: Ciclo de servicio
estado: borrador
depende_de: [reglas-negocio, estados-reserva]
---

# Ciclo de servicio

```
Visitante ─► ve franjas y simula precio (sin cuenta)
          ├─► reserva tramo de sala ─► crea cuenta ─► Pre-reservada ─► paga 50% + captura
          │        └─► Admin valida ─► Confirmada ─► En curso ─► Finalizada ─► paga 50% restante
          └─► agenda asesoría (precio fijo, pago único) ─► Admin valida ─► Confirmada ─► Realizada
                   └─► cotización a medida (plan de cuotas) ─► cliente acepta ─► reserva contra ella
Posproducción: 50% al encargar ─► versiones y observaciones ─► 50% al aprobar ─► Admin valida ─► descarga del máster (7 días)
```

1. **Contratación:** franjas y simulación → reserva de sala ([registrar-reserva](registrar-reserva.md)) o asesoría ([agendar-asesoria](agendar-asesoria.md)) → cuota validada → `Confirmada`.
2. **Producción:** asignación de personal → calibración en buffer → sesión → respaldo de multipistas → cuota `al_terminar`.
3. **Posproducción y cierre:** cuota `al_encargar` → carga de versión → auditoría del cliente con observaciones por timestamp ([versionado-feedback](versionado-feedback.md)) → aprobación → cuota `al_aprobar_version` → descarga del máster (7 días) → evaluación de satisfacción.

Reglas: [reglas-negocio](../reglas-negocio.md). Estados: [estados-reserva](../estados-reserva.md).
