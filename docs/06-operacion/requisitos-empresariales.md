---
id: operacion-requisitos-empresariales
titulo: Requisitos legales y administrativos de la empresa
estado: borrador
depende_de: [ADR-012, ADR-013, ADR-014, ADR-015, RF-16, RF-17]
---

# Requisitos legales y administrativos de la empresa

Lista para el área de operaciones ([ADR-015](../00-proyecto/decisiones/ADR-015-cancelacion-conservacion-y-correcciones.md)): lo que una EIRL peruana que presta servicios de estudio de grabación y vende por una plataforma web debe tener o cumplir. Investigación del 2026-11-16 en fuentes oficiales y, cuando no las hubo, en fuentes secundarias. **No es asesoría legal ni contable:** el abogado de los [textos legales](../08-legal/README.md) y el contador del estudio confirman cada fila. **[verificar]** marca lo que no se pudo confirmar en una fuente oficial.

Estado del estudio: **Hecho** · **Pendiente** · **Por confirmar** (el estudio no lo ha informado). Se sabe que la empresa ya está constituida y con RUC, que la marca **no** está registrada en el Indecopi y que el banco de datos **no** está inscrito ante la Autoridad Nacional de Protección de Datos Personales (ANPD).

## 1. Tributario (SUNAT)

| Requisito | Para qué | Obligatorio | Costo o referencia | Estado |
|---|---|---|---|---|
| RUC activo y habido, con domicilio fiscal y actividad económica correctos | Operar y emitir comprobantes. La actividad debe cubrir servicios de grabación y asesoría [verificar código CIIU] | Sí | Gratuito | Hecho (revisar actividad y datos) |
| Régimen tributario: General, MYPE Tributario (RMT) o Especial (RER) | Impuesto a la renta e IGV. El Nuevo RUS no sirve: no permite emitir facturas, que [ADR-013](../00-proyecto/decisiones/ADR-013-impuestos-y-parametros-sensibles.md) exige | Sí | Lo elige el contador; el RMT suele convenir a una empresa pequeña [verificar] | Por confirmar |
| Emisor electrónico de boletas y facturas | Entregar comprobante por cada pago (fuera de la plataforma, [ADR-010](../00-proyecto/decisiones/ADR-010-pagos-estados-y-cancelacion.md)) | Sí: según la RS 000075-2026/SUNAT, desde la inscripción en el RUC para las empresas del RMT, RER y General [verificar texto oficial] | Gratuito con el Sistema de Emisión Electrónica de SUNAT (Clave SOL); un proveedor (PSE u OSE) tiene costo mensual | Por confirmar |
| Declaraciones mensuales (IGV y renta) y anual; registros de ventas y compras electrónicos (SIRE) | Cumplir las obligaciones periódicas | Sí | Cronograma por último dígito del RUC; honorarios del contador | Por confirmar |
| Bancarización: pagos desde S/ 2 000 o US$ 500 por medios de pago (Ley 28194) | Que el gasto o el costo sea deducible y el crédito fiscal válido | Sí | [verificar umbral vigente] | Por confirmar |
| Detracciones en servicios facturados a empresas | Algunos servicios empresariales tienen detracción y piden cuenta en el Banco de la Nación | Solo si aplica [verificar si los servicios del estudio están en el anexo 3] | Cuenta de detracciones gratuita | Por confirmar |
| Conservar comprobantes, libros y sustentos | Fiscalización mientras el tributo no prescriba (4 años por regla general, Código Tributario art. 43) [verificar] | Sí | — | Las capturas de pago se conservan 5 años (ADR-015) |

## 2. Municipal (La Molina) y Defensa Civil

