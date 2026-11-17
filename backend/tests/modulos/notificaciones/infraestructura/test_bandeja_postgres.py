"""Bandeja `notificacion` con el rol bugalu_api real: lote exclusivo, marcas, tope de intentos."""

# ruff: noqa: E501 - datos de ejemplo y textos literales de la spec

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Iterator
from uuid import UUID

import psycopg
import pytest
from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.notificaciones.aplicacion.enviar_pendientes.caso_de_uso import enviar_pendientes
from bugalu.modulos.notificaciones.dominio.correo import Correo
from bugalu.modulos.notificaciones.infraestructura.salida.bandeja_postgres import BandejaPostgres
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

DATOS = (
    '{"folio": "BG-T", "inicio": "2027-03-10T15:00:00+00:00", "fin": "2027-03-10T17:00:00+00:00"}'
)
Poner = Callable[..., UUID]
INICIO, FIN = "2027-06-10T15:00:00+00:00", "2027-06-10T17:00:00+00:00"


class EnviadorLento:
    def __init__(self, falla: bool = False) -> None:
        self.enviados: list[str] = []
        self.correos: list[Correo] = []
        self.falla = falla

    async def enviar(self, correo: Correo) -> None:
        await asyncio.sleep(0.2)
        if self.falla:
            raise ConnectionRefusedError("sin servidor")
        self.enviados.append(correo.destinatario)
        self.correos.append(correo)


@pytest.fixture
async def bandeja(configuracion: Configuracion) -> AsyncIterator[BandejaPostgres]:
    async with crear_pool(configuracion.url_base_datos) as pool:
        yield BandejaPostgres(pool)


@pytest.fixture
def poner(configuracion: Configuracion) -> Iterator[Poner]:
    """Inserta pendientes de prueba (correos @prueba.bugalu.pe) y los borra al terminar."""
    with psycopg.connect(configuracion.url_base_datos_admin, autocommit=True) as c:

        def crear(destinatario: str, intentos: int = 0) -> UUID:
            return c.execute(
                "insert into public.notificacion (tipo, destinatario, datos, intentos) "
                "values ('reserva_caducada', %s, %s, %s) returning id",
                (destinatario, DATOS, intentos),
            ).fetchone()[0]  # type: ignore[index]

        yield crear
        c.execute("delete from public.notificacion where destinatario like '%@prueba.bugalu.pe'")
        assert c.execute("select count(*) from public.notificacion").fetchone() == (0,)


def estado(configuracion: Configuracion, id_: UUID) -> tuple[object, int, str | None]:
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        return c.execute(  # type: ignore[return-value]
            "select enviada_en, intentos, error from public.notificacion where id = %s", (id_,)
        ).fetchone()


async def test_envia_y_marca_enviada_en(
    bandeja: BandejaPostgres, poner: Poner, configuracion: Configuracion
) -> None:
    id_ = poner("ok@prueba.bugalu.pe")
    enviador = EnviadorLento()
    assert await enviar_pendientes(bandeja, enviador) == 1
    enviada, intentos, error = estado(configuracion, id_)
    assert enviada is not None and error is None
    assert enviador.enviados == ["ok@prueba.bugalu.pe"]
    assert await enviar_pendientes(bandeja, enviador) == 0  # ya no esta pendiente


async def test_un_fallo_suma_un_intento_y_guarda_el_error(
    bandeja: BandejaPostgres, poner: Poner, configuracion: Configuracion
) -> None:
    id_ = poner("fallo@prueba.bugalu.pe")
    assert await enviar_pendientes(bandeja, EnviadorLento(falla=True)) == 0
    assert estado(configuracion, id_) == (None, 1, "ConnectionRefusedError")


async def test_a_los_5_intentos_deja_de_reintentar(
    bandeja: BandejaPostgres, poner: Poner, configuracion: Configuracion
) -> None:
    agotada = poner("agotada@prueba.bugalu.pe", intentos=5)
    cuarta = poner("cuarta@prueba.bugalu.pe", intentos=4)
    enviador = EnviadorLento()
    assert await enviar_pendientes(bandeja, enviador) == 1
    assert enviador.enviados == ["cuarta@prueba.bugalu.pe"]
    assert estado(configuracion, agotada) == (None, 5, None)
    assert estado(configuracion, cuarta)[0] is not None


