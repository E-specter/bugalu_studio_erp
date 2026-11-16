"""Capturas de comprobante: el tipo sale de la firma de los bytes, no del nombre ni del mime."""

from dataclasses import dataclass

LIMITE_BYTES = 5 * 1024 * 1024
BYTES_FIRMA = 8


@dataclass(frozen=True)
class TipoCaptura:
    mime: str
    extension: str
    clase: str  # "imagen" | "pdf"


_FIRMAS = (
    (b"\xff\xd8\xff", TipoCaptura("image/jpeg", "jpg", "imagen")),
    (b"\x89PNG\r\n\x1a\n", TipoCaptura("image/png", "png", "imagen")),
    (b"%PDF-", TipoCaptura("application/pdf", "pdf", "pdf")),
)


def detectar_tipo(cabecera: bytes) -> TipoCaptura | None:
    return next((tipo for firma, tipo in _FIRMAS if cabecera.startswith(firma)), None)


def tipo_por_mime(mime: str) -> TipoCaptura:
    return next(tipo for _, tipo in _FIRMAS if tipo.mime == mime)