| Requisito | Para qué | Obligatorio | Costo o referencia | Estado |
|---|---|---|---|---|
| Licencia de funcionamiento | Abrir el local al público (Ley 28976 y su TUO, DS 163-2020-PCM; en La Molina, Ordenanza 475/MDLM, 2025). Incluye verificar que la zonificación admite el giro | Sí | Tasa del TUPA de La Molina [verificar]. Como referencia, una guía nacional de gob.pe indica S/ 246.70 (riesgo bajo) y S/ 271.70 (riesgo medio) | Por confirmar |
| Certificado ITSE (Defensa Civil) | Seguridad del local: aforo, extintores, señalización, instalaciones eléctricas. En riesgo bajo o medio la inspección es posterior a la licencia; en alto o muy alto, previa. Vigencia de 2 años | Sí | Tasa del TUPA [verificar]; renovar cada 2 años y con cada cambio de giro o área | Por confirmar |
| Autorización de anuncio (letrero) | Colocar un letrero con la marca en la fachada | Solo si hay letrero | TUPA de La Molina [verificar] | Por confirmar |
| Ruido | No superar los estándares de ruido (DS 085-2003-PCM) ni la ordenanza distrital: el aislamiento de la sala lo resuelve | Sí | [verificar ordenanza de ruido de La Molina] | Por confirmar |

## 3. Datos personales (ANPD, Ley 29733 y DS 016-2024-JUS)

| Requisito | Para qué | Obligatorio | Costo o referencia | Estado |
|---|---|---|---|---|
| Inscribir los bancos de datos en el Registro Nacional (art. 42 del reglamento) | Tratar datos de clientes, menores, reclamos y personal. Probables bancos: usuarios y clientes, Libro de Reclamaciones, personal y, si hay cámaras, videovigilancia [verificar con el abogado] | Sí | **Gratuito**, en línea en el SIPDP (sipdp.minjus.gob.pe), de aprobación automática; da constancia y código | **Pendiente** |
| Documento de seguridad y medidas de seguridad | Describe accesos, privilegios, copias, auditorías y verificaciones; debe estar aprobado y con fecha cierta | Sí | Lo redacta el estudio con el abogado; insumos en [produccion-mantenimiento](produccion-mantenimiento.md) | Pendiente |
| Comunicar el flujo transfronterizo a Google y Meta (EE. UU.) | Correo, calendario, Meet y acceso con Google o Facebook | Sí, si el abogado lo confirma [verificar arts. 18 a 21] | Gratuito, con la inscripción | Pendiente |
| Oficial de Datos Personales | Supervisa el cumplimiento | Según la Directiva de la RD 100-2025-JUS-DGTAIPD; para una empresa pequeña sin grandes volúmenes probablemente no [verificar] | — | Por confirmar |
| Atender derechos (acceso, rectificación, supresión, oposición) y notificar incidentes en 48 horas (art. 34) | Plazos de la [política de privacidad](../08-legal/politica-de-privacidad.md) | Sí | Procedimiento interno | Pendiente |
| Videovigilancia | Si hay cámaras: cartel informativo y banco propio | Solo si hay cámaras [verificar directiva vigente] | — | Por confirmar |

## 4. Consumidor (Indecopi, Ley 29571)

