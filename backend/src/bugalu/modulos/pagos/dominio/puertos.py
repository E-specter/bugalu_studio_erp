from decimal import Decimal
from typing import Protocol
from uuid import UUID

from bugalu.modulos.pagos.dominio.instrucciones import Instruccion
from bugalu.modulos.pagos.dominio.modelos import Credito, NuevoPago, Pago
from bugalu.modulos.reservas.dominio.modelos import Devolucion


class RepositorioPagos(Protocol):
    async def es_administrador(self) -> bool: ...

    async def insertar_pago(self, nuevo: NuevoPago) -> None:
        """Errores de la base ya traducidos (cuota_pagada, operacion_duplicada, 403, 404...)."""
        ...

    async def obtener_pago(self, id_pago: UUID) -> Pago | None:
        """Solo los visibles para el usuario (RLS); `cliente` solo si es administrador."""
        ...

    async def existe_pago(self, id_pago: UUID) -> bool:
        """Sin RLS: distingue 403 de 404."""
        ...

    async def listar_pagos(self, estado: str) -> list[Pago]:
        """Del estado dado (con `cliente`): pendientes del mas antiguo al mas reciente; el resto
        por `validado_en` descendente."""
        ...

    async def aprobar_pago(self, id_pago: UUID) -> None:
        """Errores de la base ya traducidos (403, 404, pago_ya_validado)."""
        ...

    async def rechazar_pago(self, id_pago: UUID, motivo: str) -> None:
        """Errores de la base ya traducidos (403, 404, pago_ya_validado, motivo invalido)."""
        ...


class AlmacenCapturas(Protocol):
    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        """Falla con AlmacenamientoNoDisponible."""
        ...

    async def firmar(self, ruta: str, segundos: int) -> str: ...


class RepositorioDatosPago(Protocol):
    async def es_administrador(self) -> bool: ...

    async def listar_instrucciones(self) -> list[Instruccion]:
        """Las que deja ver la RLS: al cliente, solo las activas; en el orden de METODOS."""
        ...

    async def guardar_instrucciones(self, instrucciones: list[Instruccion]) -> None: ...

    async def obtener_contacto(self) -> str: ...

    async def guardar_contacto(self, texto: str) -> None: ...


class RepositorioCreditos(Protocol):
    """Creditos, su uso y devoluciones (RF-18). Los errores de la base ya vienen traducidos."""

    async def es_administrador(self) -> bool: ...

    async def es_personal(self) -> bool: ...

    async def listar_creditos(self, id_cliente: UUID) -> list[Credito]: ...

    async def aplicar_credito(
        self, id_cuota: UUID, monto: Decimal, id_credito: UUID | None
    ) -> UUID:
        """Devuelve la reserva de la cuota."""
        ...

    async def solicitar_devolucion(self, id_credito: UUID, motivo: str) -> UUID: ...

    async def obtener_devolucion(self, id_devolucion: UUID) -> Devolucion | None:
        """Solo las que la RLS deja ver (el dueno y el administrador)."""
        ...

    async def listar_devoluciones(self, estado: str) -> list[Devolucion]: ...

    async def decidir_devolucion(
        self, id_devolucion: UUID, decision: str, monto: Decimal | None, motivo: str | None
    ) -> None: ...

    async def marcar_devolucion_realizada(self, id_devolucion: UUID, nota: str) -> None: ...
