"""RF-18 CA-08 a CA-10 y CA-13: se valida el horario nuevo y el calculo lo hace la base."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from bugalu.compartido.errores import (
    AnticipacionInsuficiente,
    FueraDeFranja,
    NivelCambiado,
    TramoNoDisponible,
)
from bugalu.modulos.reservas.aplicacion.reprogramar_reserva.caso_de_uso import (
    ReprogramarReserva,
    SimularReprogramacion,
)
from bugalu.modulos.reservas.dominio.disponibilidad import Tramo
from bugalu.modulos.reservas.dominio.modelos import (
    ContextoReprogramacion,
    Cotizacion,
    EspecialistaAplicado,
    Franja,
    VistaReprogramacion,
)
from tests.modulos.reservas.aplicacion.falsos import SALA, ReservasFalso, t

AHORA = t(1, 0)
ID = uuid4()
PRECIO_VIEJO: dict[str, Any] = {"total": "200.00"}
PRECIO_NUEVO: dict[str, Any] = {"total": "240.00"}


class ReprogramacionFalsa(ReservasFalso):
    def __init__(self, estudio: bool = False) -> None:
        super().__init__(personal=False)
        self.contexto = ContextoReprogramacion(
            SALA.id, uuid4(), t(10, 10), t(10, 12), estudio, PRECIO_VIEJO, Decimal("200.00"),
            (uuid4(),),
        )  # fmt: skip
        self.franjas[uuid4()] = Franja(uuid4(), SALA.id, t(20, 8), t(20, 20))
        self.llamadas: list[tuple[Any, ...]] = []
        self.error: Exception | None = None

    async def contexto_reprogramacion(self, id_reserva: UUID) -> ContextoReprogramacion:
        return self.contexto

    async def ocupacion_excluyendo(
        self, id_sala: UUID, desde: datetime, hasta: datetime, excluir: UUID
    ) -> list[Tramo]:
        assert excluir == ID
        return await self.ocupacion(id_sala, desde, hasta)

    async def vista_reprogramacion(
        self, id_reserva: UUID, inicio: datetime, total: Decimal, precio: dict[str, Any]
    ) -> VistaReprogramacion:
        self.llamadas.append(("vista", total, precio))
        return VistaReprogramacion(1, Decimal("0.00"), precio, Decimal("0.00"), Decimal("20.00"), 1)

    async def reprogramar_reserva(  # noqa: PLR0913
        self,
        id_reserva: UUID,
        inicio: datetime,
        nivel_esperado: int | None,
        total_esperado: Decimal | None,
        id_franja: UUID,
        precio: dict[str, Any],
        total: Decimal,
        especialistas: Sequence[EspecialistaAplicado],
    ) -> None:
        self.llamadas.append(("reprogramar", nivel_esperado, total_esperado, precio, total))
        if self.error:
            raise self.error

    async def obtener_reserva(self, id_reserva: UUID) -> Any:
        return "reserva"

    async def existe_reserva(self, id_reserva: UUID) -> bool:
        return True


class CotizadorFalso:
    def __init__(self) -> None:
        self.llamadas = 0

    async def cotizar(
        self,
        id_sala: UUID,
        id_servicio: UUID,
        inicio: datetime,
        fin: datetime,
        id_especialistas: Sequence[UUID],
    ) -> Cotizacion:
        self.llamadas += 1
        assert fin - inicio == timedelta(hours=2)  # la misma duracion
        return Cotizacion("ensayo", PRECIO_NUEVO, Decimal("240.00"), Decimal("120.00"), (), {})


async def test_simular_cotiza_el_horario_nuevo_y_no_bloquea_ni_escribe() -> None:
    falso, cotizador = ReprogramacionFalsa(), CotizadorFalso()
    vista = await SimularReprogramacion(falso, cotizador).ejecutar(ID, t(20, 10), AHORA)
    assert falso.llamadas == [("vista", Decimal("240.00"), PRECIO_NUEVO)]
    assert vista.precio == PRECIO_NUEVO and falso.bloqueos == []


async def test_reprogramar_bloquea_la_sala_antes_de_leer_y_pasa_el_precio_a_la_base() -> None:
    falso, cotizador = ReprogramacionFalsa(), CotizadorFalso()
    await ReprogramarReserva(falso, cotizador).ejecutar(ID, t(20, 10), 1, Decimal("240.00"), AHORA)
    assert falso.bloqueos == [SALA.id]
    assert falso.llamadas == [
        ("reprogramar", 1, Decimal("240.00"), PRECIO_NUEVO, Decimal("240.00"))
    ]


async def test_tras_una_cancelacion_del_estudio_no_se_recalcula_el_precio() -> None:
    falso, cotizador = ReprogramacionFalsa(estudio=True), CotizadorFalso()
    await ReprogramarReserva(falso, cotizador).ejecutar(ID, t(20, 10), None, None, AHORA)
    assert cotizador.llamadas == 0
    assert falso.llamadas == [("reprogramar", None, None, PRECIO_VIEJO, Decimal("200.00"))]


async def test_el_tramo_ocupado_por_otra_reserva_es_409_y_no_escribe() -> None:
    falso = ReprogramacionFalsa()
    falso.ocupados.append(Tramo(t(20, 9), t(20, 11)))
    with pytest.raises(TramoNoDisponible):
        await ReprogramarReserva(falso, CotizadorFalso()).ejecutar(ID, t(20, 10), 1, None, AHORA)
    assert falso.llamadas == []


async def test_sin_franja_o_con_cierre_es_fuera_de_franja() -> None:
    falso = ReprogramacionFalsa()
    with pytest.raises(FueraDeFranja):
        await SimularReprogramacion(falso, CotizadorFalso()).ejecutar(ID, t(21, 10), AHORA)
    await falso.insertar_cierre(SALA.id, Tramo(t(20, 10), t(20, 11)), "Mantenimiento")
    with pytest.raises(FueraDeFranja):
        await SimularReprogramacion(falso, CotizadorFalso()).ejecutar(ID, t(20, 10), AHORA)


async def test_la_anticipacion_minima_aplica_como_en_una_reserva_nueva() -> None:
    falso = ReprogramacionFalsa()
    with pytest.raises(AnticipacionInsuficiente):
        await SimularReprogramacion(falso, CotizadorFalso()).ejecutar(ID, t(1, 1), AHORA)


async def test_un_nivel_cambiado_de_la_base_lleva_el_precio_nuevo_en_el_detalle() -> None:
    falso = ReprogramacionFalsa()
    falso.error = NivelCambiado("cambio", {"nivel": 2})
    with pytest.raises(NivelCambiado) as e:
        await ReprogramarReserva(falso, CotizadorFalso()).ejecutar(
            ID, t(20, 10), 1, Decimal("240.00"), AHORA
        )
    assert e.value.detalles == {"nivel": 2, "precio": PRECIO_NUEVO}
