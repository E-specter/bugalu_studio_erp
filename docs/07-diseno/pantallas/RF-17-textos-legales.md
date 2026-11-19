---
id: pantalla-rf-17-textos-legales
titulo: Pantalla — Textos legales públicos, publicación de versiones y documentos repetidos
estado: aprobado
depende_de: [RF-17, RF-16, RF-20, ADR-012, diseno-brief, patron-estructura-app, patron-formularios, patron-tablas-y-tableros, patron-estados-sistema, comp-pie-publico, comp-tabla, comp-panel, comp-campo, comp-casilla, comp-barra-acciones, comp-aviso, comp-boton, comp-etiqueta-tecnica]
---

# Textos legales

| Campo | Valor |
|---|---|
| Requerimiento | [RF-17](../../03-requerimientos/RF-17.md): CA-01, CA-02, CA-03 (vista del Administrador), CA-14 y decisión 4 (documento repetido); ampliación del 2026-11-19 (ver, prellenar, cargar `.md` y vista previa) en [editor de textos](RF-17-textos-editor.md); [RF-20](../../03-requerimientos/RF-20.md) CA-12 (pie de las condiciones) |
| Actores | Cualquiera (páginas públicas); Administrador (publicar, retirar, revisar documentos) |
| Estructura | Landing para las páginas públicas; App, panel interno, para el Administrador |
| Ruta | `/legal/` · `/legal/{terminos-de-uso\|privacidad\|condiciones-de-contratacion\|declaracion-de-agrupacion}/?version=` · `/app/textos` · `/app/textos/ver?tipo=&version=` · `/app/textos/publicar?tipo=` · `/app/usuarios?documento=repetido`. URL: `version`, `tipo`, `documento`, `aviso` |
| Isla | `<bugalu-texto-legal tipo="…">` y `<bugalu-textos-legales vista="lista\|publicar\|ver">` (nuevas); `<bugalu-solicitudes>` (amplía la vista usuarios) |

## Páginas públicas

1. Se llega desde el [pie público](../componentes/pie-publico.md) (también en App, variante Acceso), el enlace de un [resumen legal](../componentes/resumen-legal.md) (con `?version=`) o el historial del [perfil](RF-17-perfil.md).
2. Sin `version`, se muestra la vigente (`GET /textos-legales`: la del `tipo` que no está `programada`); con `version`, esa (`GET /textos-legales/{tipo}/versiones/{version}`).

| Región | Componente | Contenido |
|---|---|---|
| Cabecera | La de `LayoutPublico` | Logotipo enlazado a inicio |
| Principal | `<h1>` (`fuente-familia-titulo`, `fuente-tamano-titulo-lg`) + línea técnica "VERSIÓN 1.0.0 · VIGENTE DESDE 1 DIC 2026" | Título del texto |
| Principal | [aviso](../componentes/aviso.md) Información (si aplica) | Versión antigua: "Estás leyendo la versión 0.9.0, que ya no está vigente." + "Leer la versión vigente (1.0.0)". Hay programada: "Desde el 15 dic 2026 rige la versión 1.1.0." + "Leer la versión 1.1.0" |
| Principal | [panel](../componentes/panel.md) Destacado `EN POCAS PALABRAS` | `resumen` tal cual |
| Principal | Prosa | `contenido` en `fuente-tamano-lectura`, `fuente-interlineado-lectura`, ancho `medida-linea-lectura`; encabezados del texto desde `<h2>` |
| Principal, solo en `condiciones-de-contratacion` | [panel](../componentes/panel.md) Base `VALORES VIGENTES` tras la prosa | `GET /parametros/danos` (RF-20 CA-12), pedido junto con el texto: "Tarifa por hora de gestión: S/ 25,00 · Tope por sesiones perdidas: 8 horas de sala". Tarifa `0.00` → "Tarifa por hora de gestión: por fijar"; tope 1 → "1 hora de sala". Vale para cualquier `?version=`: son los vigentes, como dice el título |
| Pie | [pie público](../componentes/pie-publico.md) Completa | — |

