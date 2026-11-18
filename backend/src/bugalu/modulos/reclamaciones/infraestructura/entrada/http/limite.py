"""Tope temprano de `POST /reclamaciones[/transcripcion]`: rechaza por `Content-Length`."""

from starlette.types import ASGIApp, Receive, Scope, Send

from bugalu.compartido.errores import AdjuntoMuyGrande
from bugalu.compartido.manejadores_http import respuesta_de_error
from bugalu.modulos.reclamaciones.dominio.adjuntos import LIMITE_BYTES, MAXIMO

# 3 adjuntos de 5 MB mas el margen de los campos y de la envoltura multipart.
LIMITE_PETICION = MAXIMO * LIMITE_BYTES + 256 * 1024


class LimiteReclamaciones:
    # shortcut: sin `Content-Length` (chunked) el multipart se vuelca a disco antes del 413; en
    # produccion el servidor o proxy debe limitar el tamano del cuerpo.

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"]
            .rstrip("/")
            .endswith(("/reclamaciones", "/reclamaciones/transcripcion"))
        ):
            for nombre, valor in scope["headers"]:
                if nombre == b"content-length" and valor.isdigit() and int(valor) > LIMITE_PETICION:
                    respuesta = respuesta_de_error(
                        AdjuntoMuyGrande.estado_http,
                        AdjuntoMuyGrande.codigo,
                        "La hoja y sus adjuntos pesan demasiado (hasta 3 archivos de 5 MB).",
                    )
                    await respuesta(scope, receive, send)
                    return
        await self._app(scope, receive, send)
