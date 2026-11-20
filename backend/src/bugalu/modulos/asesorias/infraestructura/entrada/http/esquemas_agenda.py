from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from bugalu.modulos.asesorias.dominio import agenda
from bugalu.modulos.asesorias.dominio.asesoria import Asesoria as AsesoriaDominio
from bugalu.modulos.asesorias.dominio.asesoria import (
    AvisoDeCancelacion as AvisoDeCancelacionDominio,
)
from bugalu.modulos.asesorias.dominio.asesoria import (
    CambioDeHorario as CambioDeHorarioDominio,
)
from bugalu.modulos.asesorias.dominio.asesoria import Constancia as ConstanciaDominio
from bugalu.modulos.asesorias.dominio.asesoria import PersonaAsesoria
from bugalu.modulos.catalogo.infraestructura.entrada.http.esquemas import Impuesto
from bugalu.modulos.reservas.dominio.disponibilidad import LIMA
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import (
    CancelacionReserva,
    Cuota,
    Devolucion,
    Instante,
    Politica,
    ReprogramacionReserva,
    cancelacion_a_esquema,
    referencia_a_esquema,
)


class NuevaAsesoria(BaseModel):
    """El cliente nunca envia precio, estado ni cuotas: `extra` prohibido."""

    model_config = ConfigDict(extra="forbid")
    id_profesional: UUID
    inicio: Instante
    duracion: Literal[30, 60]
    modalidad: Literal["presencial", "virtual"]
    version_condiciones: Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]


class CambiosEncuentro(BaseModel):
    """Solo lo enviado cambia; `lugar` y `enlace` en `null` o vacios = "por confirmar"."""

    model_config = ConfigDict(extra="forbid")
    modalidad: Literal["presencial", "virtual"] | None = None
    lugar: Annotated[str, StringConstraints(max_length=1000)] | None = None
    enlace: Annotated[str, StringConstraints(max_length=1000)] | None = None

    @model_validator(mode="after")
    def _modalidad_no_nula(self) -> CambiosEncuentro:
        if "modalidad" in self.model_fields_set and self.modalidad is None:
            raise ValueError("La modalidad no admite nulo.")
        return self

    def cambios(self) -> dict[str, Any]:
        return {c: getattr(self, c) for c in self.model_fields_set}


class Persona(BaseModel):
    id: UUID
    nombre: str | None
    nombre_artistico: str | None


class Cliente(Persona):
    telefono: str | None
    correo: str | None


class NotasAsesoria(BaseModel):
    """`texto` vacio borra las notas; hasta 5000 caracteres (CA-13)."""

    model_config = ConfigDict(extra="forbid")
    texto: Annotated[str, StringConstraints(max_length=5000)]


class PersonaConstancia(BaseModel):
    nombre: str | None
    nombre_artistico: str | None = None


class ProfesionalConstancia(PersonaConstancia):
    especialidades: list[str]


class Constancia(BaseModel):
    folio: str
    cliente: PersonaConstancia
    profesional: ProfesionalConstancia
    inicio: datetime
    fin: datetime
    duracion: int
    modalidad: str
    emitida_en: datetime

    @classmethod
    def desde_dominio(cls, c: ConstanciaDominio) -> Constancia:
        return cls(
            folio=c.folio,
            cliente=PersonaConstancia(**c.cliente),
            profesional=ProfesionalConstancia(**c.profesional),
            inicio=c.inicio.astimezone(LIMA),
            fin=c.fin.astimezone(LIMA),
            duracion=c.duracion,
            modalidad=c.modalidad,
            emitida_en=c.emitida_en.astimezone(LIMA),
        )


class PrecioAsesoria(BaseModel):
    total: Decimal
    impuesto: Impuesto


class AvisoDeCancelacion(BaseModel):
    aviso_en: datetime
    por: str


class CambioDeHorario(BaseModel):
    anterior_inicio: datetime
    nuevo_inicio: datetime
    en: datetime


