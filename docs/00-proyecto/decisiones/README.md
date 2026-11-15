# Decisiones

Registro de decisiones abiertas. Cuando una se cierra, se crea `ADR-<nnn>-<tema>.md` en esta carpeta con la plantilla de abajo, y su fila se actualiza con el enlace.

## Decisiones abiertas

| ID | Decisión | Opciones / contexto | ADR |
|---|---|---|---|
| D-01 | Almacenamiento de audio | El informe indica AWS S3; Supabase Storage es compatible con S3 y unifica el stack | — |
| D-02 | Pasarela de pagos | Sin definir | — |
| D-03 | Autenticación | Supabase Auth (sin `password_hash` propio) vs. autenticación propia en FastAPI (el informe asume `passwordHash`) | — |
| D-04 | Tipo de clave primaria | UUID (alineado con Supabase Auth) vs. entero (informe) | — |
| D-05 | Límite por defecto de rondas de corrección | Sin definir | — |
| D-06 | Caducidad de una reserva `Pre-reservada` sin pago | Sin definir | — |
| D-07 | Proveedor de correo transaccional | Sin definir | — |
| D-08 | Hosting de backend y frontend | Sin definir | — |
| D-09 | Moneda, impuestos y facturación electrónica | El informe menciona "comprobante fiscal"; alcance sin definir | — |
| D-10 | Sello/Mánager y Músico de sesión | ¿Roles del sistema o fuera de alcance v1? | — |
| D-11 | Políticas de cancelación y reembolso del anticipo | Sin definir | — |
| D-12 | Asignación de personal | El informe usa `idIngeniero` único en `reserva`; RF-07 exige varios roles por sesión | — |
| D-13 | Archivo y plan de Figma | URL del archivo maestro, plan y asiento (determinan límites de uso del MCP) | **Cerrada:** [ADR-001](ADR-001-figma-fuente-extraccion.md) |
| D-14 | Code Connect de Figma | Vincular componentes de Figma con el código; aporta precisión pero exige mantenimiento | **Cerrada:** [ADR-002](ADR-002-code-connect-descartado.md) |

Prioridad (hoja de ruta, fase 1): D-01 a D-04.

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
