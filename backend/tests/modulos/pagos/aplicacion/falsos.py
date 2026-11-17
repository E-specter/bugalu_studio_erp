from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from bugalu.compartido.errores import AlmacenamientoNoDisponible
from bugalu.modulos.pagos.dominio.modelos import (
    ClienteResumen,
    CuotaResumen,
    NuevoPago,
    Pago,
    ReservaResumen,
)


class PagosFalso:
    def __init__(self, administrador: bool = False, eventos: list[str] | None = None) -> None:
        self.administrador = administrador
        self.eventos = eventos if eventos is not None else []
        self.pagos: dict[UUID, Pago] = {}
        self.ocultos: set[UUID] = set()  # existen, pero la RLS los oculta

    async def es_administrador(self) -> bool:
        return self.administrador

    async def insertar_pago(self, nuevo: NuevoPago) -> None:
        self.eventos.append("insertar")
        self.pagos[nuevo.id] = Pago(
            id=nuevo.id,
            estado="pendiente_validacion",
            metodo=nuevo.metodo,
            monto=nuevo.monto,
            numero_operacion=nuevo.numero_operacion,
            motivo_rechazo=None,
            registrado_en=datetime.now(UTC),
            validado_en=None,
            ruta_captura=nuevo.ruta_captura,
            tipo_captura=nuevo.tipo_captura,
            cuota=CuotaResumen(nuevo.id_cuota, "al_reservar", Decimal("50.00")),
            reserva=ReservaResumen(
                UUID(int=1), "R-2027-00001", datetime.now(UTC), "pre_reservada", Decimal("18.00")
            ),
            cliente=ClienteResumen(nuevo.id_cliente, "Ana") if self.administrador else None,
        )

    async def obtener_pago(self, id_pago: UUID) -> Pago | None:
        return None if id_pago in self.ocultos else self.pagos.get(id_pago)

    async def existe_pago(self, id_pago: UUID) -> bool:
        return id_pago in self.pagos or id_pago in self.ocultos

    async def listar_pagos(self, estado: str) -> list[Pago]:
        return [p for p in self.pagos.values() if p.estado == estado]

    async def aprobar_pago(self, id_pago: UUID) -> None:
        self.eventos.append("aprobar")
        self.pagos[id_pago] = replace(self.pagos[id_pago], estado="aprobado")

    async def rechazar_pago(self, id_pago: UUID, motivo: str) -> None:
        self.eventos.append("rechazar")
        self.pagos[id_pago] = replace(
            self.pagos[id_pago], estado="rechazado", motivo_rechazo=motivo
        )


class AlmacenFalso:
    def __init__(self, eventos: list[str] | None = None, falla: bool = False) -> None:
        self.eventos = eventos if eventos is not None else []
        self.falla = falla
        self.subidos: dict[str, tuple[bytes, str]] = {}

    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        self.eventos.append("subir")
        if self.falla:
            raise AlmacenamientoNoDisponible("caido")
        self.subidos[ruta] = (contenido, mime)

    async def firmar(self, ruta: str, segundos: int) -> str:
        if self.falla:
            raise AlmacenamientoNoDisponible("caido")
        return f"http://storage/firmada/{ruta}?ttl={segundos}"
