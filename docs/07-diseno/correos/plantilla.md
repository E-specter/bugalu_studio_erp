---
id: correo-plantilla
titulo: Correo — Plantilla de marca
estado: borrador
depende_de: [ADR-016, ADR-011, ADR-015, diseno-brief, diseno-tokens, fund-color, fund-tipografia, fund-logotipo, comp-pie-publico]
---

# Plantilla de correo de la marca

Envoltorio común de **todos** los correos de la plataforma ([ADR-016](../../00-proyecto/decisiones/ADR-016-correos-con-plantilla-y-calendario.md)). La plantilla no reescribe los avisos: el asunto y el cuerpo siguen saliendo de `redactar()` (`notificaciones/dominio/redaccion.py` y `redaccion_rf18.py`) y la plantilla los enmarca.

| Archivo | Contenido |
|---|---|
| Este | Estructura, valores, bloques, copy fijo, modo oscuro y accesibilidad |
| [HTML y texto plano de referencia](plantilla-html.md) | Esqueleto HTML con estilos en línea y la versión de texto plano, listos para rellenar |
| [Evento de calendario](evento-calendario.md) | `.ics`, enlaces "Añadir a…", aviso de ADR-016 y copy del evento |
| [Avisos](avisos.md) | Qué bloques usa cada tipo de aviso y cómo el cuerpo de texto pasa a HTML |
| [logo-correo.png](logo-correo.png) | Logo para el correo (abajo) |

## Mensaje

```
multipart/mixed
├─ multipart/alternative
│  ├─ text/plain; charset=utf-8              versión de texto plano
│  ├─ multipart/related
│  │  ├─ text/html; charset=utf-8            plantilla HTML
│  │  └─ image/png  Content-ID <logo-bugalu>, Content-Disposition: inline
│  └─ text/calendar; method=REQUEST|CANCEL   solo avisos con evento
└─ application/ics  bugalu-{folio}.ics, attachment   solo avisos con evento
```

Se arma con `email.message.EmailMessage` de la biblioteca estándar (`set_content`, `add_alternative`, `add_related`, `add_attachment`); sin dependencias nuevas ni plantillas externas. El remitente y el SMTP no cambian ([ADR-011](../../00-proyecto/decisiones/ADR-011-correo-gmail-del-estudio.md)).

## Estructura HTML

