from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from bugalu.modulos.reclamaciones.dominio.modelos import Alta, Hoja, HojaResumen, NuevaHoja


class RepositorioHojas(Protocol):
    """Recibe una transaccion con identidad (o `anon` en el alta): la RLS decide el acceso.
    Los errores de la base llegan ya traducidos (demasiadas_solicitudes, ya_respondida...)."""

    async def es_administrador(self) -> bool: ...

    async def registrar(self, id_: UUID, nueva: NuevaHoja, ip: str | None) -> Alta:
        """Alta publica: limite por IP, correlativo, plazo y avisos, en la propia transaccion."""
        ...

    async def transcribir(self, id_: UUID, nueva: NuevaHoja) -> Alta: ...

    async def confirmar_adjunto(self, ruta: str) -> None:
        """Tras subir el objeto a su ruta. Falla con AlmacenamientoNoDisponible."""
        ...

    async def obtener(self, id_: UUID) -> Hoja | None:
        """Solo las visibles para el usuario (dueno o administrador)."""
        ...

    async def listar_mias(self) -> list[HojaResumen]: ...

    async def listar(
        self, estado: str | None, desde: date | None, hasta: date | None
    ) -> list[HojaResumen]:
        """Pendientes primero por `vence_respuesta`; luego las respondidas, la mas reciente antes.
        El rango es por la fecha de presentacion en Lima."""
        ...

    async def responder(
        self, id_: UUID, texto: str, referencia: str | None, enviada_en: datetime | None
    ) -> None: ...

    async def exportar(self, desde: date, hasta: date) -> list[Hoja]: ...


# Abre una transaccion (con la identidad de quien llama, o `anon`); al salir hace commit.
AbrirRepositorio = Callable[[], AbstractAsyncContextManager[RepositorioHojas]]


class AlmacenAdjuntos(Protocol):
    async def subir(self, ruta: str, contenido: bytes, mime: str) -> None:
        """Falla con AlmacenamientoNoDisponible."""
        ...

    async def firmar(self, ruta: str, segundos: int) -> str: ...