| Requisito | Para qué | Obligatorio | Costo o referencia | Estado |
|---|---|---|---|---|
| Libro de Reclamaciones virtual, con enlace siempre visible | Reclamos y quejas con respuesta en 15 días hábiles. La Ley 32495 (2025) lo exige a toda plataforma de comercio electrónico; un proveedor con local y canal virtual debe tener el virtual | Sí | En la plataforma ([RF-16](../03-requerimientos/RF-16.md)); el Indecopi ofrece gratis "Tu Libro de Reclamaciones". Reglamento: DS 011-2011-PCM; proyecto de cambio en la RM 244-2026-PCM [verificar si ya se aprobó] | Pendiente (RF-16) |
| Aviso del Libro en el local (Anexo II: A4 como mínimo, "Libro de Reclamaciones" en letras de 1 cm, con "(virtual)") y guía al consumidor en el local | Que quien está en el estudio pueda reclamar | Sí | Impresión del aviso | Pendiente |
| Libro de Reclamaciones de Respaldo físico (art. 4-A del reglamento) | Usarlo cuando la plataforma no funcione; lo anotado se transcribe a la app en 1 día calendario ([RF-16](../03-requerimientos/RF-16.md) CA-09) | Sí, con libro virtual y local abierto al público | Un cuaderno con hojas numeradas del formato del Anexo I | Pendiente |
| Precio total con IGV y condiciones antes de contratar | Información al consumidor | Sí | [ADR-013](../00-proyecto/decisiones/ADR-013-impuestos-y-parametros-sensibles.md) | En diseño |
| Sin patrones engañosos y con canales de atención accesibles y permanentes (D. Leg. 1729, 2026: arts. 24 y 56) | Casillas sin marcar, cancelar tan fácil como contratar, sin presión | Sí; su reglamento estaba pendiente [verificar] | Reglas en [resumenes-para-pantallas](../08-legal/resumenes-para-pantallas.md) | En diseño |
| Promociones solo con consentimiento (art. 58.1 e, Ley 32323) | Correos y WhatsApp promocionales | Sí, si se envían | Casilla aparte y baja inmediata | En diseño |
| Términos de uso, política de privacidad y condiciones revisados por un abogado | Contratar por la web y probar lo aceptado ([RF-17](../03-requerimientos/RF-17.md)) | Sí | Honorarios del abogado | Borradores 0.2.0 y 0.3.0 |
| Cartel por sala con las reglas de uso y su aforo (el del cálculo de aforo del ITSE, el mismo que registra el sistema), formato de acta de daños e inventario de equipos con fotos, fecha y precio de compra | Que el cliente conozca las reglas y el aforo en el local, y que el estudio pueda probar el estado previo y calcular la reposición con depreciación ([uso del estudio y daños](../08-legal/condiciones-uso-y-danos.md)) | Recomendado | Impresión; hoja de inventario | Pendiente |

## 5. Propiedad intelectual

| Requisito | Para qué | Obligatorio | Costo o referencia | Estado |
|---|---|---|---|---|
| Registro de la marca en el Indecopi | Uso exclusivo del nombre y del logo por 10 años renovables; impedir que otro la registre. Clase 41 (servicios de estudio de grabación, asesoría artística) y quizá otras [verificar clases] | No, pero muy recomendado | S/ 534.99 la primera clase y S/ 533.30 cada adicional; 25 % menos con REMYPE; búsqueda previa gratuita; unos 45 días hábiles sin oposición | **Pendiente: no registrada** |
| Contratos tipo con artistas | Cesión expresa y escrita por cada forma de uso de másteres y entregables (art. 89 del D. Leg. 822), autorización de imagen y voz (art. 15 del Código Civil) | Sí en la práctica | Base: [condiciones de propiedad intelectual](../08-legal/condiciones-propiedad-intelectual.md); el abogado define si basta el clic | Borrador |
| Contratos con músicos de sesión, productores y especialistas | Que el estudio pueda entregar o ceder su trabajo al artista (derechos del intérprete, Ley 28131) | Sí en la práctica | Contrato del abogado | Pendiente |
| Licencias de APDAYC (autores) y UNIMPRO (productores e intérpretes, con SONIEM en el ámbito de intérpretes) | Comunicar música grabada al público: música ambiental en recepción, eventos o live sessions con público | Solo si se pone música al público [verificar] | Tarifario de APDAYC según tipo de local, aforo y horas; UNIMPRO aparte | Por confirmar |
| Grabar obras ajenas (covers) | La licencia del autor la consigue el artista; el estudio puede negarse a grabar | Del artista | Ya está en las condiciones | Hecho en los borradores |
| Escuchas en la sala y afiliación del estudio a UNIMPRO como productor | Si las escuchas privadas son comunicación pública; si el estudio cobra regalías como productor de fonogramas | No [verificar] | Depende de la titularidad que fije el abogado | Por confirmar |
| Dominio propio | Correo con buena entrega, acceso con Google y Meta ([ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md)) | No, pero necesario para producción | Pago anual al registrador [verificar] | Pendiente |