class Asesoria(BaseModel):
    id: UUID
    tipo: Literal["asesoria"] = "asesoria"
    folio: str
    estado: str
    motivo_cancelacion: str | None
    inicio: datetime
    fin: datetime
    duracion: int
    precio: PrecioAsesoria
    vence_pago: datetime | None
    profesional: Persona
    modalidad: str
    lugar: str | None
    enlace: str | None
    realizada_en: datetime | None
    constancia_disponible: bool
    cuotas: list[Cuota] | None = None
    pagado: Decimal | None = None
    politica: Politica | None = None
    version_condiciones: str | None = None
    cliente: Cliente | None = None
    notas: str | None = None
    reprogramaciones: list[ReprogramacionReserva | CambioDeHorario] = []
    cancelacion: CancelacionReserva | AvisoDeCancelacion | None = None
    eleccion_estudio: str | None = None
    devolucion: Devolucion | None = None

    @classmethod
    def desde_dominio(cls, a: AsesoriaDominio) -> Asesoria:
        def lima(i: datetime | None) -> datetime | None:
            return i.astimezone(LIMA) if i else None

        cuotas = None
        if a.cuotas is not None:
            cuotas = [
                Cuota(
                    **{
                        **vars(c),
                        "pagos": [
                            {**vars(p), "registrado_en": p.registrado_en.astimezone(LIMA)}
                            for p in c.pagos
                        ],
                    }
                )
                for c in a.cuotas
            ]
        return cls(
            id=a.id,
            folio=a.folio,
            estado=a.estado,
            motivo_cancelacion=a.motivo_cancelacion,
            inicio=a.inicio.astimezone(LIMA),
            fin=a.fin.astimezone(LIMA),
            duracion=a.duracion,
            precio=PrecioAsesoria.model_validate(a.precio),
            vence_pago=lima(a.vence_pago),
            profesional=Persona(**_persona(a.profesional)),
            modalidad=a.modalidad,
            lugar=a.lugar,
            enlace=a.enlace,
            realizada_en=lima(a.realizada_en),
            constancia_disponible=a.constancia_disponible,
            cuotas=cuotas,
            pagado=a.pagado,
            politica=Politica(**vars(a.politica)) if a.politica else None,
            version_condiciones=a.version_condiciones,
            cliente=Cliente(
                **_persona(a.cliente), telefono=a.cliente.telefono, correo=a.cliente.correo
            )
            if a.cliente
            else None,
            notas=a.notas,
            reprogramaciones=[_reprogramacion(g, lima) for g in a.reprogramaciones],
            cancelacion=_cancelacion(a.cancelacion),
            eleccion_estudio=a.eleccion_estudio,
            devolucion=Devolucion.desde_dominio(a.devolucion) if a.devolucion else None,
        )


def _reprogramacion(g: Any, lima: Any) -> ReprogramacionReserva | CambioDeHorario:
    fechas = {c: lima(getattr(g, c)) for c in ("anterior_inicio", "nuevo_inicio", "en")}
    if isinstance(g, CambioDeHorarioDominio):
        return CambioDeHorario(**fechas)
    return ReprogramacionReserva(**{**vars(g), **fechas, "por": referencia_a_esquema(g.por)})


def _cancelacion(c: Any) -> CancelacionReserva | AvisoDeCancelacion | None:
    if isinstance(c, AvisoDeCancelacionDominio):
        return AvisoDeCancelacion(aviso_en=c.aviso_en.astimezone(LIMA), por=c.por)
    return cancelacion_a_esquema(c) if c else None


def _persona(p: PersonaAsesoria) -> dict[str, Any]:
    return {"id": p.id, "nombre": p.nombre, "nombre_artistico": p.nombre_artistico}


class AsesoriaResumen(BaseModel):
    id: UUID
    folio: str
    estado: str
    inicio: datetime
    fin: datetime
    modalidad: str
    vence_pago: datetime | None
    profesional: Persona
    cliente: Cliente | None = None
    por_cerrar: bool
    encuentro_pendiente: bool

    @classmethod
    def desde_dominio(cls, a: AsesoriaDominio, ahora: datetime) -> AsesoriaResumen:
        completa = Asesoria.desde_dominio(a)
        return cls(
            id=a.id,
            folio=a.folio,
            estado=a.estado,
            inicio=completa.inicio,
            fin=completa.fin,
            modalidad=a.modalidad,
            vence_pago=completa.vence_pago,
            profesional=completa.profesional,
            cliente=completa.cliente,
            por_cerrar=agenda.por_cerrar(a.estado, a.fin, ahora),
            encuentro_pendiente=agenda.encuentro_pendiente(a.modalidad, a.lugar, a.enlace),
        )


class VistaReprogramacionAsesoria(BaseModel):
    nivel: int | None
    penalizacion: Decimal
    precio: PrecioAsesoria
    saldo: Decimal
    credito: Decimal
    reprogramaciones_restantes: int
