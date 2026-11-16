---
id: ADR-012
titulo: Textos legales, consentimientos versionados, menores y registro reforzado
estado: aprobado
depende_de: [ADR-008, ADR-009, ADR-010]
---

# ADR-012: Textos legales, consentimientos versionados, menores y registro reforzado

## Contexto

La plataforma no tenía términos, política de privacidad ni condiciones de contratación. Son obligatorios para operar en Perú (Ley 29733 de Protección de Datos Personales, Código de Protección y Defensa del Consumidor) y para pasar a producción el acceso con Google y Meta ([credenciales-oauth](../../06-operacion/credenciales-oauth.md)).

## Decisión

Usuario, 2026-11-16:

| Tema | Decisión |
|---|---|
| Titular | Aural Perú EIRL, RUC 20615656128, domicilio fiscal Av. Javier Prado Este 5920, La Molina, Lima. Contacto: correo del estudio ([ADR-011](ADR-011-correo-gmail-del-estudio.md)), WhatsApp 925530800, Facebook `/bugalu.studio`, Instagram y TikTok `@bugalu.studio`, o un profesional autorizado del estudio |
| Textos | Leader redacta borradores de términos de uso, política de privacidad y condiciones de contratación (reservas, pagos, cancelación y reprogramación, menores, propiedad intelectual). **Un abogado los revisa antes de publicarlos** |
| Aceptación | Cada texto tiene versión y fecha. Se registra quién aceptó qué versión y cuándo, al registrarse y al reservar (la casilla antes pendiente). Cada paso muestra un resumen claro de lo que implica, con enlace al texto completo |
| Propiedad intelectual | Los derechos de las grabaciones son del estudio, salvo los másteres y los demás entregables pactados por contrato, que son del artista. El estudio puede usar el material o fragmentos para promoción; los textos detallan los casos y límites |
| Capturas de pago | Se conservan indefinidamente, con medidas de seguridad y optimización |
| Promociones | Se enviarán promociones generales y específicas, solo con consentimiento aparte y revocable |
| Menores de edad | Se atienden con consentimiento previo de padres o tutor (documento legal) y un adulto responsable presente en el recinto durante la sesión |
| Libro de Reclamaciones | Virtual y estandarizado en la plataforma (RF nuevo); el físico llegará después |
| Registro de artistas | Más fiable sin ser restrictivo: documento de identidad, contacto, redes, domicilio y conocimiento de las políticas; modalidad individual o agrupación |

## Consecuencias

- Borradores en `docs/08-legal/`, con versión, para revisión legal; la versión vigente se publica en la plataforma.
- RF nuevos: [RF-16](../../03-requerimientos/RF-16.md) (Libro de Reclamaciones) y [RF-17](../../03-requerimientos/RF-17.md) (registro reforzado y aceptación de textos); RF-01 y RF-04 incorporan la aceptación.
- Datos de identidad y de menores amplían el tratamiento de datos personales: la política de privacidad y el banco de datos deben reflejarlo.
