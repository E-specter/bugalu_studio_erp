from uuid import UUID

from bugalu.compartido.errores import CierreConReservas, NoEncontrado
from bugalu.modulos.reservas.aplicacion.permisos import exigir_administrador
from bugalu.modulos.reservas.dominio.disponibilidad import LIMA, Tramo
from bugalu.modulos.reservas.dominio.modelos import Cierre
from bugalu.modulos.reservas.dominio.puertos import RepositorioReservas


class RegistrarCierre:
    def __init__(self, reservas: RepositorioReservas) -> None:
        self._reservas = reservas

    async def ejecutar(self, id_sala: UUID, tramo: Tramo, motivo: str) -> Cierre:
        await exigir_administrador(self._reservas)
        if not await self._reservas.existe_sala(id_sala):
            raise NoEncontrado("No existe la sala.")
        ocupados = {
            (o.inicio, o.fin)
            for o in await self._reservas.ocupacion(id_sala, tramo.inicio, tramo.fin)
        }
        if ocupados:
            reservas = [
                r
                for r in await self._reservas.reservas_visibles(id_sala, tramo.inicio, tramo.fin)
                if (r.inicio, r.fin_buffer) in ocupados
            ]
            nombres = await self._reservas.nombres_de_clientes([r.id_cliente for r in reservas])
            raise CierreConReservas(
                "Hay reservas vigentes dentro del cierre.",
                {
                    "reservas": [
                        {
                            "id": str(r.id),
                            "folio": r.folio,
                            "inicio": r.inicio.astimezone(LIMA).isoformat(),
                            "cliente": nombres.get(r.id_cliente),
                        }
                        for r in reservas
                    ]
                },
            )
        return await self._reservas.insertar_cierre(id_sala, tramo, motivo)