## 6. Personal

| Requisito | Para qué | Obligatorio | Costo o referencia | Estado |
|---|---|---|---|---|
| Inscripción en el REMYPE | Régimen laboral especial de microempresa y descuento en el registro de marca | No | Gratuita con Clave SOL; ventas de microempresa hasta 150 UIT (UIT 2026: S/ 5 500) [verificar] | Por confirmar |
| Trabajadores en planilla | Contrato escrito con el régimen laboral; alta en el T-Registro el mismo día de ingreso; PLAME mensual; EsSalud 9 % a cargo del empleador; AFP u ONP; boletas de pago; remuneración mínima [verificar monto vigente] | Sí, si hay trabajadores | Costo laboral según régimen | Por confirmar |
| Seguro Vida Ley | Desde el primer día de trabajo (D. Leg. 688, modificado por el DU 044-2019) | Sí, con planilla | Prima de una aseguradora | Por confirmar |
| Seguridad y salud en el trabajo (Ley 29783) | Identificar riesgos (ruido, electricidad), registros y capacitación | Sí, con planilla [verificar régimen simplificado para microempresa] | — | Por confirmar |
| Locación de servicios (especialistas independientes) | Contrato civil sin subordinación; recibo por honorarios electrónico; retención de cuarta categoría según montos de la SUNAT [verificar] | Sí, si los hay | Riesgo: si hay horario y subordinación, Sunafil lo trata como relación laboral | Por confirmar |

## 7. Seguros recomendados (opcionales)

- **Multirriesgo o todo riesgo de equipos:** incendio, robo, daño eléctrico de equipos de audio y del servidor ([ADR-014](../00-proyecto/decisiones/ADR-014-alojamiento-inicial-local.md)).
- **Responsabilidad civil frente a terceros:** clientes, menores y acompañantes en el local.
- **Ciberriesgos:** incidentes con datos personales en el servidor propio.
- El SCTR solo es obligatorio en actividades de riesgo; un estudio de grabación no figura entre ellas [verificar].

## 8. Plataforma web

