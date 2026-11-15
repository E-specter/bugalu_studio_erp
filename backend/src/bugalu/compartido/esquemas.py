from typing import Annotated

from pydantic import BaseModel, StringConstraints

# Todo texto de entrada usa uno de estos tipos: un NUL tumba la base (DataError) y los controles
# ensucian lo que se muestra despues. El largo admite ademas salto de linea y tabulador.
TextoCorto = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$"
    ),
]
TextoLargo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=500, pattern=r"^[^\x00-\x08\x0b-\x1f\x7f]+$"
    ),
]


class DetalleError(BaseModel):
    codigo: str
    mensaje: str


class RespuestaError(BaseModel):
    error: DetalleError
