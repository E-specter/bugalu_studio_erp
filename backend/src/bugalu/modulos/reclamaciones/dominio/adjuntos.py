"""Adjuntos de una hoja: hasta 3 PDF, JPG o PNG de 5 MB, verificados por el contenido (CA-06)."""

import re
from collections.abc import Sequence

from bugalu.compartido.errores import AdjuntoMuyGrande, AdjuntoNoPermitido, DemasiadosAdjuntos
from bugalu.modulos.reclamaciones.dominio.modelos import AdjuntoNuevo

LIMITE_BYTES = 5 * 1024 * 1024
MAXIMO = 3
_FIRMAS = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"%PDF-", "application/pdf", "pdf"),
)
_CONTROLES = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _nombre_limpio(nombre: str, n: int, extension: str) -> str:
    base = _CONTROLES.sub("", nombre).replace("\\", "/").rsplit("/", 1)[-1].strip()[:200]
    return base or f"adjunto-{n}.{extension}"


def validar_adjuntos(archivos: Sequence[tuple[str, bytes]]) -> list[AdjuntoNuevo]:
    """`archivos` son (nombre, contenido). El primero que falla manda, con su posicion desde 1."""
    if len(archivos) > MAXIMO:
        raise DemasiadosAdjuntos("Se admiten hasta 3 adjuntos.")
    validados = []
    for n, (nombre, contenido) in enumerate(archivos, start=1):
        if len(contenido) > LIMITE_BYTES:
            raise AdjuntoMuyGrande("Cada adjunto pesa hasta 5 MB.", {"adjunto": n})
        tipo = next(((m, e) for f, m, e in _FIRMAS if contenido.startswith(f)), None)
        if tipo is None:
            raise AdjuntoNoPermitido("Los adjuntos son PDF, JPG o PNG.", {"adjunto": n})
        validados.append(
            AdjuntoNuevo(
                n, _nombre_limpio(nombre, n, tipo[1]), tipo[0], len(contenido), contenido, tipo[1]
            )
        )
    return validados
