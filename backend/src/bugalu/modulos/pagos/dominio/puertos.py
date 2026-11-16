from typing import Protocol
from uuid import UUID

from bugalu.modulos.pagos.dominio.instrucciones import Instruccion
from bugalu.modulos.pagos.dominio.modelos import NuevoPago, Pago


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