- **Cookies:** hoy solo almacenamiento local necesario, sin analítica ni publicidad: basta informarlo en la [política de privacidad](../08-legal/politica-de-privacidad.md#cookies-y-almacenamiento-local). Si se añade analítica, pedir consentimiento previo; la ANPD no tiene una guía de cookies vigente confirmada [verificar].
- **Accesibilidad:** no se encontró una obligación general de WCAG para empresas privadas [verificar]; el D. Leg. 1729 exige canales de atención accesibles. El [brief](../07-diseno/brief.md) ya fija WCAG 2.2 AA.
- **Patrones engañosos:** ver la sección 4.
- **Seguridad:** HTTPS, copias y registro de cambios sensibles ([produccion](produccion.md)).

## Prioridad

**Antes de abrir la plataforma al público:**

1. Licencia de funcionamiento e ITSE vigentes, si aún no están.
2. Régimen tributario y emisión electrónica confirmados con el contador.
3. Inscribir los bancos de datos en el SIPDP y aprobar el documento de seguridad.
4. Libro de Reclamaciones virtual ([RF-16](../03-requerimientos/RF-16.md)) y aviso en el local.
5. Textos legales revisados por el abogado y aceptación versionada ([RF-17](../03-requerimientos/RF-17.md)).
6. Contratos con el personal y los especialistas; T-Registro y Vida Ley si hay planilla.
7. Dominio y HTTPS ([produccion-exposicion](produccion-exposicion.md)).
8. Licencias de APDAYC y UNIMPRO, si se pone música al público.

**Después (lo antes posible, sin bloquear la apertura):**

1. Inscripción en el REMYPE y, con su descuento, el registro de la marca: cuanto antes, menor el riesgo de que otro la registre.
2. Seguros de equipos y de responsabilidad civil.
3. Evaluar el Oficial de Datos Personales, la afiliación a UNIMPRO y una auditoría de accesibilidad.
4. Libro de Reclamaciones físico.

## Fuentes

- Inscribir banco de datos (gob.pe): https://www.gob.pe/8060-inscribir-banco-de-datos-en-el-registro-nacional-de-proteccion-de-datos-personales · Inscripción gratuita (El Peruano): https://www.elperuano.pe/noticia/272457-tienes-datos-personales-de-clientes-o-usuarios-registralos-gratis-y-en-linea-en-el-rnpd-como-exige-la-ley
- Reglamento DS 016-2024-JUS (gob.pe): https://cdn.www.gob.pe/uploads/document/file/7886737/93001-nuevo-reglamento-de-la-ley-de-proteccion-de-datos-personales.pdf · Oficial de Datos Personales (El Peruano): https://elperuano.pe/noticia/288028-suplemento-legal-juridica-tratas-datos-sensibles-o-grandes-volumenes-evalua-si-debes-nombrar-un-odp
- Registro de marca, tasas (Indecopi en gob.pe): https://www.gob.pe/institucion/indecopi/noticias/665850-emprendedor-conoce-cuanto-cuesta-registrar-tu-marca-en-indecopi · https://www.gob.pe/institucion/indecopi/campa%C3%B1as/6164-protege-tu-sueno-registra-tu-marca
- Licencia de funcionamiento riesgo bajo o medio (gob.pe): https://www.gob.pe/20844-obtener-licencia-de-funcionamiento-para-negocios-de-riesgo-bajo-o-medio · Ordenanza de La Molina (El Peruano): https://busquedas.elperuano.pe/dispositivo/NL/2418358-1
- ITSE riesgo bajo o medio (gob.pe): https://www.gob.pe/20961-obtener-certificado-de-inspeccion-tecnica-de-seguridad-en-edificaciones-de-riesgo-bajo-o-medio
- Emisión electrónica desde el primer día (El Peruano): https://www.elperuano.pe/noticia/296489-sin-marcha-blanca-sunat-exige-facturacion-electronica-desde-el-primer-dia · Obligados (SUNAT): https://cpe.sunat.gob.pe/informacion_general/obligados_cpe
- Ley 32495, Libro de Reclamaciones en plataformas (El Peruano): https://elperuano.pe/noticia/282787-plataformas-de-comercio-electronico-deberan-contar-con-libro-de-reclamaciones · Herramienta gratuita (Indecopi): https://www.gob.pe/institucion/indecopi/noticias/1296574-los-emprendedores-ya-pueden-generar-su-libro-de-reclamaciones-de-manera-rapida-y-sencilla-sin-costo-alguno
- D. Leg. 1729 (El Peruano): https://www.elperuano.pe/noticia/289089-por-primera-vez-el-codigo-del-consumidor-introduce-cambios-para-un-comercio-electronico-sin-abusos-informate · https://busquedas.elperuano.pe/dispositivo/NL/2486266-3
- T-Registro (gob.pe): https://www.gob.pe/8214-t-registro · REMYPE y CTS (Sunafil): https://www.gob.pe/institucion/sunafil/noticias/1389500-pequenas-empresas-que-no-esten-inscritas-en-el-remype-tienen-que-pagar-cts-completa
- Vida Ley desde el primer día (Andina): https://andina.pe/agencia/noticia-trabajadores-tendran-seguro-vida-desde-primer-dia-laboral-779814.aspx · UIT 2026 (El Peruano): https://www.elperuano.pe/noticia/285847-uit-impacto-de-su-nuevo-valor-2026
- Tarifario APDAYC 2026: https://apdayc.org.pe/uploads/shares/tarifarios/PDF/Tarifario%202026/ANEXO_1.pdf · Sociedades de gestión colectiva (Andina): https://andina.pe/ingles/noticia-indecopi-exhorta-a-empresas-radio-television-y-cable-a-cumplir-pago-regalias-800364.aspx
