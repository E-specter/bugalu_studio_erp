from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, get_args
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from bugalu.modulos.identidad.dominio import textos_legales as dominio
from bugalu.modulos.identidad.infraestructura.salida.markdown_a_html import markdown_a_html

Tipo = Literal[
    "terminos_uso", "politica_privacidad", "condiciones_contratacion", "declaracion_agrupacion"
]
TipoCambio = Literal["mayor", "menor", "parche"]
Contexto = Literal[
    "registro", "reserva", "asesoria", "pago", "menor", "promociones", "usos_promocionales"
]


def _sin_nul_ni_blanco(valor: str) -> str:
    if "\x00" in valor or not valor.strip():
        raise ValueError("texto vacio o con caracteres no permitidos")
    return valor


Markdown = Annotated[str, StringConstraints(max_length=300_000), AfterValidator(_sin_nul_ni_blanco)]
Resumen = Annotated[str, StringConstraints(min_length=1, max_length=2000, pattern=r"^[^\x00]+$")]


class NuevoTexto(BaseModel):
    tipo: Tipo
    version: Annotated[str, StringConstraints(max_length=29)]  # el formato lo valida el dominio
    tipo_cambio: TipoCambio
    contenido: Markdown
    resumenes: dict[str, Resumen] = {}
    resumen_cambios: (
        Annotated[str, StringConstraints(min_length=1, max_length=500, pattern=r"^[^\x00]+$")]
        | None
    ) = None
    vigente_desde: AwareDatetime | None = None

    @field_validator("resumenes")
    @classmethod
    def _contextos_conocidos(cls, valor: dict[str, str]) -> dict[str, str]:
        if not set(valor) <= set(get_args(Contexto)):
            raise ValueError("contexto desconocido")
        return valor


class NuevaVistaPrevia(BaseModel):
    """Mismo limite que publicar: lo que se previsualiza se puede publicar."""

    model_config = ConfigDict(extra="forbid")
    contenido: Markdown


class VistaPrevia(BaseModel):
    contenido_html: str


class TextoResumen(BaseModel):
    tipo: str
    version: str
    tipo_cambio: str
    vigente_desde: datetime
    resumenes: dict[str, str]
    resumen_cambios: str | None
    programada: bool

    @classmethod
    def desde_dominio(cls, texto: dominio.TextoLegal) -> TextoResumen:
        return cls(
            tipo=texto.tipo,
            version=texto.version,
            tipo_cambio=texto.tipo_cambio,
            vigente_desde=texto.vigente_desde,
            resumenes=texto.resumenes,
            resumen_cambios=texto.resumen_cambios,
            programada=texto.programada,
        )


class TextoLegal(TextoResumen):
    contenido: str
    contenido_html: str
    publicado_en: datetime

    @classmethod
    def desde_dominio(cls, texto: dominio.TextoLegal) -> TextoLegal:
        base = TextoResumen.desde_dominio(texto)
        return cls(
            **base.model_dump(),
            contenido=texto.contenido,
            contenido_html=markdown_a_html(texto.contenido),
            publicado_en=texto.publicado_en,
        )


class TextoAceptado(BaseModel):
    tipo: Tipo
    version: Annotated[str, StringConstraints(max_length=29)]


class NuevaAceptacion(BaseModel):
    contexto: Literal["registro"]
    textos: Annotated[list[TextoAceptado], Field(min_length=1, max_length=3)]


class Aceptacion(BaseModel):
    id: UUID
    tipo: str
    version: str
    contexto: str
    id_operacion: UUID | None
    aceptada_en: datetime
    retirada_en: datetime | None
    aceptante: dict[str, str] | None

    @classmethod
    def desde_dominio(cls, aceptacion: dominio.Aceptacion) -> Aceptacion:
        return cls(**aceptacion.__dict__)
