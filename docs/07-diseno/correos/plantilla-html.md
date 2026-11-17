---
id: correo-plantilla-html
titulo: Correo — HTML y texto plano de referencia
estado: borrador
depende_de: [correo-plantilla]
---

# HTML y texto plano de referencia

Esqueleto de la [plantilla](plantilla.md). `{…}` son huecos que rellena el backend (escapados con `html.escape`); los comentarios `[…]` marcan bloques opcionales. Las clases `b-*` solo sirven al modo oscuro: los estilos en línea son la fuente.

```html
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{asunto}</title>
<!--[if mso]><style>body,table,td,th,h1,h2,p,a{font-family:Arial,Helvetica,sans-serif !important;}</style><![endif]-->
<style>
  @media (min-width: 37.5em) { .b-relleno { padding: 24px !important; } } /* punto-quiebre-tableta */
  @media (prefers-color-scheme: dark) {
    body, .b-fondo, .b-contenedor { background: #262757 !important; }
    .b-contenedor, .b-regla, .b-dato { border-color: #E1C9E3 !important; }
    .b-texto { color: #EBEBFF !important; }
    .b-sec { color: #E1C9E3 !important; }
    .b-destacado { background: #262757 !important; border-color: #E1C9E3 !important; }
    .b-boton { border-color: #E1C9E3 !important; }
  }
</style>
</head>
<body class="b-fondo" style="margin:0;padding:0;background:#EBEBFF;">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preheader}</div>
<div role="article" aria-roledescription="correo" aria-label="{asunto}" lang="es">
<table role="presentation" class="b-fondo" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#EBEBFF;">
<tr><td align="center" style="padding:16px 8px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" class="b-contenedor" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background:#EBEBFF;border:2px solid #262757;">

<!-- 1 Cabecera de marca -->
<tr><td style="background:#262757;padding:24px;">
  <img src="cid:logo-bugalu" width="94" height="86" alt="Bugalú Studio" style="display:block;border:0;color:#E1C9E3;font-family:Arial,Helvetica,sans-serif;font-size:20px;font-weight:700;">
</td></tr>

<tr><td class="b-relleno" style="padding:16px;">
  <!-- 2 Etiqueta y título -->
  <p class="b-sec" style="margin:0 0 8px;font-family:'Geist Mono',Consolas,'Courier New',monospace;font-size:11px;line-height:14px;font-weight:600;text-transform:uppercase;color:#4A4B7D;">// {etiqueta}</p>
  <h1 class="b-texto" style="margin:0 0 24px;font-family:'Mona Sans',Arial,Helvetica,sans-serif;font-size:24px;line-height:29px;font-weight:700;text-transform:uppercase;color:#262757;">{asunto}</h1>
  <!-- 3 Saludo y 4 Cuerpo: párrafos -->
  <p class="b-texto" style="margin:0 0 16px;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:16px;line-height:24px;color:#231F20;">Hola:</p>
  <p class="b-texto" style="margin:0 0 16px;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:16px;line-height:24px;color:#231F20;">{párrafo}</p>
  <!-- 4 Cuerpo: tabla de datos (una fila por línea "Clave: valor") -->
  <table class="b-regla" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;border-top:1px solid #262757;margin:0 0 16px;">
    <tr>
      <th scope="row" class="b-sec b-dato" style="width:38%;padding:8px 12px 8px 0;text-align:left;vertical-align:top;border-bottom:1px solid #262757;font-family:'Geist Mono',Consolas,'Courier New',monospace;font-size:11px;line-height:14px;font-weight:600;text-transform:uppercase;color:#4A4B7D;">{clave}</th>
      <td class="b-texto b-dato" style="padding:8px 0;vertical-align:top;border-bottom:1px solid #262757;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:14px;line-height:20px;color:#262757;">{valor}</td>
    </tr>
  </table>
  <!-- 4 Cuerpo: lista (líneas "- ") -->
  <ul class="b-texto" style="margin:0 0 16px;padding:0 0 0 20px;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:16px;line-height:24px;color:#231F20;"><li>{elemento}</li></ul>
  <!-- 5 Botón de acción -->
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 24px;"><tr>
    <td class="b-boton" style="background:#E1C9E3;border:2px solid #262757;">
      <a href="{url_boton}" style="display:inline-block;padding:12px 20px;font-family:'Mona Sans',Arial,Helvetica,sans-serif;font-size:14px;line-height:18px;font-weight:700;text-transform:uppercase;color:#262757;text-decoration:none;">{texto_boton}</a>
    </td></tr></table>
  <!-- [6 Evento de calendario: solo con evento] -->
  <table role="presentation" class="b-destacado" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#E1C9E3;border:2px solid #262757;margin:0 0 8px;"><tr><td style="padding:16px;">
    <h2 class="b-texto" style="margin:0 0 8px;font-family:'Geist Mono',Consolas,'Courier New',monospace;font-size:11px;line-height:14px;font-weight:600;text-transform:uppercase;color:#262757;">Evento de calendario</h2>
    <p class="b-texto" style="margin:0 0 8px;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:16px;line-height:24px;color:#231F20;">{texto del evento}</p>
    <p class="b-texto" style="margin:0 0 8px;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:16px;line-height:24px;color:#231F20;">{aviso de ADR-016}</p>
    <!-- [Enlaces: solo REQUEST] -->
    <p style="margin:0;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:14px;line-height:20px;">
      <a class="b-texto" href="{url_google}" style="display:inline-block;padding:6px 0;font-weight:600;color:#262757;text-decoration:underline;">Añadir a Google Calendar</a><br>
      <a class="b-texto" href="{url_outlook}" style="display:inline-block;padding:6px 0;font-weight:600;color:#262757;text-decoration:underline;">Añadir a Outlook</a>
    </p>
  </td></tr></table>
</td></tr>

<!-- 7 Pie -->
<tr><td class="b-relleno b-regla" style="padding:16px;border-top:2px solid #262757;font-family:'Geist',Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#4A4B7D;">
  <p class="b-sec" style="margin:0 0 8px;font-family:'Geist Mono',Consolas,'Courier New',monospace;font-size:11px;line-height:14px;font-weight:600;text-transform:uppercase;">Bugalú Studio · Converge y crea.</p>
  <p class="b-sec" style="margin:0 0 8px;">{línea de ayuda}</p>
  <p style="margin:0 0 8px;"><a class="b-texto" href="{url}/app/reservas" style="display:inline-block;padding:3px 0;color:#262757;text-decoration:underline;">Mis reservas</a> · {demás enlaces útiles, mismo estilo}</p>
  <p style="margin:0 0 8px;">{enlaces legales, mismo estilo}</p>
  <p class="b-sec" style="margin:0 0 8px;font-family:'Geist Mono',Consolas,'Courier New',monospace;font-size:11px;line-height:14px;text-transform:uppercase;">Aural Perú E.I.R.L. · RUC 20615656128 · Av. Javier Prado Este 5920, La Molina, Lima</p>
  <p class="b-sec" style="margin:0;">{motivo del envío}</p>
</td></tr>

</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table>
</div>
</body>
</html>
```

