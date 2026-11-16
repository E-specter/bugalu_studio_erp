from typing import Protocol
from uuid import UUID

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


class AlmacenCapturas(Protocol):
    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        """Falla con AlmacenamientoNoDisponible."""
        ...

    async def firmar(self, ruta: str, segundos: int) -> str: ...
