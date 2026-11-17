from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

from bugalu.modulos.notificaciones.aplicacion.enviar_pendientes.caso_de_uso import enviar_pendientes
from bugalu.modulos.notificaciones.dominio.correo import Correo
from bugalu.modulos.notificaciones.dominio.puertos import DatosReserva, Pendiente

DATOS = {"folio": "BG-1", "inicio": "2027-03-10T15:00:00+00:00", "fin": "2027-03-10T17:00:00+00:00"}


class LoteFalso:
    def __init__(self, pendientes: list[Pendiente]) -> None:
        self.pendientes = pendientes
        self.instrucciones: list[tuple[str, str]] = []
        self.reservas: dict[UUID, DatosReserva] = {}
        self.enviadas: list[UUID] = []
        self.fallos: dict[UUID, str] = {}

    async def marcar_enviada(self, id_: UUID) -> None:
        self.enviadas.append(id_)

    async def marcar_fallo(self, id_: UUID, error: str) -> None:
        self.fallos[id_] = error


class BandejaFalsa:
    def __init__(self, pendientes: list[Pendiente]) -> None:
        self.lote = LoteFalso(pendientes)

    @asynccontextmanager
    async def tomar(self, limite: int, max_intentos: int) -> AsyncIterator[LoteFalso]:
        yield self.lote


class EnviadorFalso:
    def __init__(self, falla_con: str | None = None) -> None:
        self.enviados: list[Correo] = []
        self.falla_con = falla_con

    async def enviar(self, correo: Correo) -> None:
        if self.falla_con and correo.destinatario == self.falla_con:
            raise ConnectionRefusedError("clave=secreta " + "x" * 500)
        self.enviados.append(correo)


def pendiente(destinatario: str = "a@b.pe", tipo: str = "reserva_caducada") -> Pendiente:
    return Pendiente(uuid4(), tipo, destinatario, DATOS, 0)


async def test_envia_y_marca_enviada() -> None:
    p = pendiente()
    bandeja, enviador = BandejaFalsa([p]), EnviadorFalso()
    assert await enviar_pendientes(bandeja, enviador) == 1
    assert [c.destinatario for c in enviador.enviados] == ["a@b.pe"]
    assert "BG-1" in enviador.enviados[0].asunto
    assert bandeja.lote.enviadas == [p.id]


async def test_un_fallo_se_registra_corto_y_no_detiene_a_los_demas() -> None:
    malo, bueno = pendiente("malo@b.pe"), pendiente("bueno@b.pe")
    bandeja, enviador = BandejaFalsa([malo, bueno]), EnviadorFalso(falla_con="malo@b.pe")
    assert await enviar_pendientes(bandeja, enviador) == 1
    assert bandeja.lote.enviadas == [bueno.id]
    assert list(bandeja.lote.fallos) == [malo.id]
    error = bandeja.lote.fallos[malo.id]
    assert error == "ConnectionRefusedError"
    assert "secreta" not in error


async def test_destinatario_con_salto_de_linea_es_un_fallo_y_no_se_envia() -> None:
    p = pendiente("a@b.pe\r\nBcc: x@y.pe")
    bandeja, enviador = BandejaFalsa([p]), EnviadorFalso()
    assert await enviar_pendientes(bandeja, enviador) == 0
    assert enviador.enviados == []
    assert p.id in bandeja.lote.fallos


async def test_tipo_desconocido_es_un_fallo() -> None:
    p = pendiente(tipo="otro")
    bandeja = BandejaFalsa([p])
    assert await enviar_pendientes(bandeja, EnviadorFalso()) == 0
    assert p.id in bandeja.lote.fallos


async def test_el_correo_sale_con_la_plantilla_y_la_url_publica_configurada() -> None:
    bandeja, enviador = BandejaFalsa([pendiente()]), EnviadorFalso()
    await enviar_pendientes(bandeja, enviador, url_publica="https://erp.bugalu.pe/")
    correo = enviador.enviados[0]
    assert correo.html.startswith("<!doctype html>") and correo.evento is None
    assert "https://erp.bugalu.pe/reservar/" in correo.cuerpo
    assert "https://erp.bugalu.pe//" not in correo.cuerpo


async def test_aviso_confirmado_sale_con_ics_de_la_reserva_de_la_bandeja() -> None:
    datos = {
        "id_reserva": "r-1", "folio": "BG-1", "hito": "al_reservar", "monto": 10,
        "reserva_confirmada": True,
    }  # fmt: skip
    p = Pendiente(uuid4(), "pago_aprobado", "a@b.pe", datos, 0, datetime(2027, 3, 1, tzinfo=UTC))
    bandeja, enviador = BandejaFalsa([p]), EnviadorFalso()
    bandeja.lote.reservas[p.id] = DatosReserva(
        datetime(2027, 3, 10, 15, tzinfo=UTC),
        datetime(2027, 3, 10, 17, tzinfo=UTC),
        "Grabación",
        "Sala A",
        True,
    )
    assert await enviar_pendientes(bandeja, enviador, remitente="no-responder@bugalu.pe") == 1
    evento = enviador.enviados[0].evento
    assert evento is not None and evento.metodo == "REQUEST"
    assert "ORGANIZER;CN=Bugalú Studio:mailto:no-responder@bugalu.pe" in evento.ics


async def test_aviso_confirmado_sin_datos_de_la_reserva_es_un_fallo_para_reintentar() -> None:
    datos = {
        "id_reserva": "r-1", "folio": "BG-1", "hito": "al_reservar", "monto": 10,
        "reserva_confirmada": True,
    }  # fmt: skip
    p = Pendiente(uuid4(), "pago_aprobado", "a@b.pe", datos, 0, datetime(2027, 3, 1, tzinfo=UTC))
    bandeja = BandejaFalsa([p])
    assert await enviar_pendientes(bandeja, EnviadorFalso()) == 0
    assert bandeja.lote.fallos == {p.id: "ValueError"}
