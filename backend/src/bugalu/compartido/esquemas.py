from pydantic import BaseModel


class DetalleError(BaseModel):
    codigo: str
    mensaje: str


class RespuestaError(BaseModel):
    error: DetalleError
