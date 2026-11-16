from decimal import Decimal
from uuid import UUID, uuid4

from bugalu.compartido.errores import ArchivoMuyGrande, FormatoNoAdmitido
from bugalu.modulos.pagos.dominio.captura import BYTES_FIRMA, LIMITE_BYTES, detectar_tipo
from bugalu.modulos.pagos.dominio.modelos import NuevoPago, Pago
from bugalu.modulos.pagos.dominio.puertos import AlmacenCapturas, RepositorioPagos


class RegistrarPago:
    def __init__(self, pagos: RepositorioPagos, almacen: AlmacenCapturas) -> None:
        self._pagos = pagos
        self._almacen = almacen

    async def ejecutar(
        self,
        id_cliente: UUID,
        id_cuota: UUID,
        metodo: str,
        monto: Decimal,
        numero_operacion: str,
        captura: bytes,
    ) -> Pago:
        if len(captura) > LIMITE_BYTES:
            raise ArchivoMuyGrande("La captura pesa mas de 5 MB.")
        tipo = detectar_tipo(captura[:BYTES_FIRMA])
        if tipo is None:
            raise FormatoNoAdmitido("La captura debe ser JPG, PNG o PDF.", {"campo": "captura"})
        id_pago = uuid4()
        ruta = f"{id_cliente}/{id_pago}.{tipo.extension}"
        # ADR-010: insertar (valida todo) -> subir -> confirmar (al salir de la transaccion).
        await self._pagos.insertar_pago(
            NuevoPago(
                id_pago,
                id_cuota,
                id_cliente,
                metodo,
                monto,
                numero_operacion.upper(),
                ruta,
                tipo.mime,
            )
        )
        await self._almacen.subir(ruta, captura, tipo.mime)
        pago = await self._pagos.obtener_pago(id_pago)
        assert pago is not None  # el dueño lee lo que acaba de insertar
        return pago
