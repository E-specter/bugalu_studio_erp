from datetime import datetime, timedelta
from uuid import UUID

from bugalu.modulos.pagos.aplicacion.obtener_pago.caso_de_uso import pago_visible
from bugalu.modulos.pagos.dominio.captura import tipo_por_mime
from bugalu.modulos.pagos.dominio.modelos import CapturaFirmada
from bugalu.modulos.pagos.dominio.puertos import AlmacenCapturas, RepositorioPagos

VIGENCIA_SEGUNDOS = 300


class ObtenerCaptura:
    def __init__(self, pagos: RepositorioPagos, almacen: AlmacenCapturas) -> None:
        self._pagos = pagos
        self._almacen = almacen

    async def ejecutar(self, id_pago: UUID, ahora: datetime) -> CapturaFirmada:
        pago = await pago_visible(self._pagos, id_pago)
        url = await self._almacen.firmar(pago.ruta_captura, VIGENCIA_SEGUNDOS)
        return CapturaFirmada(
            url,
            ahora + timedelta(seconds=VIGENCIA_SEGUNDOS),
            tipo_por_mime(pago.tipo_captura).clase,
        )
