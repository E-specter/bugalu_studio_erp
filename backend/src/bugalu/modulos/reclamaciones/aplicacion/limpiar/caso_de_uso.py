import logging

from bugalu.modulos.reclamaciones.dominio.puertos import AbrirRepositorio, AlmacenAdjuntos

_registro = logging.getLogger(__name__)


class LimpiarAdjuntosHuerfanos:
    """Borra de Storage los objetos subidos cuya confirmacion fallo y cuya subida ya caduco.
    La fila de la subida la quita despues la limpieza diaria de la base."""

    def __init__(self, abrir: AbrirRepositorio, almacen: AlmacenAdjuntos) -> None:
        self._abrir = abrir
        self._almacen = almacen

    async def ejecutar(self) -> int:
        async with self._abrir() as hojas:
            rutas = await hojas.rutas_huerfanas()
        borradas = 0
        for ruta in rutas:
            try:
                await self._almacen.borrar(ruta)
            except Exception:  # noqa: BLE001 - una ruta que falla no frena las demas
                _registro.exception("No se pudo borrar el adjunto huerfano %s.", ruta)
                continue
            borradas += 1
        return borradas