`/legal/`: `<h1>` TEXTOS LEGALES, "Las reglas con las que trabajamos. Cada texto indica su versión y desde cuándo rige." y [tabla](../componentes/tabla.md) Directorio TEXTO (enlace) · VERSIÓN · VIGENTE DESDE · PRÓXIMA VERSIÓN ("1.1.0 desde el 15 dic 2026" o "—").

Estados: carga "Cargando…" con `aria-busy` · 404 "No existe la versión {v} de este texto." + "Leer la versión vigente" · sin versión publicada "Este texto aún no está publicado." · 503, red: aviso Error "No pudimos cargar el texto. Inténtalo de nuevo en unos minutos." + "Reintentar" · sin JS: ver Pendientes. `VALORES VIGENTES` no tiene carga ni error propios: se pinta solo si el texto cargó y su petición respondió 200; si falla (503, red, no JSON), el texto queda legible sin el pie y sin aviso.

## Administrador: textos

| Vista | Región | Componente (variante) | Contenido |
|---|---|---|---|
| Lista | Principal | panel `TEXTOS` + tabla Directorio | TEXTO · VIGENTE ("versión 1.0.0 · desde 1 dic 2026" + "Ver", [editor](RF-17-textos-editor.md#ver); sin versión: [etiqueta](../componentes/etiqueta-tecnica.md) Aviso SIN PUBLICAR) · PROGRAMADA (versión y fecha + "Ver", o "—") · "Publicar versión de {texto}" ([botón](../componentes/boton.md) Secundario como enlace) y, si hay programada, "Retirar versión {v}" (Peligro) |
| Lista, retirar | Principal | panel `RETIRAR VERSIÓN {v} DE {TEXTO}` en lugar de la tabla | "Se borra el contenido y no se puede recuperar. La versión vigente sigue rigiendo." + [barra](../componentes/barra-acciones.md) Decisión: "Volver" + Peligro "Retirar versión" |
| Publicar | Principal (un `<form>`) | panel `P1 VERSIÓN` → panel `P2 CONTENIDO` | P1: `<dl>` TEXTO y ÚLTIMA VERSIÓN; TIPO DE CAMBIO ([casillas](../componentes/casilla.md) Radio con detalle); VERSIÓN ([campo](../componentes/campo.md) Texto, prellenada con la siguiente según el tipo); VIGENTE DESDE (`date`, `min` = hoy + 15 días; con Parche se sustituye por "Rige al publicarla."). P2: CONTENIDO (Área, obligatorio; prellenado, con "Cargar archivo .md" y VISTA PREVIA, [editor](RF-17-textos-editor.md#publicar-contenido-y-vista-previa)) → grupo `<fieldset>` RESUMEN POR PASO (un Área por contexto del texto; el primero obligatorio) → RESUMEN DE CAMBIOS (Área, opcional) → Primario "Revisar y publicar". TIPO DE CAMBIO lleva "(obligatorio)" en su `<legend>` |
| Publicar, revisión | Principal | panel `R1 REVISA ANTES DE PUBLICAR` | `<dl>` de P1, consecuencias (Copy), resumen como texto y contenido con formato final ([editor](RF-17-textos-editor.md#revisión-r1); contenedor con desplazamiento, `tabindex="0"`) + barra Formulario: "Volver a editar" + Primario "Publicar versión" |

**Decisión del brief:** publicar es irreversible (la versión queda inmutable), así que tiene revisión propia ([formularios](../patrones/formularios.md#prevención-de-errores)), sin palabra escrita: esa barrera es solo para los [cambios sensibles](RF-20-cambios-sensibles.md). La revisión es un estado de la vista, como allí; "Volver a editar" conserva todo.

| Situación | Forma y texto |
|---|---|
| Validación | "Elige el tipo de cambio." · "Escribe la versión como 1.2.0." · "Elige desde cuándo rige." · "Escribe el resumen." · "Escribe el contenido." |
| 422 `version_invalida` | Bajo VERSIÓN: "Para un cambio {mayor} la versión debe ser {2.0.0}, mayor que la última ({1.0.0})." |
| 422 `aviso_insuficiente` | Bajo VIGENTE DESDE: "Elige una fecha desde el {D MMM AAAA}: los clientes necesitan 15 días de aviso." |
| 409 `version_programada` | Aviso Error "Ya hay una versión programada de este texto ({v}, desde {fecha}). Retírala antes de publicar otra." + "Volver a textos" |
| 409 `conflicto` | Aviso Error "Alguien publicó una versión de este texto hace un momento. Revisa la lista antes de seguir." |
| 409 `version_vigente` al retirar | Aviso Error "Esa versión ya está vigente y no se puede retirar." y la lista recargada |
| Éxito | `/app/textos?aviso=version-publicada` "Versión publicada." · `version-retirada` "Versión retirada." |
| Carga, 401, 403, 503, red, sin JS | Como [tarifas](RF-02-tarifas.md#estados); al enviar, sin "Reintentar" y con lo escrito conservado |

## Administrador: documentos repetidos

En [usuarios](RF-01-solicitudes.md#composición): las etiquetas Filtro suman "Documento repetido" (`?documento=repetido`); la tabla suma DOCUMENTO ("DNI 12345678" y, si se repite, etiqueta Aviso REPETIDO), ordenada por documento para que las cuentas que lo comparten queden juntas. En la persona, U1 suma modalidad, documento, domicilio, redes e integrantes, y un panel `U3 TEXTOS ACEPTADOS` (`GET /usuarios/{id}/aceptaciones`, misma tabla que el [perfil](RF-17-perfil.md#composición)). Sin resultados: "No hay documentos repetidos." Solo informa: el Administrador contacta a las personas por fuera.

## Copy

| Elemento | Texto |
|---|---|
| Ruta e índice | Inicio / Textos · `[A10] CONTROL / TEXTOS` |
| Título y descripción | TEXTOS LEGALES · "Publica nuevas versiones de los términos, la privacidad y las condiciones. Las publicadas no se editan." |
| Publicar | PUBLICAR VERSIÓN · "{Texto}: elige el tipo de cambio y desde cuándo rige." |
| Tipo de cambio (detalle) | Mayor: "Cambia derechos u obligaciones. Avisa por correo; los términos se vuelven a aceptar." · Menor: "Aclara o añade sin cambiar lo esencial. Avisa por correo." · Parche: "Erratas y formato. Rige al publicarla, sin aviso." |
| Consecuencias | Mayor o menor: "Al publicarla no podrás editarla. Avisaremos por correo a todos los clientes y regirá desde el {fecha} para las operaciones nuevas." (+ en términos y mayor: "Cada cliente tendrá que aceptarlos de nuevo para reservar.") · Parche: "Al publicarla no podrás editarla ni retirarla, y rige desde ahora." |
| Ayudas | RESUMEN: "Lo que verá la persona antes de aceptar. Frases cortas, en segunda persona." · CONTENIDO: "Texto completo en Markdown: # para títulos y - para listas." |

## Accesibilidad

- Páginas públicas: `<main>` con un `<h1>`; el contenido empieza en `<h2>`; la línea de versión es texto. El aviso de versión va antes del resumen.
- Administrador: foco al `<h2>` de R1 al revisar y al botón "Publicar versión de {texto}" al volver; acciones de fila con el texto en el nombre accesible.
- Región `role="status"` de cada isla para carga y resultado; al fallar un envío, el foco va al aviso.

## Pendientes

- Resuelto: la API devuelve `contenido_html` saneado ([precisiones de RF-17](../../03-requerimientos/RF-17.md#precisiones-de-contrato-leader-tras-las-specs-de-pantalla)).
- **leader:** un texto legal no debería depender de JavaScript para leerse; con salida estática y textos en la base, el `<noscript>` solo puede dar el contacto. Alternativa: generar las páginas al publicar.
- **leader / dev-backend:** documento repetido: proponemos `documento_repetido` en el `Perfil` que ve el Administrador y el filtro `GET /usuarios?documento_repetido=true`.
- Resuelto: `/libro-de-reclamaciones/` ya tiene pantalla ([formulario de RF-16](RF-16-formulario.md)).
- **leader:** el texto `autorizacion_menor` entra en la lista y en `/legal/` con la etapa B.
