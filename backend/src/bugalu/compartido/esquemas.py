from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, StringConstraints

# Todo texto de entrada usa uno de estos tipos: un NUL tumba la base (DataError) y los controles
# ensucian lo que se muestra despues. Tambien se rechazan los controles C1 y U+2028/U+2029.
# El largo admite ademas salto de linea, retorno de carro (se normaliza a \n) y tabulador.
TextoCorto = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
        pattern=r"^[^\x00-\x1f\x7f-\x9f  ]+$",
    ),
]
TextoLargo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=500,
        pattern=r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f  ]+$",
    ),
    AfterValidator(lambda v: v.replace("\r\n", "\n").replace("\r", "\n")),
]


class DetalleError(BaseModel):
    codigo: str
    mensaje: str
    detalles: dict[str, Any] | None = None


class RespuestaError(BaseModel):
    error: DetalleError
