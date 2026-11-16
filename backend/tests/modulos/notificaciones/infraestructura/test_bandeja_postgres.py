"""Bandeja `notificacion` con el rol bugalu_api real: lote exclusivo, marcas, tope de intentos."""

import asyncio
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

pytestmark = pytest.mark.integracion

DATOS = (
    '{"folio": "BG-T", "inicio": "2027-03-10T15:00:00+00:00", "fin": "2027-03-10T17:00:00+00:00"}'
)
Poner = Callable[..., UUID]


class EnviadorLento:
    def __init__(self, falla: bool = False) -> None:
        self.enviados: list[str] = []
        self.falla = falla

    async def enviar(self, correo: Correo) -> None:
        await asyncio.sleep(0.2)
        if self.falla:
            raise ConnectionRefusedError("sin servidor")
        self.enviados.append(correo.destinatario)


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
