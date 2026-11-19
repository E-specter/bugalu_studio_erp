from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from bugalu.compartido.esquemas import TextoLargo
from bugalu.modulos.pagos.dominio import modelos
from bugalu.modulos.reservas.dominio.disponibilidad import LIMA
from bugalu.modulos.reservas.infraestructura.entrada.http.esquemas import Devolucion


class OrigenCredito(BaseModel):
    id_reserva: UUID
    folio: str
    tipo: str


class Credito(BaseModel):
    id: UUID
    monto: Decimal
    saldo: Decimal
    vence: datetime
    estado: Literal["vigente", "agotado", "vencido"]
    tipo: Literal["nivel_1", "nivel_2", "reprogramacion", "excepcion"]
    origen: OrigenCredito
    devolucion: Devolucion | None = None

    @classmethod
    def desde_dominio(cls, c: modelos.Credito) -> Credito:
        campos = {
            "id": c.id,
            "monto": c.monto,
            "saldo": c.saldo,
            "vence": c.vence.astimezone(LIMA),
            "estado": c.estado,
            "tipo": c.tipo,
            "origen": OrigenCredito(
                id_reserva=c.origen.id_reserva, folio=c.origen.folio, tipo=c.origen.tipo
            ),
        }
        if c.devolucion:  # opcional: solo si alguna vez se pidio
            campos["devolucion"] = Devolucion.desde_dominio(c.devolucion)
        return cls(**campos)


class AplicacionCredito(BaseModel):
    """`monto` sin tope de decimales: la base rechaza lo invalido con `monto_invalido`."""

    model_config = ConfigDict(extra="forbid")
    monto: Annotated[Decimal, Field(allow_inf_nan=False, max_digits=12)]
    id_credito: UUID | None = None


class SolicitudDevolucion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: Annotated[TextoLargo, Field(min_length=10)]


class DecisionDevolucion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["total", "parcial", "rechazo"]
    monto: Annotated[Decimal, Field(allow_inf_nan=False, max_digits=12)] | None = None
    motivo: TextoLargo | None = None


class NotaRealizada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nota: TextoLargo
