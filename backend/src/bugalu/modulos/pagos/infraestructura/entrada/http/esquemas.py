from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, SerializerFunctionWrapHandler, model_serializer

from bugalu.modulos.pagos.dominio import modelos
from bugalu.modulos.reservas.dominio.disponibilidad import LIMA


class CuotaDelPago(BaseModel):
    id: UUID
    hito: str
    monto: Decimal


class ReservaDelPago(BaseModel):
    id: UUID
    folio: str
    inicio: datetime
    estado: str


class ClienteDelPago(BaseModel):
    id: UUID
    nombre: str | None


class Pago(BaseModel):
    id: UUID
    estado: str
    metodo: str
    monto: Decimal
    numero_operacion: str
    motivo_rechazo: str | None
    registrado_en: datetime
    validado_en: datetime | None
    monto_coincide: bool
    cuota: CuotaDelPago
    reserva: ReservaDelPago
    cliente: ClienteDelPago | None = None

    @model_serializer(mode="wrap")
    def _cliente_solo_para_el_administrador(
        self, siguiente: SerializerFunctionWrapHandler
    ) -> dict[str, Any]:
        datos: dict[str, Any] = siguiente(self)
        if datos.get("cliente") is None:
            datos.pop("cliente", None)
        return datos

    @classmethod
    def desde_dominio(cls, p: modelos.Pago) -> Pago:
        return cls(
            id=p.id,
            estado=p.estado,
            metodo=p.metodo,
            monto=p.monto,
            numero_operacion=p.numero_operacion,
            motivo_rechazo=p.motivo_rechazo,
            registrado_en=p.registrado_en.astimezone(LIMA),
            validado_en=p.validado_en.astimezone(LIMA) if p.validado_en else None,
            monto_coincide=p.monto_coincide,
            cuota=CuotaDelPago(id=p.cuota.id, hito=p.cuota.hito, monto=p.cuota.monto),
            reserva=ReservaDelPago(
                id=p.reserva.id,
                folio=p.reserva.folio,
                inicio=p.reserva.inicio.astimezone(LIMA),
                estado=p.reserva.estado,
            ),
            cliente=ClienteDelPago(id=p.cliente.id, nombre=p.cliente.nombre) if p.cliente else None,
        )


class Captura(BaseModel):
    url: str
    expira_en: datetime
    tipo: str
