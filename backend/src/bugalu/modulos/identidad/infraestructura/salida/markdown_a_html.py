"""Markdown de un texto legal a HTML saneado (CA-14): sin HTML crudo, enlaces seguros."""

import re
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token

_MD = MarkdownIt("commonmark", {"html": False})  # el HTML crudo sale escapado como texto
_ATRIBUTO = {"link_open": "href", "image": "src"}
_CORREO = re.compile(r"[^\s:,;?#/<>@]+@[^\s:,;?#/<>@]+")  # una sola direccion, sin parametros


def _permitido(destino: str) -> bool:
    partes = urlsplit(destino.strip())
    if partes.scheme.lower() == "mailto":
        return _CORREO.fullmatch(partes.path) is not None and not partes.query
    if partes.scheme:
        return partes.scheme.lower() in ("http", "https") and bool(partes.netloc)
    primer_tramo = partes.path.split("/")[0]
    return not partes.netloc and ":" not in primer_tramo  # `//otro.sitio` y `x:y` no son relativos


def _sanear(tokens: list[Token]) -> None:
    for token in tokens:
        atributo = _ATRIBUTO.get(token.type)
        if atributo and not _permitido(str(token.attrGet(atributo) or "")):
            token.attrs.pop(atributo, None)
        if token.children:
            _sanear(token.children)


def markdown_a_html(texto: str) -> str:
    tokens = _MD.parse(texto)
    _sanear(tokens)
    return str(_MD.renderer.render(tokens, _MD.options, {}))
