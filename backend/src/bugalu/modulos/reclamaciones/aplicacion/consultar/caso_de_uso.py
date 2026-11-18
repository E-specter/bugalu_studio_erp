from dataclasses import replace
from datetime import date, datetime, timedelta
from uuid import UUID

from bugalu.compartido.errores import NoEncontrado, RangoInvalido, SinPermiso
from bugalu.modulos.reclamaciones.dominio.exportar import a_csv, fila_csv
from bugalu.modulos.reclamaciones.dominio.modelos import Hoja, HojaResumen
from bugalu.modulos.reclamaciones.dominio.puertos import AlmacenAdjuntos, RepositorioHojas

SEGUNDOS_URL = 300


async def _exigir_administrador(hojas: RepositorioHojas) -> None:
    if not await hojas.es_administrador():
        raise SinPermiso("Solo el Administrador puede hacerlo.")


def _rango(desde: date | None, hasta: date | None) -> None:
    if desde and hasta and desde > hasta:
        raise RangoInvalido("La fecha inicial es posterior a la final.", {"campo": "desde"})


def _para_el_cliente(h: Hoja) -> Hoja:
    """La marca de spam y el autor de la respuesta son del Administrador."""
    respuesta = replace(h.respuesta, respondida_por=None) if h.respuesta else None
    return replace(h, revisar_spam=None, respuesta=respuesta)


class ObtenerHoja:
    def __init__(self, hojas: RepositorioHojas) -> None:
        self._hojas = hojas

    async def ejecutar(self, id_: UUID) -> Hoja:
        hoja = await self._hojas.obtener(id_)
        if hoja is None:  # inexistente o ajena: no se distingue
            raise NoEncontrado("No existe esa hoja.")
        return hoja if await self._hojas.es_administrador() else _para_el_cliente(hoja)


class ListarMisHojas:
    def __init__(self, hojas: RepositorioHojas) -> None:
        self._hojas = hojas

    async def ejecutar(self) -> list[HojaResumen]:
        return [replace(r, revisar_spam=None) for r in await self._hojas.listar_mias()]


class ListarHojas:
    def __init__(self, hojas: RepositorioHojas) -> None:
        self._hojas = hojas

    async def ejecutar(
        self, estado: str | None, desde: date | None, hasta: date | None
    ) -> list[HojaResumen]:
        await _exigir_administrador(self._hojas)
        _rango(desde, hasta)
        return await self._hojas.listar(estado, desde, hasta)


class UrlAdjunto:
    def __init__(self, hojas: RepositorioHojas, almacen: AlmacenAdjuntos) -> None:
        self._hojas = hojas
        self._almacen = almacen

    async def ejecutar(self, id_: UUID, n: int, ahora: datetime) -> tuple[str, datetime]:
        await _exigir_administrador(self._hojas)
        hoja = await self._hojas.obtener(id_)
        adjunto = next((a for a in hoja.adjuntos if a.n == n), None) if hoja else None
        if adjunto is None:
            raise NoEncontrado("No existe ese adjunto.")
        url = await self._almacen.firmar(adjunto.ruta, SEGUNDOS_URL)
        return url, ahora + timedelta(seconds=SEGUNDOS_URL)


class ExportarHojas:
    def __init__(self, hojas: RepositorioHojas) -> None:
        self._hojas = hojas

    async def ejecutar(self, desde: date, hasta: date) -> str:
        await _exigir_administrador(self._hojas)
        _rango(desde, hasta)
        return a_csv([fila_csv(h) for h in await self._hojas.exportar(desde, hasta)])