async def test_dos_ejecuciones_concurrentes_no_envian_dos_veces(
    configuracion: Configuracion, poner: Poner
) -> None:
    for i in range(6):
        poner(f"c{i}@prueba.bugalu.pe")
    pool: AsyncConnectionPool
    async with crear_pool(configuracion.url_base_datos) as pool:
        bandeja, enviador = BandejaPostgres(pool), EnviadorLento()
        resultados = await asyncio.gather(
            enviar_pendientes(bandeja, enviador, limite=3),
            enviar_pendientes(bandeja, enviador, limite=3),
        )
    assert sorted(resultados) == [3, 3]
    assert sorted(enviador.enviados) == [f"c{i}@prueba.bugalu.pe" for i in range(6)]


@pytest.fixture
def reserva_de_prueba(
    configuracion: Configuracion, crear_usuario: Callable[[], UsuarioDePrueba]
) -> Iterator[UUID]:
    """Una reserva confirmada de 2027 (la limpia al terminar) para los avisos con evento."""
    cliente = crear_usuario()
    with psycopg.connect(configuracion.url_base_datos_admin, autocommit=True) as c:
        id_ = c.execute(
            "insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, "
            "estado) select %s, sa.id, se.id, '2027-06-10 15:00+00', '2027-06-10 17:00+00', 50, "
            "'confirmada' from public.servicio se, (select id from public.sala_tecnica limit 1) sa "
            "where se.nombre = 'Ensayo' returning id",
            (cliente.id,),
        ).fetchone()[0]  # type: ignore[index]
        yield id_
        c.execute("delete from public.notificacion where destinatario like '%@prueba.bugalu.pe'")
        c.execute("delete from public.reserva where id = %s", (id_,))


async def test_la_bandeja_trae_la_reserva_de_los_avisos_con_evento_y_el_correo_sale_con_ics(
    bandeja: BandejaPostgres, configuracion: Configuracion, reserva_de_prueba: UUID
) -> None:
    datos = json.dumps({"id_reserva": str(reserva_de_prueba), "folio": "R-T", "inicio": INICIO,
                        "fin": FIN})  # fmt: skip
    confirmada = json.dumps({"id_reserva": str(reserva_de_prueba), "folio": "R-T", "hito": "al_reservar",
                             "monto": 50, "reserva_confirmada": True})  # fmt: skip
    with psycopg.connect(configuracion.url_base_datos_admin, autocommit=True) as c:
        ids = {
            tipo: c.execute(
                "insert into public.notificacion (tipo, destinatario, datos, creada_en) "
                "values (%s, 'evento@prueba.bugalu.pe', %s, now() - %s * interval '1 hour') "
                "returning id",
                (tipo, d, horas),
            ).fetchone()[0]  # type: ignore[index]
            for tipo, d, horas in (
                ("pago_aprobado", confirmada, 2),
                ("reserva_caducada", datos, 1),
                ("reserva_cancelada_estudio", datos, 0),
            )
        }
    enviador = EnviadorLento()
    async with bandeja.tomar(10, 5) as lote:
        assert all(p.creada_en is not None for p in lote.pendientes)
        assert set(lote.reservas) == {ids["pago_aprobado"], ids["reserva_cancelada_estudio"]}
        cancelacion = lote.reservas[ids["reserva_cancelada_estudio"]]
        assert (cancelacion.servicio, cancelacion.tiene_evento) == ("Ensayo", True)
    await enviar_pendientes(bandeja, enviador)
    por_tipo = {c.asunto: c for c in enviador.correos}
    metodos = sorted(c.evento.metodo for c in por_tipo.values() if c.evento)
    assert metodos == ["CANCEL", "REQUEST"]
    assert sum(1 for c in por_tipo.values() if c.evento is None) == 1  # reserva_caducada
