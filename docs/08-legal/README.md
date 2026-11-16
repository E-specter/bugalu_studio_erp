# 08 · Textos legales (borradores)

> **Borradores para revisión de un abogado colegiado en el Perú. No son asesoría legal ni están vigentes.** Los redactó el equipo del proyecto según [ADR-012](../00-proyecto/decisiones/ADR-012-textos-legales-y-consentimientos.md); ninguno se publica en la plataforma hasta que el abogado los revise y el estudio los apruebe.

## Índice

| Archivo | Contenido | Se acepta en |
|---|---|---|
| [terminos-de-uso](terminos-de-uso.md) | Titular y contacto, cuentas y roles, uso aceptable, propiedad intelectual de la plataforma, responsabilidad, cambios, ley aplicable y Libro de Reclamaciones | Registro |
| [politica-de-privacidad](politica-de-privacidad.md) | Datos que se tratan, finalidades, promociones, destinatarios y transferencias, conservación, seguridad, derechos, menores y almacenamiento local | Se lee en el registro (no se "acepta") |
| [condiciones-de-contratacion](condiciones-de-contratacion.md) | Servicios, reservas, precios con IGV, pagos, caducidad, cancelación por niveles, cancelación por el estudio, asesorías, entregables y menores | Cada reserva y asesoría |
| [condiciones-propiedad-intelectual](condiciones-propiedad-intelectual.md) | Parte de las condiciones: titularidad de las grabaciones, usos promocionales y sus límites, retiro a pedido | Con las condiciones |
| [resumenes-para-pantallas](resumenes-para-pantallas.md) | Texto corto y casilla de cada paso: registro, menores, reserva, asesoría, pago, promociones y cancelación | — |

Marcas en los textos: **[verificar]**, dato o norma que el abogado debe confirmar; **[cifra por confirmar]**, valor que el estudio aún no decide.

## Versionado

Cada texto lleva en su frontmatter `version` (versión semántica) y `vigente_desde` (fecha), y los repite al inicio del cuerpo.

| Cambio | Ejemplo | Versión | Qué pasa con los usuarios |
|---|---|---|---|
| Cambia derechos u obligaciones | Nuevos plazos o retenciones, nueva finalidad o nuevo destinatario de datos | Mayor (2.0.0) | Aviso por correo y en la plataforma con [cifra por confirmar] días de anticipación; nueva aceptación en el siguiente ingreso o contrato |
| Añade o aclara sin quitar derechos | Un canal de contacto nuevo, un ejemplo más | Menor (1.1.0) | Aviso por correo; no se vuelve a aceptar |
| Corrección de forma | Erratas, formato | Parche (1.0.1) | Sin aviso |

- Los borradores van en 0.x.y. La primera versión publicada, ya revisada por el abogado, es la **1.0.0** y pasa a `estado: aprobado`.
- **Cada versión publicada es inmutable:** la plataforma guarda y sirve el texto exacto de cada versión, para que el usuario vea lo que aceptó y el estudio pueda probarlo (art. 47 e y f del Código de Protección y Defensa del Consumidor; art. 9 del reglamento de la Ley 29733).
- **Registro de aceptación** ([RF-17](../03-requerimientos/RF-17.md)): usuario, texto, versión, fecha y hora con zona horaria, paso (registro, reserva, asesoría, pago, menor, promociones) y la operación asociada (folio de la reserva o asesoría). En un menor, también quién aceptó por él. Los consentimientos opcionales guardan además su retiro con fecha.
- Un servicio ya contratado se rige por la versión de las condiciones que se aceptó al contratarlo.

## Puntos que el abogado debe revisar