- **Una columna**, ancho máximo **600 px**, centrada; en pantallas estrechas ocupa el 100 % con 8 px de margen lateral. Para Outlook de escritorio, la tabla de 600 px va dentro de un comentario condicional `<!--[if mso]>`.
- **Maquetación con tablas** (`role="presentation"`, `cellpadding="0"`, `cellspacing="0"`, `border="0"`); nada de `flex`, `grid`, `position` ni `float`.
- **Estilos en línea** en cada elemento, con propiedades largas (`font-family`, `font-size`, `line-height`, `font-weight`): Outlook ignora la abreviada `font`. El `<style>` del `<head>` solo lleva la consulta de ancho y el modo oscuro, que son mejoras: sin ellos el correo se lee igual.
- **Sin** imágenes remotas, fuentes web, `var()`, JavaScript, formularios ni vídeo. HTML final < 100 KB (Gmail recorta por encima de 102 KB).
- Medidas en **px**: los clientes de correo no respetan `rem` de forma fiable. Es la única excepción a las [medidas relativas](../fundamentos/espaciado-reticula.md#unidades) del brief.

## Valores (tokens resueltos)

El correo no puede leer `tokens.css`: cada valor es el **literal** del token de rol. Si un token cambia en [tokens](../tokens.md), cambia aquí.

| Uso en el correo | Token de rol | Literal |
|---|---|---|
| Fondo exterior y del contenedor | `color-fondo-lienzo`, `color-fondo-superficie` | `#EBEBFF` |
| Banda de cabecera | `color-fondo-invertido` | `#262757` |
| Bordes y reglas | `color-borde-fuerte` | `#262757` |
| Título, claves y valores de datos, enlaces | `color-texto-principal` | `#262757` |
| Párrafos | `color-texto-cuerpo` | `#231F20` |
| Etiqueta técnica, metadatos, pie | `color-texto-secundario` | `#4A4B7D` |
| Botón y bloque de calendario | `color-fondo-destacado` | `#E1C9E3` |
| Texto sobre navy | `color-texto-invertido` | `#EBEBFF` |
| Borde del contenedor, botón y bloques | `borde-grosor-base` | `2px` |
| Reglas de la tabla de datos | `borde-grosor-fino` | `1px` |
| Relleno: móvil / desde 600 px | `espacio-4` / `espacio-6` | `16px` / `24px` |
| Separación entre bloques | `espacio-6` | `24px` |

Todos los pares están en [contraste verificado](../fundamentos/color.md#contraste-verificado) (texto ≥ 6,89:1). El naranja de marca **no se usa**: el correo no tiene hover ni aviso Crítico. Radio 0 en todo, sin sombras.

## Tipografía

Las fuentes de marca solo se ven si el destinatario las tiene instaladas: no se cargan fuentes web (degradan mal en Gmail y Outlook). Cada pila termina en una segura.

| Papel | Pila | Tamaño / interlineado | Peso y forma |
|---|---|---|---|
| Título del aviso (`<h1>`) | `'Mona Sans', Arial, Helvetica, sans-serif` | 24 / 29 px | 700, mayúsculas |
| Párrafo, saludo | `'Geist', Arial, Helvetica, sans-serif` | 16 / 24 px | 400 |
| Valor de dato, enlaces del calendario | `'Geist', Arial, Helvetica, sans-serif` | 14 / 20 px | 400 (enlaces 600) |
| Botón | `'Mona Sans', Arial, Helvetica, sans-serif` | 14 / 18 px | 700, mayúsculas |
| Etiqueta técnica, clave de dato, título de bloque | `'Geist Mono', Consolas, 'Courier New', monospace` | 11 / 14 px | 600, mayúsculas |
| Pie | `'Geist', Arial, Helvetica, sans-serif` | 12 / 18 px | 400 |

Unbounded no se usa: sin fuente web caería en un respaldo genérico y perdería su papel de voz display. Las mayúsculas se aplican con `text-transform: uppercase`; el texto se escribe en minúsculas normales para que el lector de pantalla y el texto plano lo lean bien. Outlook de Windows recibe `Arial` forzado en un `<style>` condicional `mso` (si no, cae en Times New Roman).

## Logo

**Decisión: imagen PNG incrustada por `cid:`**, con el nombre de marca como texto alternativo.

- [logo-correo.png](logo-correo.png): logo apilado ([logotipo](../fundamentos/logotipo.md)) en lavanda sobre navy **opaco**, 188 × 172 px (2×), mostrado a 94 × 86 px. Se generó desde `fundamentos/assets/logo-apilado.svg`; el backend lo copia a su paquete y lo adjunta en `multipart/related` con `Content-ID: <logo-bugalu>`.
- **Por qué `cid:`:** Gmail (web y móvil), Outlook y Apple Mail lo muestran sin pedir permiso para "descargar imágenes", que bloquea las remotas; el SVG no se admite en Gmail ni en Outlook; y no depende de un servidor público (ADR-016: sin imágenes remotas obligatorias).
- **Por qué opaco y sobre navy:** el modo oscuro de Gmail y Outlook invierte fondos claros pero no las imágenes; un PNG transparente navy desaparecería sobre el fondo oscurecido. Lavanda sobre navy cumple la regla 3 del logotipo (9,05:1).
- **Si la imagen no carga:** el `alt="Bugalú Studio"` se pinta con estilo en el propio `<img>` (lavanda, 700, 20 px) sobre la banda navy: queda el nombre de marca como texto.

## Bloques

En este orden, todos dentro del contenedor con borde. El HTML exacto está en [HTML de referencia](plantilla-html.md).

| # | Bloque | Contenido | Siempre |
|---|---|---|---|
| 0 | Previsualización | Texto oculto: primer párrafo del cuerpo, cortado a 110 caracteres por palabra, con "…" | Sí |
| 1 | Cabecera de marca | Banda navy, relleno 24 px, logo a la izquierda | Sí |
| 2 | Etiqueta y título | Etiqueta técnica del aviso (`// RESERVA`, ver [avisos](avisos.md)) y el **asunto** como `<h1>` | Sí |
| 3 | Saludo | "Hola:" | Sí |
| 4 | Cuerpo | El cuerpo de `redactar()` convertido en párrafos, tabla de datos y listas ([reglas](avisos.md#del-texto-al-html)) | Sí |
| 5 | Botón de acción | Un solo botón: [botón](../componentes/boton.md) Primario (lavanda, borde navy, texto navy); texto y destino por aviso | Sí |
| 6 | Evento de calendario | Fondo lavanda, borde navy; texto, aviso y enlaces ([evento](evento-calendario.md)) | Solo con evento |
| 7 | Pie | Regla superior navy; contacto, enlaces, datos de la empresa y motivo del envío | Sí |

El saludo no lleva nombre: los datos de los avisos no lo traen. Si algún día lo traen (`nombre_destinatario`), pasa a "Hola, {nombre}:".

## Pie: copy fijo

Variante **Cuenta** (avisos al cliente o a todas las cuentas) y **Administración** (avisos al Administrador); cuál usa cada aviso, en [avisos](avisos.md#por-tipo). `{url}` es la URL pública de la plataforma (configuración del backend, sin barra final).

| Línea | Cuenta | Administración |
|---|---|---|
| Marca (técnica, 11 px) | BUGALÚ STUDIO · CONVERGE Y CREA. | Igual |
| Ayuda | ¿Dudas? Responde a este correo o escríbenos por WhatsApp al +51 925 530 800. | — |
| Enlaces útiles | Mis reservas (`{url}/app/reservas`) · WhatsApp (`https://wa.me/51925530800`) · Instagram (`https://www.instagram.com/bugalu.studio`) · TikTok (`https://www.tiktok.com/@bugalu.studio`) · Facebook (`https://www.facebook.com/bugalu.studio`) | Panel de Bugalú (`{url}/app`) |
| Legales | Términos de uso (`{url}/legal/terminos-de-uso/`) · Política de privacidad (`{url}/legal/privacidad/`) · Condiciones de contratación (`{url}/legal/condiciones-de-contratacion/`) · Libro de Reclamaciones (`{url}/libro-de-reclamaciones/`) | Igual |
| Empresa (técnica, 11 px) | AURAL PERÚ E.I.R.L. · RUC 20615656128 · AV. JAVIER PRADO ESTE 5920, LA MOLINA, LIMA | Igual |
| Motivo del envío | Te enviamos este aviso porque tienes una cuenta en la plataforma de Bugalú Studio. Es parte del servicio, no publicidad. | Te enviamos este aviso porque eres Administrador en la plataforma de Bugalú Studio. |

Datos de la empresa y canales: [Términos de uso](../../08-legal/terminos-de-uso.md) ("Quiénes somos"). Enlaces legales: los del [pie público](../componentes/pie-publico.md).

## Modo oscuro

- `<meta name="color-scheme" content="light dark">` y `supported-color-schemes`.
- Apple Mail y Outlook de Mac/iOS aplican `@media (prefers-color-scheme: dark)`: fondo navy `#262757`; títulos, párrafos, valores y enlaces en lienzo `#EBEBFF` (11,83:1); etiqueta, claves y pie en lavanda `#E1C9E3` (9,05:1); bordes en lavanda; el bloque de calendario pasa a fondo navy con borde lavanda; el botón conserva lavanda con texto navy y su borde pasa a lavanda.
- Gmail y Outlook.com oscurecen por su cuenta e ignoran esa consulta: por eso no hay imágenes transparentes ni información que dependa solo del color.

## Accesibilidad

- `<html lang="es">`, `<title>` con el asunto y el contenido dentro de `<div role="article" aria-roledescription="correo" aria-label="{asunto}" lang="es">`.
- Orden de lectura = orden visual (una columna): marca, etiqueta, título, saludo, cuerpo, botón, calendario, pie. Tablas de maquetación con `role="presentation"`; la tabla de datos es una tabla real con `<th scope="row">`.
- Un `<h1>` (el asunto) y `<h2>` para el título del bloque de calendario.
- Botón y acciones son **enlaces `<a>`** con texto que dice adónde llevan ("Ver mi reserva", "Añadir a Google Calendar"); nunca "clic aquí" ni una imagen. Enlaces del pie y del calendario **subrayados**.
- Objetivos táctiles: botón ≥ 44 px de alto; enlaces del calendario y del pie con relleno vertical para ≥ 24 px ([WCAG 2.5.8](../componentes/README.md#estados-comunes)).
- Texto mínimo 11 px y solo en mayúsculas técnicas cortas; prosa a 16 px. El correo se lee al 200 % de zoom sin desbordar (ancho fluido, sin alturas fijas).
- Logo con `alt="Bugalú Studio"`; no hay otras imágenes.
- Todo dato que viene del usuario o de la base (nombres, motivos, notas) se escapa con `html.escape` antes de entrar al HTML.
