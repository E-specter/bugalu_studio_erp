"""Plantilla de marca de los correos (ADR-016): HTML con estilos en linea y texto plano.

El asunto y el cuerpo siguen saliendo de `redactar()`; aqui solo se enmarcan. Los colores y
tamanos son los literales de los tokens (docs/07-diseno/correos/plantilla.md).
"""

import re
from dataclasses import dataclass
from html import escape
from typing import Any
from urllib.parse import quote

from bugalu.modulos.notificaciones.dominio.calendario import AVISO_ADR_016

_DETALLE = "/app/reservas/detalle?id={id_reserva}"
_CREDITOS = "/app/reservas/creditos"
_RUTAS_LEGALES = {
    "terminos_uso": "terminos-de-uso",
    "politica_privacidad": "privacidad",
    "condiciones_contratacion": "condiciones-de-contratacion",
    "declaracion_agrupacion": "declaracion-de-agrupacion",
}


@dataclass(frozen=True)
class Aviso:
    etiqueta: str
    para_admin: bool  # pie de Administracion en vez del de Cuenta
    texto_boton: str
    ruta: str  # relativa a la URL publica (o absoluta); admite {campos} de los datos del aviso
    para_reclamo: bool = (
        False  # pie del Libro de Reclamaciones: quien reclama puede no tener cuenta
    )


def _aviso(etiqueta: str, texto: str, ruta: str, admin: bool = False) -> Aviso:
    return Aviso(etiqueta, admin, texto, ruta)


_DETALLE_HOJA = "/app/reclamos/detalle?id={id}"
_LIBRO = "LIBRO DE RECLAMACIONES"
_COPIA_HOJA = Aviso(_LIBRO, False, "Ver mi hoja", _DETALLE_HOJA, True)
_SIN_CUENTA = Aviso(_LIBRO, False, "Escribirnos por WhatsApp", "https://wa.me/51925530800", True)


_VER_MI = _aviso("RESERVA", "Ver mi reserva", _DETALLE)
AVISOS: dict[str, Aviso] = {
    "reserva_creada": _VER_MI,
    "reserva_caducada": _aviso("RESERVA", "Reservar otro horario", "/reservar/"),
    "pago_registrado": _aviso("PAGO", "Revisar el pago", "/app/pagos/revisar?id={id_pago}", True),
    "pago_aprobado": _aviso("PAGO", "Ver mi reserva", _DETALLE),
    "pago_rechazado": _aviso("PAGO", "Ver mi reserva", _DETALLE),
    "reserva_finalizada_saldo": _VER_MI,
    "reserva_cancelada_estudio": _VER_MI,
    "reserva_cancelada_cliente": _aviso("RESERVA", "Ver la reserva", _DETALLE, True),
    "reserva_cancelada_con_pagos": _VER_MI,
    "reserva_reprogramada": _VER_MI,
    "inasistencia_marcada": _VER_MI,
    "eleccion_estudio_resuelta": _aviso("RESERVA", "Ver la reserva", _DETALLE, True),
    "credito_por_vencer": _aviso("CRÉDITO", "Ver mis créditos", _CREDITOS),
    "devolucion_solicitada": _aviso(
        "DEVOLUCIÓN",
        "Revisar la devolución",
        "/app/pagos/devoluciones/revisar?id={id_devolucion}",
        True,
    ),
    "devolucion_decidida": _aviso("DEVOLUCIÓN", "Ver mis créditos", _CREDITOS),
    "devolucion_realizada": _aviso("DEVOLUCIÓN", "Ver mis créditos", _CREDITOS),
    "texto_legal_nuevo": _aviso("TEXTOS LEGALES", "Leer el texto", "/legal/{ruta}/"),
    "reclamacion_registrada": _COPIA_HOJA,
    "reclamacion_recibida": _aviso(_LIBRO, "Revisar la hoja", _DETALLE_HOJA, True),
    "reclamacion_respondida": _COPIA_HOJA,
    "reclamaciones_por_vencer": _aviso(
        _LIBRO, "Ver hojas pendientes", "/app/reclamos/?estado=pendiente", True
    ),
}
_SIN_CUENTA_SI_FALTA = frozenset({"reclamacion_registrada", "reclamacion_respondida"})


