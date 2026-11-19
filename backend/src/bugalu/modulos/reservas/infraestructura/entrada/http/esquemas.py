from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
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


class Itse(BaseModel):
    certificado: str
    vence: date


class Sala(BaseModel):
    id: UUID
    nombre: str
    sede: str
    aforo: int | None
    itse: Itse | None

    @classmethod
    def desde_dominio(cls, s: modelos.Sala) -> Sala:
        itse = Itse(certificado=s.itse.certificado, vence=s.itse.vence) if s.itse else None
        return cls(id=s.id, nombre=s.nombre, sede=s.sede, aforo=s.aforo, itse=itse)


def _fecha_iso(valor: object) -> object:
    # Solo AAAA-MM-DD: ni fechas con hora ni marcas de tiempo numericas.
    if not isinstance(valor, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        raise ValueError("Se espera AAAA-MM-DD.")
    return valor


class CambiosSala(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aforo: Annotated[int, Field(strict=True, ge=1, le=200)]
    itse_certificado: Annotated[TextoCorto, Field(max_length=40)]
    itse_vence: Annotated[date, BeforeValidator(_fecha_iso)]


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
    pago_por_validar: bool


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
                        pago_por_validar=o.reserva.pago_por_validar,
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


class Cancelacion(BaseModel):
    """Cuerpo de cancelar (RF-18). El cliente da `nivel_esperado`; `por` y `aviso_en` son del
    administrador. La nota es obligatoria segun el caso (lo decide la base)."""

    model_config = ConfigDict(extra="forbid")
    nivel_esperado: Annotated[int, Field(ge=1, le=3)] | None = None
    nota: Annotated[TextoLargo, Field(max_length=300)] | None = None
    por: Literal["cliente", "estudio"] | None = None
    aviso_en: Instante | None = None

    @field_validator("nota", mode="before")
    @classmethod
    def _sin_nulo(cls, valor: object) -> object:
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
    version_condiciones: Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]


class Referencia(BaseModel):
    id: UUID
    nombre: str | None


class ServicioReserva(BaseModel):
    id: UUID
    nombre: str
    categoria: str


class PagoDeCuota(BaseModel):
    id: UUID
    estado: str
    metodo: str
    monto: Decimal
    numero_operacion: str
    motivo_rechazo: str | None
    registrado_en: datetime


class Cuota(BaseModel):
    id: UUID
    hito: str
    monto: Decimal
    estado: str
    pagable: bool
    pagos: list[PagoDeCuota]
    pagado: Decimal


class Excepcion(BaseModel):
    motivo: str
    por: Referencia | None
    en: datetime


class CancelacionReserva(BaseModel):
    nivel: int | None
    aviso_en: datetime
    por: str
    pagado: Decimal
    retenido: Decimal
    credito: Decimal
    nota: str | None
    registrada_por: Referencia | None
    excepcion: Excepcion | None = None


class ReprogramacionReserva(BaseModel):
    anterior_inicio: datetime
    nuevo_inicio: datetime
    nivel: int | None
    penalizacion: Decimal
    total_anterior: Decimal
    total_nuevo: Decimal
    por: Referencia | None
    en: datetime


class Politica(BaseModel):
    horas_nivel_1: int
    horas_nivel_2: int
    porcentaje_penalizacion_nivel_2: int
    minutos_tolerancia_inasistencia: int
    dias_vigencia_credito: int
    reprogramaciones_nivel_1: int
    reprogramaciones_nivel_2: int


class ReservaDeDevolucion(BaseModel):
    id: UUID
    folio: str
    tipo: Literal["sala", "asesoria"]


class Devolucion(BaseModel):
    id: UUID
    id_credito: UUID | None
    id_reserva: UUID
    folio: str
    cliente: Referencia
    tipo: str
    motivo: str
    monto_solicitado: Decimal
    solicitada_en: datetime
    estado: str
    monto_aprobado: Decimal | None = None
    motivo_decision: str | None = None
    decidida_en: datetime | None = None
    nota_realizada: str | None = None
    realizada_en: datetime | None = None
    limite: datetime | None = None
    reserva: ReservaDeDevolucion | None = None

    @classmethod
    def desde_dominio(cls, d: modelos.Devolucion) -> Devolucion:
        def lima(i: datetime | None) -> datetime | None:
            return i.astimezone(LIMA) if i else None

        return cls(
            **{
                **vars(d),
                "cliente": Referencia(id=d.cliente.id, nombre=d.cliente.nombre),
                "solicitada_en": d.solicitada_en.astimezone(LIMA),
                "decidida_en": lima(d.decidida_en),
                "realizada_en": lima(d.realizada_en),
                "limite": lima(d.limite),
                "reserva": ReservaDeDevolucion(id=d.id_reserva, folio=d.folio, tipo=d.tipo_reserva),
            }
        )


class VistaCancelacion(BaseModel):
    nivel: int | None
    anticipacion_horas: float
    pagado: Decimal
    en_validacion: Decimal
    retenido: Decimal
    credito: Decimal
    credito_vence: datetime | None
    puede_reprogramar: bool
    reprogramaciones_restantes: int

    @classmethod
    def desde_dominio(cls, v: modelos.VistaCancelacion) -> VistaCancelacion:
        return cls(
            **{
                **vars(v),
                "credito_vence": v.credito_vence.astimezone(LIMA) if v.credito_vence else None,
            }
        )


class NuevaExcepcion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: Annotated[TextoLargo, Field(min_length=10)]


class NuevoHorario(BaseModel):
    """Vista previa de reprogramar: solo el inicio (sala, servicio y duracion se conservan)."""

    model_config = ConfigDict(extra="forbid")
    inicio: Instante


class Reprogramacion(NuevoHorario):
    """Confirma lo que el cliente vio: sin `nivel_esperado` o `total_esperado` que coincidan, 409.
    Tras una cancelacion del estudio no hay nivel (`null`) ni se recalcula el precio."""

    nivel_esperado: Annotated[int, Field(ge=1, le=3)] | None = None
    total_esperado: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)] | None = None


