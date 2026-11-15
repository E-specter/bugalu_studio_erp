---
id: ADR-008
titulo: Acceso, registro y roles de la v1
estado: aprobado
depende_de: [D-10, ADR-005]
---

# ADR-008: Acceso, registro y roles de la v1

## Contexto

RF-01 pide registro, inicio de sesión y perfiles con privilegios diferenciados ([ADR-005](ADR-005-supabase-auth.md): Supabase Auth con roles `cliente`, `personal` y `administrador`). Figma diseña dos accesos (artista e interno), dos registros (proyecto artístico y "Solicitar acceso" interno) y la recuperación de contraseña. D-10 preguntaba si sello o mánager y músico de sesión son roles del sistema. El visitante crea su cuenta al reservar o agendar ([flujo](../../02-dominio/flujos/registrar-reserva.md)).

## Opciones consideradas

- D-10: roles propios para mánager y músico de sesión (relación mánager–artistas, reglas por proyecto en varias tablas, toca RF-01, 04, 05, 08, 09 y 10) **o fuera de la v1**.
- Personal interno: **solicitud desde el registro interno y aprobación del administrador** o invitación del administrador.
- Confirmación del correo: antes de iniciar sesión o **antes del primer pago**.
- Acceso con Google: no, para todos o **solo para artistas y clientes**.

## Decisión

Usuario, 2026-11-15:

| Tema | Decisión |
|---|---|
| Sello o mánager y músico de sesión (D-10) | **Fuera de la v1.** Sello o mánager y músico de sesión no tienen cuenta; si hace falta, figuran como datos del proyecto. Mejora posible: colaboradores invitados por proyecto (RF-08) |
| Personal interno | Solicita acceso desde el registro interno; queda pendiente hasta que el Administrador aprueba (asigna rol y especialidad) o rechaza con motivo |
| Correo | El cliente inicia sesión y reserva sin confirmar; **confirmar el correo es obligatorio antes del primer pago** ([RF-05](../../03-requerimientos/RF-05.md)) |
| Primer administrador | Con un comando de mantenimiento (CLI), no desde la web |
| Perfil | Nombre y teléfono para todos; nombre artístico para el cliente. Rol y especialidad solo los cambia el Administrador |
| Contraseña | Mínimo 8 caracteres con minúsculas, mayúsculas, números y símbolos, exigido por Supabase Auth; medidor de robustez en el formulario; recuperación por correo |
| Google | Solo artistas y clientes. El personal entra siempre con correo y contraseña. Sin costo: permisos básicos (`openid`, `email`, `profile`) sin verificación de Google; incluido en todos los planes de Supabase |

## Consecuencias

- Tres roles de sistema; las reglas de acceso siguen siendo por dueño y por rol.
- Nueva tabla de solicitudes de acceso interno y columnas `telefono` y `nombre_artistico` en `usuario` ([modelo-datos](../../01-arquitectura/modelo-datos.md)).
- El perfil expone si el correo está verificado; RF-05 lo exige antes de registrar el primer pago. Quien entra con Google ya tiene el correo verificado.
- **Ajuste técnico (leader, 2026-11-15):** el CLI de Supabase local no permite iniciar sesión con el correo sin confirmar (o lo exige, o lo confirma al registrar). Para mantener la decisión igual en local y en producción, Supabase confirma al registrar y la verificación se lleva en `usuario.correo_verificado_en`, que solo escribe una función de la base cuando la sesión viene de un enlace de correo de un solo uso o de Google. Para el usuario es una confirmación por enlace como cualquier otra.
- Google necesita un cliente OAuth en Google Cloud Console (paso del usuario); mientras no exista, el botón no se muestra y nada más cambia.
- Ampliar roles más adelante es una migración (la restricción `rol in (…)`) más las reglas de acceso del RF afectado.