def _aviso_de(tipo: str, datos: dict[str, Any]) -> Aviso:
    """Quien reclama puede no tener cuenta: la copia y la respuesta lo mandan a WhatsApp."""
    if tipo in _SIN_CUENTA_SI_FALTA and not datos.get("con_cuenta"):
        return _SIN_CUENTA
    return AVISOS.get(tipo, _GENERICO)


_GENERICO = _aviso("AVISO", "Ir a la plataforma", "/app")


@dataclass(frozen=True)
class BloqueEvento:
    texto: str
    con_aviso: bool  # el aviso de ADR-016 (solo REQUEST)
    url_google: str | None
    url_outlook: str | None


# -- Del texto al HTML --------------------------------------------------------------------------

_DATO = re.compile(r"^[A-ZÁÉÍÓÚÑÜ][^:]{0,39}: .+$")


def _tipo_linea(linea: str) -> str:
    if linea.startswith("- "):
        return "lista"
    return "tabla" if _DATO.match(linea) else "p"


def bloques_del_cuerpo(cuerpo: str) -> list[tuple[str, Any]]:
    """Lista de ("p", lineas), ("tabla", [(clave, valor)]) o ("lista", elementos)."""
    bloques: list[tuple[str, Any]] = []
    for bloque in re.split(r"\n\s*\n", cuerpo.strip("\n")):
        tipos = [(linea, _tipo_linea(linea)) for linea in bloque.split("\n") if linea.strip()]
        # Una sola linea "Clave: valor", sin otra al lado, es parrafo y no tabla.
        for i, (linea, tipo) in enumerate(tipos):
            junto = (i > 0 and tipos[i - 1][1] == "tabla") or (
                i + 1 < len(tipos) and tipos[i + 1][1] == "tabla"
            )
            if tipo == "tabla" and not junto:
                tipos[i] = (linea, "p")
        # Cada bloque separado por una linea en blanco empieza grupo nuevo.
        primero = len(bloques)
        for linea, tipo in tipos:
            if len(bloques) > primero and bloques[-1][0] == tipo:
                bloques[-1][1].append(_valor(linea, tipo))
            else:
                bloques.append((tipo, [_valor(linea, tipo)]))
    return bloques


def _valor(linea: str, tipo: str) -> Any:
    if tipo == "lista":
        return linea[2:]
    if tipo == "tabla":
        clave, valor = linea.split(": ", 1)
        return (clave, valor)
    return linea


# -- Estilos ------------------------------------------------------------------------------------

_SANS = "'Geist',Arial,Helvetica,sans-serif"
_MONO = "'Geist Mono',Consolas,'Courier New',monospace"
_MONA = "'Mona Sans',Arial,Helvetica,sans-serif"
_PARRAFO = f"margin:0 0 16px;font-family:{_SANS};font-size:16px;line-height:24px;color:#231F20;"
_TECNICO = (
    f"font-family:{_MONO};font-size:11px;line-height:14px;font-weight:600;text-transform:uppercase;"
)
_ENLACE = "display:inline-block;padding:3px 0;color:#262757;text-decoration:underline;"