Notas:

- Las mayúsculas las pone `text-transform`: en el HTML el texto va como en el copy ("Ver mi reserva").
- Separador de enlaces: " · " como texto, no como imagen.
- El botón es un enlace dentro de una celda con fondo: en Outlook de escritorio solo el texto es pulsable, que es aceptable; no se usa VML.

## Texto plano

Misma información y mismo orden, sin HTML. El cuerpo va **tal cual** sale de `redactar()`.

```
BUGALÚ STUDIO
// {ETIQUETA}

{Asunto}

Hola:

{cuerpo de redactar(), sin cambios}

{Texto del botón}: {url del botón}

[Solo con evento: bloque de texto de evento-calendario.md]

--
Bugalú Studio · Converge y crea.
{Línea de ayuda, solo Cuenta}
Mis reservas: {url}/app/reservas        (Administración: Panel de Bugalú: {url}/app)
WhatsApp: +51 925 530 800 · Instagram y TikTok: @bugalu.studio · Facebook: facebook.com/bugalu.studio   (solo Cuenta)
Términos de uso: {url}/legal/terminos-de-uso/
Política de privacidad: {url}/legal/privacidad/
Condiciones de contratación: {url}/legal/condiciones-de-contratacion/
Libro de Reclamaciones: {url}/libro-de-reclamaciones/
Aural Perú E.I.R.L. · RUC 20615656128 · Av. Javier Prado Este 5920, La Molina, Lima
{Motivo del envío}
```
