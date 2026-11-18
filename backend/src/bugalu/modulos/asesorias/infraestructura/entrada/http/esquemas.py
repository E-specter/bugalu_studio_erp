from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bugalu.compartido.esquemas import TextoCorto, TextoLargo
from bugalu.modulos.asesorias.aplicacion.disponibilidad.caso_de_uso import (
    Disponibilidad as DisponibilidadDominio,
)
from bugalu.modulos.asesorias.dominio import modelos
from bugalu.modulos.asesorias.infraestructura.salida.almacen_storage import url_publica
from bugalu.modulos.catalogo.infraestructura.entrada.http.esquemas import Impuesto
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import Instante

# Formato de las redes de RF-17 (identidad no se importa: los modulos no dependen entre si).
RedSocial = Literal["instagram", "tiktok", "facebook", "youtube", "spotify", "otra"]
PrecioAsesoria = Annotated[
    Decimal, Field(gt=0, max_digits=10, decimal_places=2, allow_inf_nan=False)
]


# --- respuestas ---------------------------------------------------------------------------------


class Especialidad(BaseModel):
    id: UUID
    nombre: str
    activa: bool

    @classmethod
    def desde_dominio(cls, e: modelos.Especialidad) -> Especialidad:
        return cls(id=e.id, nombre=e.nombre, activa=e.activa)


class EspecialidadResumen(BaseModel):
    id: UUID
    nombre: str


class Duracion(BaseModel):
    minutos: int
    precio: Decimal
    igv: Impuesto

    @classmethod
    def desde_dominio(cls, d: modelos.Duracion) -> Duracion:
        return cls(minutos=d.minutos, precio=d.precio, igv=Impuesto(**vars(d.igv)))


class Red(BaseModel):
    red: RedSocial
    valor: str


class ProfesionalResumen(BaseModel):
    id: UUID
    nombre: str | None
    nombre_artistico: str | None
    especialidades: list[EspecialidadResumen]
    foto_url: str | None
    duraciones: list[Duracion]
    activo: bool | None = None  # solo para el propio y el administrador
    publicado: bool | None = None


class Profesional(ProfesionalResumen):
    presentacion: str | None
    redes: list[Red]


def _campos(
    p: modelos.Profesional, duraciones: list[modelos.Duracion], url_supabase: str, ve_estado: bool
) -> dict[str, object]:
    return {
        "id": p.id,
        "nombre": p.nombre,
        "nombre_artistico": p.nombre_artistico,
        "especialidades": [EspecialidadResumen(id=e.id, nombre=e.nombre) for e in p.especialidades],
        "foto_url": url_publica(url_supabase, p.foto_ruta) if p.foto_ruta else None,
        "duraciones": [Duracion.desde_dominio(d) for d in duraciones],
        "activo": p.activo if ve_estado else None,
        "publicado": p.publicado if ve_estado else None,
    }


def resumen_de(
    p: modelos.Profesional, duraciones: list[modelos.Duracion], url_supabase: str, ve_estado: bool
) -> ProfesionalResumen:
    return ProfesionalResumen(**_campos(p, duraciones, url_supabase, ve_estado))


def profesional_de(
    p: modelos.Profesional, duraciones: list[modelos.Duracion], url_supabase: str, ve_estado: bool
) -> Profesional:
    return Profesional(
        **_campos(p, duraciones, url_supabase, ve_estado),
        presentacion=p.presentacion,
        redes=[Red(**r) for r in p.redes],
    )


class Horario(BaseModel):
    id: UUID
    inicio: datetime
    fin: datetime

    @classmethod
    def desde_dominio(cls, h: modelos.Horario) -> Horario:
        return cls(id=h.id, inicio=h.inicio, fin=h.fin)


class Tramo(BaseModel):
    inicio: datetime
    fin: datetime


class Ocupado(Tramo):
    propia: bool = False


class Limites(BaseModel):
    desde: datetime
    hasta: datetime


class DiaLibre(BaseModel):
    fecha: date
    minutos_libres: int


class DisponibilidadProfesional(BaseModel):
    limites: Limites
    horarios: list[Horario]
    ocupados: list[Ocupado]
    dias: list[DiaLibre]
    duraciones: list[Duracion]

    @classmethod
    def desde_dominio(cls, d: DisponibilidadDominio) -> DisponibilidadProfesional:
        return cls(
            limites=Limites(desde=d.limites.desde, hasta=d.limites.hasta),
            horarios=[Horario.desde_dominio(h) for h in d.horarios],
            ocupados=[Ocupado(inicio=o.inicio, fin=o.fin) for o in d.ocupados],
            dias=[DiaLibre(fecha=x.fecha, minutos_libres=x.minutos) for x in d.dias],
            duraciones=[Duracion.desde_dominio(x) for x in d.duraciones],
        )


# --- cuerpos de entrada -------------------------------------------------------------------------


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NuevaEspecialidad(_Cuerpo):
    nombre: Annotated[TextoCorto, Field(min_length=2, max_length=60)]


class CambiosEspecialidad(_Cuerpo):
    nombre: Annotated[TextoCorto, Field(min_length=2, max_length=60)] | None = None
    activa: bool | None = None

    @model_validator(mode="after")
    def _sin_nulos(self) -> CambiosEspecialidad:
        if {"nombre", "activa"} & self.model_fields_set and (
            (self.nombre is None and "nombre" in self.model_fields_set)
            or (self.activa is None and "activa" in self.model_fields_set)
        ):
            raise ValueError("Los campos no admiten null.")
        return self


class NuevoPerfil(_Cuerpo):
    id_usuario: UUID


class PreciosEntrada(_Cuerpo):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    p30: PrecioAsesoria | None = Field(default=None, alias="30")
    p60: PrecioAsesoria | None = Field(default=None, alias="60")


class CambiosProfesional(_Cuerpo):
    nombre_artistico: Annotated[TextoCorto, Field(max_length=80)] | None = None
    presentacion: Annotated[TextoLargo, Field(max_length=600)] | None = None
    redes: Annotated[list[Red], Field(max_length=5)] | None = None
    especialidades: Annotated[list[UUID], Field(min_length=1, max_length=5)] | None = None
    activo: bool | None = None
    precios: PreciosEntrada | None = None

    @model_validator(mode="after")
    def _sin_nulos(self) -> CambiosProfesional:
        for campo in ("redes", "especialidades", "activo", "precios"):  # no admiten null
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} no admite null.")
        return self


class TramoEntrada(_Cuerpo):
    inicio: Instante
    fin: Instante


class NuevosHorarios(_Cuerpo):
    horarios: Annotated[list[TramoEntrada], Field(min_length=1, max_length=200)]