_CABECERA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{asunto}</title>
<!--[if mso]><style>body,table,td,th,h1,h2,p,a{{font-family:Arial,Helvetica,sans-serif !important;}}</style><![endif]-->
<style>
  @media (min-width: 37.5em) {{ .b-relleno {{ padding: 24px !important; }} }}
  @media (prefers-color-scheme: dark) {{
    body, .b-fondo, .b-contenedor {{ background: #262757 !important; }}
    .b-contenedor, .b-regla, .b-dato {{ border-color: #E1C9E3 !important; }}
    .b-texto {{ color: #EBEBFF !important; }}
    .b-sec {{ color: #E1C9E3 !important; }}
    .b-destacado {{ background: #262757 !important; border-color: #E1C9E3 !important; }}
    .b-boton {{ border-color: #E1C9E3 !important; }}
  }}
</style>
</head>
"""  # noqa: E501


def _p(texto_html: str, extra: str = "") -> str:
    return f'<p class="b-texto" style="{_PARRAFO}{extra}">{texto_html}</p>\n'


def _html_cuerpo(bloques: list[tuple[str, Any]]) -> str:
    salida = []
    for tipo, items in bloques:
        if tipo == "p":
            salida.append(_p("<br>".join(escape(x) for x in items)))
        elif tipo == "lista":
            lis = "".join(f"<li>{escape(x)}</li>" for x in items)
            salida.append(
                f'<ul class="b-texto" style="margin:0 0 16px;padding:0 0 0 20px;'
                f'font-family:{_SANS};font-size:16px;line-height:24px;color:#231F20;">{lis}</ul>\n'
            )
        else:
            filas = "".join(
                f'<tr><th scope="row" class="b-sec b-dato" style="width:38%;'
                "padding:8px 12px 8px 0;text-align:left;vertical-align:top;"
                f'border-bottom:1px solid #262757;{_TECNICO}color:#4A4B7D;">{escape(k)}</th>'
                f'<td class="b-texto b-dato" style="padding:8px 0;vertical-align:top;'
                f"border-bottom:1px solid #262757;font-family:{_SANS};font-size:14px;"
                f'line-height:20px;color:#262757;">{escape(v)}</td></tr>'
                for k, v in items
            )
            salida.append(
                '<table class="b-regla" width="100%" cellpadding="0" cellspacing="0" border="0" '
                f'style="border-collapse:collapse;border-top:1px solid #262757;margin:0 0 16px;">'
                f"{filas}</table>\n"
            )
    return "".join(salida)


def _previa(bloques: list[tuple[str, Any]], asunto: str) -> str:
    texto = next((" ".join(i) for t, i in bloques if t == "p"), asunto)
    if len(texto) <= 110:
        return texto
    return texto[:110].rsplit(" ", 1)[0].rstrip() + "…"


def _html_evento(e: BloqueEvento) -> str:
    aviso = _p(escape(AVISO_ADR_016), "margin:0 0 8px;") if e.con_aviso else ""
    estilo_a = "display:inline-block;padding:6px 0;font-weight:600;color:#262757;"
    enlaces = ""
    if e.url_google and e.url_outlook:
        enlaces = (
            f'<p style="margin:0;font-family:{_SANS};font-size:14px;line-height:20px;">'
            f'<a class="b-texto" href="{escape(e.url_google)}" style="{estilo_a}'
            'text-decoration:underline;">Añadir a Google Calendar</a><br>'
            f'<a class="b-texto" href="{escape(e.url_outlook)}" style="{estilo_a}'
            'text-decoration:underline;">Añadir a Outlook</a></p>\n'
        )
    return (
        '<table role="presentation" class="b-destacado" width="100%" cellpadding="0" '
        'cellspacing="0" border="0" style="background:#E1C9E3;border:2px solid #262757;'
        'margin:0 0 8px;"><tr><td style="padding:16px;">\n'
        f'<h2 class="b-texto" style="margin:0 0 8px;{_TECNICO}color:#262757;">'
        "Evento de calendario</h2>\n"
        + _p(escape(e.texto), "margin:0 0 8px;")
        + aviso
        + enlaces
        + "</td></tr></table>\n"
    )


def _pie(
    para_admin: bool, url: str, para_reclamo: bool = False
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    util = (
        [("Panel de Bugalú", f"{url}/app")]
        if para_admin
        else [
            *([] if para_reclamo else [("Mis reservas", f"{url}/app/reservas")]),
            ("WhatsApp", "https://wa.me/51925530800"),
            ("Instagram", "https://www.instagram.com/bugalu.studio"),
            ("TikTok", "https://www.tiktok.com/@bugalu.studio"),
            ("Facebook", "https://www.facebook.com/bugalu.studio"),
        ]
    )
    legales = [
        ("Términos de uso", f"{url}/legal/terminos-de-uso/"),
        ("Política de privacidad", f"{url}/legal/privacidad/"),
        ("Condiciones de contratación", f"{url}/legal/condiciones-de-contratacion/"),
        ("Libro de Reclamaciones", f"{url}/libro-de-reclamaciones/"),
    ]
    return util, legales


_AYUDA = "¿Dudas? Responde a este correo o escríbenos por WhatsApp al +51 925 530 800."
_EMPRESA = "Aural Perú E.I.R.L. · RUC 20615656128 · Av. Javier Prado Este 5920, La Molina, Lima"
_MOTIVO_CUENTA = (
    "Te enviamos este aviso porque tienes una cuenta en la plataforma de Bugalú Studio. "
    "Es parte del servicio, no publicidad."
)
_MOTIVO_RECLAMO = (
    "Te enviamos este correo porque presentaste una hoja en el Libro de Reclamaciones de "
    "Bugalú Studio."
)
_MOTIVO_ADMIN = (
    "Te enviamos este aviso porque eres Administrador en la plataforma de Bugalú Studio."
)


def _motivo(aviso: Aviso) -> str:
    if aviso.para_admin:
        return _MOTIVO_ADMIN
    return _MOTIVO_RECLAMO if aviso.para_reclamo else _MOTIVO_CUENTA


def _enlaces_html(enlaces: list[tuple[str, str]]) -> str:
    return " · ".join(
        f'<a class="b-texto" href="{escape(u)}" style="{_ENLACE}">{escape(t)}</a>'
        for t, u in enlaces
    )


def _html_pie(aviso: Aviso, url: str) -> str:
    util, legales = _pie(aviso.para_admin, url, aviso.para_reclamo)
    ayuda = "" if aviso.para_admin else f'<p class="b-sec" style="margin:0 0 8px;">{_AYUDA}</p>\n'
    motivo = _motivo(aviso)
    return (
        '<tr><td class="b-relleno b-regla" style="padding:16px;border-top:2px solid #262757;'
        f'font-family:{_SANS};font-size:12px;line-height:18px;color:#4A4B7D;">\n'
        f'<p class="b-sec" style="margin:0 0 8px;{_TECNICO}">Bugalú Studio · Converge y crea.</p>\n'
        f"{ayuda}"
        f'<p style="margin:0 0 8px;">{_enlaces_html(util)}</p>\n'
        f'<p style="margin:0 0 8px;">{_enlaces_html(legales)}</p>\n'
        f'<p class="b-sec" style="margin:0 0 8px;{_TECNICO}font-weight:400;">{_EMPRESA}</p>\n'
        f'<p class="b-sec" style="margin:0;">{motivo}</p>\n'
        "</td></tr>\n"
    )


def _texto_pie(aviso: Aviso, url: str) -> str:
    util, legales = _pie(aviso.para_admin, url, aviso.para_reclamo)
    if aviso.para_admin:
        lineas = [f"{util[0][0]}: {util[0][1]}"]
    else:
        lineas = [
            _AYUDA,
            *([] if aviso.para_reclamo else [f"{util[0][0]}: {util[0][1]}"]),
            "WhatsApp: +51 925 530 800 · Instagram y TikTok: @bugalu.studio · "
            "Facebook: facebook.com/bugalu.studio",
        ]
    lineas += [f"{t}: {u}" for t, u in legales]
    lineas += [_EMPRESA, _motivo(aviso)]
    return "\n".join(["--", "Bugalú Studio · Converge y crea.", *lineas])


def _texto_evento(e: BloqueEvento) -> str:
    lineas = ["EVENTO DE CALENDARIO", e.texto]
    if e.con_aviso:
        lineas.append(AVISO_ADR_016)
    if e.url_google and e.url_outlook:
        lineas += [
            f"Añadir a Google Calendar: {e.url_google}",
            f"Añadir a Outlook: {e.url_outlook}",
        ]
    return "\n".join(lineas) + "\n"


def _url_boton(aviso: Aviso, datos: dict[str, Any], url: str) -> str:
    if aviso.ruta.startswith("https://"):
        return aviso.ruta
    campos = {k: quote(str(v), safe="") for k, v in datos.items()}
    if "tipo" in datos:
        campos["ruta"] = _RUTAS_LEGALES.get(str(datos["tipo"]), quote(str(datos["tipo"])))
    return url + aviso.ruta.format_map(campos)


def componer(
    tipo: str,
    datos: dict[str, Any],
    asunto: str,
    cuerpo: str,
    url_publica: str,
    evento: BloqueEvento | None,
) -> tuple[str, str]:
    """Devuelve (texto plano, HTML) del aviso ya redactado."""
    url = url_publica.rstrip("/")
    aviso = _aviso_de(tipo, datos)
    destino = _url_boton(aviso, datos, url)
    bloques = bloques_del_cuerpo(cuerpo)

    texto = (
        f"BUGALÚ STUDIO\n// {aviso.etiqueta}\n\n{asunto}\n\nHola:\n\n{cuerpo.rstrip()}\n\n"
        f"{aviso.texto_boton}: {destino}\n\n"
        + (_texto_evento(evento) + "\n" if evento else "")
        + _texto_pie(aviso, url)
        + "\n"
    )

    a = escape(asunto)
    html = (
        _CABECERA.format(asunto=a)
        + '<body class="b-fondo" style="margin:0;padding:0;background:#EBEBFF;">\n'
        f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">'
        f"{escape(_previa(bloques, asunto))}</div>\n"
        f'<div role="article" aria-roledescription="correo" aria-label="{a}" lang="es">\n'
        '<table role="presentation" class="b-fondo" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="background:#EBEBFF;">\n'
        '<tr><td align="center" style="padding:16px 8px;">\n'
        '<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'border="0"><tr><td><![endif]-->\n'
        '<table role="presentation" class="b-contenedor" width="100%" cellpadding="0" '
        'cellspacing="0" border="0" style="max-width:600px;background:#EBEBFF;'
        'border:2px solid #262757;">\n'
        '<tr><td style="background:#262757;padding:24px;">\n'
        '<img src="cid:logo-bugalu" width="94" height="86" alt="Bugalú Studio" '
        'style="display:block;border:0;color:#E1C9E3;font-family:Arial,Helvetica,sans-serif;'
        'font-size:20px;font-weight:700;"></td></tr>\n'
        '<tr><td class="b-relleno" style="padding:16px;">\n'
        f'<p class="b-sec" style="margin:0 0 8px;{_TECNICO}color:#4A4B7D;">'
        f"// {aviso.etiqueta}</p>\n"
        f'<h1 class="b-texto" style="margin:0 0 24px;font-family:{_MONA};font-size:24px;'
        f'line-height:29px;font-weight:700;text-transform:uppercase;color:#262757;">{a}</h1>\n'
        + _p("Hola:")
        + _html_cuerpo(bloques)
        + '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:8px 0 24px;"><tr><td class="b-boton" style="background:#E1C9E3;'
        f'border:2px solid #262757;"><a href="{escape(destino)}" style="display:inline-block;'
        f"padding:12px 20px;font-family:{_MONA};font-size:14px;line-height:18px;"
        'font-weight:700;text-transform:uppercase;color:#262757;text-decoration:none;">'
        f"{escape(aviso.texto_boton)}</a></td></tr></table>\n"
        + (_html_evento(evento) if evento else "")
        + "</td></tr>\n"
        + _html_pie(aviso, url)
        + "</table>\n<!--[if mso]></td></tr></table><![endif]-->\n</td></tr></table>\n</div>\n"
        "</body>\n</html>\n"
    )
    return texto, html