class EleccionEstudio(BaseModel):
    """La reprogramacion sin costo usa `POST /reprogramar`; aqui solo la devolucion integra."""

    model_config = ConfigDict(extra="forbid")
    opcion: Literal["devolucion"]


class VistaReprogramacion(BaseModel):
    nivel: int | None
    penalizacion: Decimal
    precio: Simulacion
    saldo: Decimal
    credito: Decimal
    reprogramaciones_restantes: int

    @classmethod
    def desde_dominio(cls, v: modelos.VistaReprogramacion) -> VistaReprogramacion:
        return cls(**{**vars(v), "precio": Simulacion.model_validate(v.precio)})


def _referencia(r: modelos.Referencia | None) -> Referencia | None:
    return Referencia(id=r.id, nombre=r.nombre) if r else None


def _cancelacion(c: modelos.CancelacionReserva) -> CancelacionReserva:
    campos = {
        **vars(c),
        "aviso_en": c.aviso_en.astimezone(LIMA),
        "registrada_por": _referencia(c.registrada_por),
    }
    if c.excepcion:  # opcional: solo se emite si se aplico
        campos["excepcion"] = Excepcion(
            motivo=c.excepcion.motivo,
            por=_referencia(c.excepcion.por),
            en=c.excepcion.en.astimezone(LIMA),
        )
    else:
        del campos["excepcion"]
    return CancelacionReserva(**campos)


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
    pago_por_validar: bool
    vence_pago: datetime | None
    cliente: Referencia | None = None
    nota_cancelacion: str | None = None
    version_condiciones: str | None = None
    pagado: Decimal
    politica: Politica | None
    reprogramaciones: list[ReprogramacionReserva]
    cancelacion: CancelacionReserva | None = None
    eleccion_estudio: str | None = None
    devolucion: Devolucion | None = None

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
            cuotas=[
                Cuota(
                    **{
                        **vars(c),
                        "pagos": [
                            PagoDeCuota(
                                **{**vars(p), "registrado_en": p.registrado_en.astimezone(LIMA)}
                            )
                            for p in c.pagos
                        ],
                    }
                )
                for c in r.cuotas
            ],
            pago_por_validar=r.pago_por_validar,
            nota_cancelacion=r.nota_cancelacion,
            version_condiciones=r.version_condiciones,
            vence_pago=lima(r.vence_pago),
            pagado=r.pagado,
            politica=Politica(**vars(r.politica)) if r.politica else None,
            reprogramaciones=[
                ReprogramacionReserva(
                    **{
                        **vars(g),
                        "anterior_inicio": g.anterior_inicio.astimezone(LIMA),
                        "nuevo_inicio": g.nuevo_inicio.astimezone(LIMA),
                        "en": g.en.astimezone(LIMA),
                        "por": _referencia(g.por),
                    }
                )
                for g in r.reprogramaciones
            ],
            **(
                {"cliente": Referencia(id=r.cliente.id, nombre=r.cliente.nombre)}
                if r.cliente
                else {}
            ),
            **({"cancelacion": _cancelacion(r.cancelacion)} if r.cancelacion else {}),
            **({"eleccion_estudio": r.eleccion_estudio} if r.eleccion_estudio else {}),
            **({"devolucion": Devolucion.desde_dominio(r.devolucion)} if r.devolucion else {}),
        )


# Para la politica de las asesorias (modulo asesorias), que reutiliza estas conversiones.
cancelacion_a_esquema = _cancelacion
referencia_a_esquema = _referencia
