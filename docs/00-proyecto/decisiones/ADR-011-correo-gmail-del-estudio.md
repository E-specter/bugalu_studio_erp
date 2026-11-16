---
id: ADR-011
titulo: Correo saliente con la cuenta de Google del estudio
estado: aprobado
depende_de: [D-07, ADR-009]
---

# ADR-011: Correo saliente con la cuenta de Google del estudio

## Contexto

Los avisos de reservas y pagos salen de la bandeja `notificacion` por SMTP ([ADR-009](ADR-009-reservas-tarifas-y-caducidad.md)); en local llegan a Mailpit. Supabase Auth también envía correos (confirmación, restablecer contraseña, enlaces de un solo uso). Faltaba el proveedor real (D-07).

## Decisión

Usuario, 2026-11-16: el correo del estudio es la cuenta de Google `somos.bugalu.studio@gmail.com`.

- **Envío:** SMTP de Gmail (`smtp.gmail.com`, puerto 587 con STARTTLS) autenticado con una **contraseña de aplicación** de esa cuenta (exige la verificación en dos pasos). La contraseña nunca se versiona: va en el entorno del backend y del servicio de Auth.
- **Quién lo usa:** el backend para los avisos de la bandeja y Supabase Auth para sus correos, ambos con el mismo remitente.
- **Local:** Mailpit sigue siendo el destino en desarrollo y pruebas; nada se envía de verdad.

## Consecuencias

- El adaptador SMTP del backend admite STARTTLS y credenciales por variables de entorno, sin cambiar Mailpit en local.
- El procedimiento (verificación en dos pasos, contraseña de aplicación, variables, prueba) se documenta en `docs/06-operacion/`.
- Una cuenta personal de Gmail tiene un límite diario de envíos (del orden de cientos de destinatarios). Si el volumen crece, se pasa a Google Workspace o a un proveedor transaccional cambiando solo la configuración.
- La conexión con Google Calendar se decide aparte, según lo que el estudio quiera sincronizar.
