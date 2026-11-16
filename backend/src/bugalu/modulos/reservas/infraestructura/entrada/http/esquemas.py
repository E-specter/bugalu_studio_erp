from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from bugalu.compartido.esquemas import TextoCorto, TextoLargo
from bugalu.modulos.catalogo.infraestructura.entrada.http.esquemas import Simulacion
from bugalu.modulos.reservas.aplicacion.consultar_disponibilidad.caso_de_uso import (
    Disponibilidad as DisponibilidadDominio,
)
from bugalu.modulos.reservas.dominio import modelos
from bugalu.modulos.reservas.dominio.disponibilidad import LIMA


def _acotado(valor: datetime) -> datetime:
    # Evita desbordes al pasar a hora de Lima: solo anios razonables.
    if not 2000 <= valor.year <= 2100:
        raise ValueError("Fecha fuera de rango.")
    return valor


Instante = Annotated[AwareDatetime, AfterValidator(_acotado)]
Entero = Annotated[StrictInt, Field(ge=1, le=100000)]


class Sala(BaseModel):
    id: UUID
    nombre: str
    sede: str

    @classmethod
    def desde_dominio(cls, s: modelos.Sala) -> Sala:
        return cls(id=s.id, nombre=s.nombre, sede=s.sede)


class Franja(BaseModel):
    id: UUID
    id_sala: UUID
    inicio: datetime
    fin: datetime


class Cierre(Franja):
    motivo: str


class FranjaDisp(BaseModel):
    id: UUID
    inicio: datetime
    fin: datetime


class CierreDisp(FranjaDisp):
    motivo: str


class Detalle(BaseModel):
    id_reserva: UUID
    cliente: str | None
    servicio: str
    estado: str


class Ocupado(BaseModel):
    inicio: datetime
    fin: datetime
    propia: bool
    detalle: Detalle | None = None


class Limites(BaseModel):
    desde: datetime
    hasta: datetime


class Dia(BaseModel):
    fecha: date
    minutos_libres: int


class Disponibilidad(BaseModel):
    limites: Limites
    franjas: list[FranjaDisp]
    ocupados: list[Ocupado]
    cierres: list[CierreDisp]
    dias: list[Dia]

    @classmethod
    def desde_dominio(cls, d: DisponibilidadDominio) -> Disponibilidad:
        return cls(
            limites=Limites(desde=d.limites.desde, hasta=d.limites.hasta),
            franjas=[FranjaDisp(id=f.id, inicio=f.inicio, fin=f.fin) for f in d.franjas],
            ocupados=[
                Ocupado(
                    inicio=o.inicio,
                    fin=o.fin,
                    propia=o.propia,
                    detalle=Detalle(
                        id_reserva=o.reserva.id,
                        cliente=o.cliente,
                        servicio=o.reserva.servicio,
                        estado=o.reserva.estado,
                    )
                    if o.reserva
                    else None,
                )
                for o in d.ocupados
            ],
            cierres=[
                CierreDisp(id=c.id, inicio=c.inicio, fin=c.fin, motivo=c.motivo) for c in d.cierres
            ],
            dias=[Dia(fecha=f, minutos_libres=m) for f, m in d.dias.items()],
        )


class Tramo(BaseModel):
    inicio: datetime
    fin: datetime


class TramoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inicio: Instante
    fin: Instante

    @model_validator(mode="after")
    def _en_media_hora(self) -> TramoEntrada:
        if self.fin <= self.inicio:
            raise ValueError("El fin debe ser posterior al inicio.")
        for v in (self.inicio, self.fin):
            if v.microsecond or v.timestamp() % 1800:
                raise ValueError("Los instantes van en multiplos de 30 minutos.")
        return self


class NuevasFranjas(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_sala: UUID
    franjas: Annotated[list[TramoEntrada], Field(min_length=1, max_length=200)]


class NuevoCierre(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_sala: UUID
    inicio: Instante
    fin: Instante
    motivo: TextoCorto

    @model_validator(mode="after")
    def _fin_posterior(self) -> NuevoCierre:
        if self.fin <= self.inicio:
            raise ValueError("El fin debe ser posterior al inicio.")
        return self


class Parametros(BaseModel):
    dias_limite_pago: int
    horas_limite_pago: int
    anticipacion_minima_horas: int
    anticipacion_maxima_semanas: int


class CambiosParametros(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dias_limite_pago: Entero | None = None
    horas_limite_pago: Entero | None = None
    anticipacion_minima_horas: Entero | None = None
    anticipacion_maxima_semanas: Entero | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _sin_nulos(cls, valor: object) -> object:
        if valor is None:
            raise ValueError("El campo no admite nulo.")
        return valor


class NuevaReserva(BaseModel):
    """El cliente nunca envia precios, estado ni cuotas: `extra` prohibido."""

    model_config = ConfigDict(extra="forbid")
    id_sala: UUID
    id_servicio: UUID
    inicio: Instante
    fin: Instante
    especialistas: Annotated[list[UUID], Field(max_length=20)] = []
    detalle: TextoLargo | None = None


class Referencia(BaseModel):
    id: UUID
    nombre: str | None


class ServicioReserva(BaseModel):
    id: UUID
    nombre: str
    categoria: str


class Cuota(BaseModel):
    id: UUID
    hito: str
    monto: Decimal
    estado: str


class Reserva(BaseModel):
    id: UUID
    folio: str
    estado: str
    motivo_cancelacion: str | None
    inicio: datetime
    fin: datetime
    fin_buffer: datetime
    sala: Referencia
    servicio: ServicioReserva
    especialistas: list[Referencia]
    precio: Simulacion
    cuotas: list[Cuota]
    vence_pago: datetime | None
    cliente: Referencia | None = None

    @classmethod
    def desde_dominio(cls, r: modelos.Reserva) -> Reserva:
        def lima(instante: datetime | None) -> datetime | None:
            return instante.astimezone(LIMA) if instante else None

        return cls(
            id=r.id,
            folio=r.folio,
            estado=r.estado,
            motivo_cancelacion=r.motivo_cancelacion,
            inicio=r.inicio.astimezone(LIMA),
            fin=r.fin.astimezone(LIMA),
            fin_buffer=r.fin_buffer.astimezone(LIMA),
            sala=Referencia(id=r.sala.id, nombre=r.sala.nombre),
            servicio=ServicioReserva(**vars(r.servicio)),
            especialistas=[Referencia(id=e.id, nombre=e.nombre) for e in r.especialistas],
            precio=Simulacion.model_validate(r.precio),
            cuotas=[Cuota(**vars(c)) for c in r.cuotas],
            vence_pago=lima(r.vence_pago),
            **(
                {"cliente": Referencia(id=r.cliente.id, nombre=r.cliente.nombre)}
                if r.cliente
                else {}
            ),
        )