1. **Titular y marca:** que Aural Perú E.I.R.L. figure como titular y si la marca Bugalú Studio está registrada ante el Indecopi.
2. **Capturas de pago conservadas indefinidamente** (decisión del estudio): choca con el principio de calidad, que exige conservar los datos solo el tiempo necesario (art. 8 de la Ley 29733). Proponer un plazo (por ejemplo, el tributario) o fundamentar la decisión.
3. **Datos obligatorios del registro:** si el domicilio y las redes son indispensables; condicionar el servicio a datos no indispensables afecta la libertad del consentimiento (art. 3.2 del DS 016-2024-JUS).
4. **Promociones:** si una casilla en el registro cumple el art. 58.1 e del Código del Consumidor (modificado por la Ley 32323, 2025), que solo permite mensajes masivos cuando el consumidor contacta al proveedor por iniciativa propia y consiente; el uso de WhatsApp; y si las promociones "específicas" son perfilamiento que debe informarse (art. 6.1.8 del reglamento).
5. **Flujo transfronterizo** a Google y Meta (EE. UU.): base legal (art. 15, incisos 4 y 7, de la Ley 29733), garantías y comunicación al Registro (arts. 18 a 21 del reglamento).
6. **Banco de datos:** inscripción en el Registro Nacional (art. 42), si hacen falta bancos separados (clientes, reclamaciones, personal), si se requiere Oficial de Datos Personales (art. 37) y el documento de seguridad (art. 47).
7. **Alojamiento propio** ([ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md)): medidas mínimas de seguridad (arts. 46 a 48 del reglamento) y el procedimiento de notificación de incidentes en 48 horas (art. 34).
8. **Menores:** quién contrata (capacidad, Código Civil), consentimiento para datos desde los 14 años frente al contrato que firma el adulto (arts. 22 y 25 del reglamento), verificación de identidad del adulto (art. 25.4), qué datos del adulto se pueden pedir (art. 23.2), consecuencia de que el adulto no esté presente y la asesoría virtual.
9. **Política de cancelación por niveles:** proporcionalidad de las retenciones (arts. 49 y 51 a del Código del Consumidor; reducción de penalidades en el Código Civil [verificar]); si el crédito puede reemplazar la devolución, su vigencia y qué pasa al vencer; la inasistencia sin devolución; y la regla de la v1 de que el cliente con pagos pide la cancelación al estudio, frente al derecho a desvincularse por el mismo medio con que contrató (art. 47 c).
10. **Cancelación por el estudio y suspensión de cuentas:** compatibilidad con las cláusulas de ineficacia absoluta (art. 50 a, b y c) y plazo de devolución.
11. **Cláusula de jurisdicción** (jueces de Lima) frente a consumidores (art. 50 f).
12. **Propiedad intelectual:** si el estudio es "productor de fonogramas" cuando el artista encarga y paga la grabación (art. 2, num. 33, del D. Leg. 822); si la aceptación por clic cumple la cesión "expresa y escrita" por cada forma de uso (art. 89); derechos del artista intérprete (arts. 131 y 132; Ley 28131); autorización expresa de imagen y voz para los usos promocionales (art. 15 del Código Civil), y si debe ser una casilla aparte; qué entregables recibe por defecto quien solo graba.
13. **Libro de Reclamaciones:** campos, constancia y conservación según el reglamento vigente (DS 011-2011-PCM y sus modificaciones, como el DS 101-2022-PCM) y si ya se aprobó el proyecto de modificación para plataformas digitales (RM 244-2026-PCM, julio de 2026).
14. **Comprobantes de pago:** momento y medio de emisión de boletas y facturas fuera de la plataforma (SUNAT) y plazos de conservación tributaria.
15. **Retención de archivos por saldo impago** y tiempo no usado por llegada tarde: si son exigibles.
16. **Diseño de las pantallas:** casillas sin marcar y rechazo tan fácil como aceptar (art. 56.1 h del Código, incorporado por el D. Leg. 1729, 2026).

## Fuentes consultadas

- Código de Protección y Defensa del Consumidor, Ley 29571, texto actualizado al 12/02/2026 (Editora Perú): https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=17
- Ley 29733 y su reglamento, DS 016-2024-JUS, texto actualizado (Editora Perú): https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=23
- Principales cambios del reglamento de datos personales (El Peruano): https://www.elperuano.pe/noticia/259141--peru-fortalece-la-proteccion-de-datos-estos-son-los-principales-cambios-del-nuevo-reglamento
- DS 016-2024-JUS en la ANPD (gob.pe): https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus
- DS 101-2022-PCM, plazo de 15 días hábiles para reclamos y quejas (Andina): https://andina.pe/agencia/noticia.aspx?id=905857
- Proyecto de modificación del Reglamento del Libro de Reclamaciones, RM 244-2026-PCM (El Peruano): https://elperuano.pe/noticia/300583-pcm-publica-proyecto-para-modificar-el-reglamento-del-libro-de-reclamaciones
- D. Leg. 822, Ley sobre el Derecho de Autor (ficha OMPI): https://www.wipo.int/wipolex/es/legislation/details/18762 · texto con notas del Indecopi (reproducción no oficial): https://alejandrius.com/decreto-legislativo-no-822/
- Código Civil, art. 15, derecho a la imagen y la voz (comentario, fuente secundaria): https://lpderecho.pe/articulo-15-del-codigo-civil-derecho-a-la-imagen-y-voz/
