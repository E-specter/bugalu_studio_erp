# Decisiones

Registro de decisiones abiertas. Cuando una se cierra, se crea `ADR-<nnn>-<tema>.md` en esta carpeta con la plantilla de abajo, y su fila se actualiza con el enlace.

## Decisiones abiertas

| ID | Decisión | Opciones / contexto | ADR |
|---|---|---|---|
| D-01 | Almacenamiento de audio | El informe indica AWS S3; Supabase Storage es compatible con S3 y unifica el stack | **Cerrada:** [ADR-003](ADR-003-almacenamiento-supabase-storage.md) |
| D-02 | Pasarela de pagos | Perú (PEN); hoy se valida cada pago con su captura | **Cerrada:** [ADR-004](ADR-004-pagos-validacion-manual.md) |
| D-03 | Autenticación | Supabase Auth (sin `password_hash` propio) vs. autenticación propia en FastAPI (el informe asume `passwordHash`) | **Cerrada:** [ADR-005](ADR-005-supabase-auth.md) |
| D-04 | Tipo de clave primaria | UUID (alineado con Supabase Auth) vs. entero (informe) | **Cerrada:** [ADR-006](ADR-006-claves-uuid.md) |
| D-05 | Límite por defecto de rondas de corrección | Sin definir | — |
| D-06 | Caducidad de una reserva `Pre-reservada` sin pago | 3 días antes o 1 hora, ajustables | **Cerrada:** [ADR-009](ADR-009-reservas-tarifas-y-caducidad.md) (reservas de sala) |
| D-07 | Proveedor de correo transaccional | Sin definir | — |
| D-08 | Hosting de backend y frontend | Sin definir | — |
| D-09 | Moneda, impuestos y facturación electrónica | Moneda **PEN** decidida ([ADR-004](ADR-004-pagos-validacion-manual.md)); boleta o factura fuera de la v1 ([ADR-010](ADR-010-pagos-estados-y-cancelacion.md)); impuestos sin definir | Parcial |
| D-10 | Sello/Mánager y Músico de sesión | ¿Roles del sistema o fuera de alcance v1? | **Cerrada:** [ADR-008](ADR-008-acceso-y-roles-v1.md) (fuera de la v1) |
| D-11 | Políticas de cancelación y reembolso del anticipo | v1: el cliente con pagos lo pide al estudio; el Administrador cancela con nota del reembolso gestionado fuera; política de devolución sin definir | **Parcial:** [ADR-010](ADR-010-pagos-estados-y-cancelacion.md) |
| D-12 | Asignación de personal | El informe usa `idIngeniero` único en `reserva`; RF-07 exige varios roles por sesión | — |
| D-13 | Archivo y plan de Figma | URL del archivo maestro, plan y asiento (determinan límites de uso del MCP) | **Cerrada:** [ADR-001](ADR-001-figma-fuente-extraccion.md) |
| D-14 | Code Connect de Figma | Vincular componentes de Figma con el código; aporta precisión pero exige mantenimiento | **Cerrada:** [ADR-002](ADR-002-code-connect-descartado.md) |

**Decisiones sin fila D previa:** [ADR-007](ADR-007-acceso-postgres-directo.md) (acceso a PostgreSQL directo con RLS por transacción, fase 3).

D-01 a D-04 se cerraron en la fase 1 con la [spec de contratación](../../superpowers/specs/2026-11-15-contratacion-y-decisiones-design.md).

## Plantilla de ADR

```markdown
---
id: ADR-<nnn>
titulo: <decisión>
estado: aprobado
depende_de: [D-xx]
---

# ADR-<nnn>: <decisión>

## Contexto
## Opciones consideradas
## Decisión
## Consecuencias
```
