from dataclasses import dataclass


@dataclass(frozen=True)
class Correo:
    destinatario: str
    asunto: str
    cuerpo: str

    def __post_init__(self) -> None:
        # Inyeccion de cabeceras: ni el destinatario ni el asunto pueden traer CR/LF.
        for valor in (self.destinatario, self.asunto):
            if "\r" in valor or "\n" in valor:
                raise ValueError("salto de linea en una cabecera del correo")
