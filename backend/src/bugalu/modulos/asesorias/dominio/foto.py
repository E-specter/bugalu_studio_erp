"""Fotos de perfil: el tipo sale de la firma de los bytes, no del nombre ni del mime declarado."""

from dataclasses import dataclass

LIMITE_BYTES = 2 * 1024 * 1024
BYTES_FIRMA = 12


@dataclass(frozen=True)
class TipoFoto:
    mime: str
    extension: str


def detectar_tipo(cabecera: bytes) -> TipoFoto | None:
    if cabecera.startswith(b"\xff\xd8\xff"):
        return TipoFoto("image/jpeg", "jpg")
    if cabecera.startswith(b"\x89PNG\r\n\x1a\n"):
        return TipoFoto("image/png", "png")
    if cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        return TipoFoto("image/webp", "webp")
    return None
