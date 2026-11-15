---
id: actores-roles
titulo: Actores del sistema
estado: borrador
depende_de: [D-10]
---

# Actores del sistema

| Actor | Tipo | Descripción |
|---|---|---|
| Visitante | Humano (sin cuenta) | Consulta franjas y simula precios; crea su cuenta al reservar o agendar una asesoría |
| Artista / Cliente | Humano | Músico, banda o artista independiente que contrata servicios |
| Ingeniero de Audio | Humano (personal interno) | Ingeniero de grabación, operador de mezcla o asistente de cabina |
| Profesional artístico | Humano (personal interno) | Da asesorías (presenciales o virtuales) y publica sus horarios; rol `personal` con especialidad `asesoria` ([ADR-005](../00-proyecto/decisiones/ADR-005-supabase-auth.md)) |
| Administrador | Humano | Gestiona operación, franjas, personal, estados, validación de pagos y reportes |
| Banco / billetera | Externo, sin integración | Donde el cliente paga (transferencia, Yape, Plin, tarjeta); el sistema solo recibe la captura ([ADR-004](../00-proyecto/decisiones/ADR-004-pagos-validacion-manual.md)) |
| Almacenamiento Cloud | Sistema externo | Supabase Storage: custodia multipistas, mezclas, másteres y capturas de pago ([ADR-003](../00-proyecto/decisiones/ADR-003-almacenamiento-supabase-storage.md)) |

Actores de negocio sin rol definido en el sistema: Sello discográfico / Mánager y Músico de sesión (D-10, ver [decisiones](../00-proyecto/decisiones/README.md)).

Los privilegios por rol se definen en [RF-01](../03-requerimientos/RF-01.md).
