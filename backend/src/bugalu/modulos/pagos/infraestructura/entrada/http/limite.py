"""Tope temprano de `POST /pagos`: rechaza por `Content-Length` antes de leer el formulario."""

from starlette.types import ASGIApp, Receive, Scope, Send

from bugalu.compartido.errores import ArchivoMuyGrande
from bugalu.compartido.manejadores_http import respuesta_de_error
from bugalu.modulos.pagos.dominio.captura import LIMITE_BYTES

# 5 MB de captura mas el margen de los campos y de la envoltura multipart.
LIMITE_PETICION = LIMITE_BYTES + 64 * 1024


class LimitePagos:
    """Sin `Content-Length` (chunked) pasa: el limite de lectura de la captura sigue vigente."""

    # shortcut: sin `Content-Length` (chunked) el multipart se vuelca a disco antes del 413; en
    # produccion el servidor o proxy debe limitar el tamano del cuerpo (ver montaje-local.md).

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"].endswith("/pagos")
        ):
            for nombre, valor in scope["headers"]:
                if nombre == b"content-length" and valor.isdigit() and int(valor) > LIMITE_PETICION:
                    respuesta = respuesta_de_error(
                        ArchivoMuyGrande.estado_http,
                        ArchivoMuyGrande.codigo,
                        "La captura pesa mas de 5 MB.",
                    )
                    await respuesta(scope, receive, send)
                    return
        await self._app(scope, receive, send)
