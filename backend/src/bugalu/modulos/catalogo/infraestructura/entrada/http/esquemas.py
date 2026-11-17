from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from bugalu.compartido.esquemas import TextoCorto
from bugalu.modulos.catalogo.dominio import cambios_sensibles as sensibles
from bugalu.modulos.catalogo.dominio import precio
from bugalu.modulos.catalogo.dominio.precio import Unidad

# Decimales con la forma de numeric(10, 2) y numeric(5, 2): el 422 sale aqui, no de la base.
Monto = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2, allow_inf_nan=False)]
Porcentaje = Annotated[
    Decimal, Field(ge=0, le=300, max_digits=5, decimal_places=2, allow_inf_nan=False)
]
Hora = Annotated[str, StringConstraints(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
Fecha = Annotated[date, Field(ge=date(2000, 1, 1), le=date(2100, 12, 31))]


def _hora(valor: str) -> time:
    return time.fromisoformat(valor)


# --- respuestas ---------------------------------------------------------------------------------


class Servicio(BaseModel):
    id: UUID
    nombre: str
    categoria: str
    ocupa_sala: bool
    tarifa_hora: Decimal
    monto_fijo: Decimal
    especialistas_por_defecto: list[UUID]
    activo: bool

    @classmethod
    def desde_dominio(cls, s: precio.Servicio) -> Servicio:
        return cls(**{**vars(s), "especialistas_por_defecto": list(s.especialistas_por_defecto)})


class Especialista(BaseModel):
    id: UUID
    nombre: str
    monto_fijo: Decimal
    monto_variable: Decimal
    unidad: Unidad
    activo: bool

    @classmethod
    def desde_dominio(cls, e: precio.Especialista) -> Especialista:
        return cls(**vars(e))


class Feriado(BaseModel):
    fecha: date
    nombre: str


class Linea(BaseModel):
    concepto: str
    cantidad: Decimal
    unidad: str
    monto: Decimal


class LineaRecargo(BaseModel):
    tipo: str
    bloques: int
    monto: Decimal


class Impuestos(BaseModel):
    porcentaje_igv: Decimal
    precios_incluyen_igv: bool

    @classmethod
    def desde_dominio(cls, c: precio.ConfiguracionImpuestos) -> Impuestos:
        return cls(porcentaje_igv=c.porcentaje, precios_incluyen_igv=c.incluido)


class Impuesto(BaseModel):
    nombre: str = "IGV"
    porcentaje: Decimal
    incluido: bool
    base: Decimal
    monto: Decimal


class Simulacion(BaseModel):
    lineas: list[Linea]
    recargos: list[LineaRecargo]
    total: Decimal
    anticipo: Decimal
    impuesto: Impuesto
    porcentaje_adelanto: Decimal

    @classmethod
    def desde_dominio(cls, s: precio.Simulacion) -> Simulacion:
        return cls(
            lineas=[Linea(**vars(x)) for x in s.lineas],
            recargos=[LineaRecargo(**vars(x)) for x in s.recargos],
            total=s.total,
            anticipo=s.anticipo,
            impuesto=Impuesto(**vars(s.impuesto)),
            porcentaje_adelanto=s.porcentaje_adelanto,
        )


class _PorcentajeSolo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    porcentaje: Porcentaje


class _Noche(_PorcentajeSolo):
    desde: Hora
    hasta: Hora

    @model_validator(mode="after")
    def _ventana_con_duracion(self) -> _Noche:
        if self.desde == self.hasta:
            raise ValueError("La noche no puede empezar y terminar a la misma hora.")
        return self


class Recargos(BaseModel):
    """Cuerpo de PUT y respuesta de GET."""

    model_config = ConfigDict(extra="forbid")
    noche: _Noche
    fin_de_semana: _PorcentajeSolo
    feriado: _PorcentajeSolo

    @classmethod
    def desde_dominio(cls, r: precio.Recargos) -> Recargos:
        return cls(
            noche=_Noche(
                porcentaje=r.noche,
                desde=r.desde_noche.strftime("%H:%M"),
                hasta=r.hasta_noche.strftime("%H:%M"),
            ),
            fin_de_semana=_PorcentajeSolo(porcentaje=r.fin_de_semana),
            feriado=_PorcentajeSolo(porcentaje=r.feriado),
        )

    def a_dominio(self) -> precio.Recargos:
        return precio.Recargos(
            noche=self.noche.porcentaje,
            desde_noche=_hora(self.noche.desde),
            hasta_noche=_hora(self.noche.hasta),
            fin_de_semana=self.fin_de_semana.porcentaje,
            feriado=self.feriado.porcentaje,
        )


# --- cuerpos de entrada -------------------------------------------------------------------------


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")  # un campo de mas (nombre, categoria...) es 422

    @field_validator("*", mode="before")
    @classmethod
    def _sin_nulos(cls, valor: Any) -> Any:
        if valor is None:
            raise ValueError("El campo no admite nulo.")
        return valor


class CambiosServicio(_Cuerpo):
    tarifa_hora: Monto | None = None
    monto_fijo: Monto | None = None
    activo: bool | None = None
    especialistas_por_defecto: Annotated[list[UUID], Field(max_length=20)] | None = None


class CambiosEspecialista(_Cuerpo):
    monto_fijo: Monto | None = None
    monto_variable: Monto | None = None
    unidad: Unidad | None = None
    activo: bool | None = None


class NuevoFeriado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fecha: Fecha
    nombre: TextoCorto


class NuevaSimulacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_sala: UUID
    id_servicio: UUID
    inicio: AwareDatetime
    fin: AwareDatetime
    especialistas: Annotated[list[UUID], Field(max_length=20)] = []


# --- RF-20: cambios sensibles -------------------------------------------------------------------

Recurso = Literal["impuestos", "servicio", "especialista", "recargos", "parametros"]
PorcentajeIgv = Annotated[
    Decimal, Field(ge=0, le=Decimal("99.99"), max_digits=4, decimal_places=2, allow_inf_nan=False)
]


class CambiosImpuestos(_Cuerpo):
    porcentaje_igv: PorcentajeIgv | None = None
    precios_incluyen_igv: bool | None = None


class SensiblesServicio(_Cuerpo):
    tarifa_hora: Monto | None = None
    monto_fijo: Monto | None = None


class SensiblesEspecialista(_Cuerpo):
    monto_fijo: Monto | None = None
    monto_variable: Monto | None = None
    unidad: Unidad | None = None


class NuevaPrevisualizacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recurso: Recurso
    id_recurso: UUID | None = None
    cambios: dict[str, Any]


class NuevaConfirmacion(BaseModel):
    """Sin limite de largo: una palabra o un token disparatados dan 422 palabra_incorrecta o 409."""

    model_config = ConfigDict(extra="forbid")
    token: str
    palabra: str


class CambioPrevio(BaseModel):
    campo: str
    anterior: str
    nuevo: str


class EjemploImpacto(BaseModel):
    concepto: str
    antes: str
    despues: str
    tipo: Literal["importe", "fecha_hora", "texto"]


class Impacto(BaseModel):
    ejemplos: list[EjemploImpacto]
    operaciones_vigentes: int


class Previsualizacion(BaseModel):
    token: str
    expira_en: datetime
    palabra: str = sensibles.PALABRA
    recurso: Recurso
    id_recurso: UUID | None
    nombre_recurso: str
    cambios: list[CambioPrevio]
    impacto: Impacto


class Autor(BaseModel):
    id: UUID
    nombre: str


class CambioRegistrado(BaseModel):
    id: UUID
    cambiado_en: datetime
    autor: Autor
    recurso: Recurso
    id_recurso: UUID | None
    nombre_recurso: str
    campo: str
    anterior: str
    nuevo: str

    @classmethod
    def desde_dominio(cls, c: sensibles.CambioRegistrado) -> CambioRegistrado:
        return cls(
            id=c.id,
            cambiado_en=c.cambiado_en,
            autor=Autor(id=c.id_autor, nombre=c.autor_nombre),
            recurso=c.recurso,
            id_recurso=c.id_recurso,
            nombre_recurso=c.nombre_recurso,
            campo=c.campo,
            anterior=c.anterior,
            nuevo=c.nuevo,
        )


class CambioConfirmado(BaseModel):
    recurso: Recurso
    id_recurso: UUID | None
    valor: dict[str, Any]
    cambios: list[CambioRegistrado]
