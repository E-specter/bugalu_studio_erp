# ruff: noqa: E501, F811 - cuerpos JSON de prueba y fixtures compartidas
"""RF-15 C1 contra el stack local: cerrar la asesoria (CA-12), notas y constancia (CA-13), ensayo (CA-15)."""

from collections.abc import Callable
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba
from tests.modulos.asesorias.infraestructura.conftest import Ejecutar, con
from tests.modulos.asesorias.infraestructura.test_api_agendar import _caducado, _con_alg
from tests.modulos.asesorias.infraestructura.test_api_politica import (  # noqa: F401 - fixtures
    ases,
    codigo,
    prof,
    sin_asesorias_cercanas,
)
from tests.modulos.reservas.infraestructura.conftest import franja, sala  # noqa: F401 - fixtures
from tests.modulos.reservas.infraestructura.test_api_reservar import (  # noqa: F401 - fixtures
    catalogo,
    dia,
    reservar,
)

pytestmark = pytest.mark.integracion

A = "/api/v1/asesorias"
R = "/api/v1/reservas"


@pytest.fixture(autouse=True)
def horario_pasado(prof: UsuarioDePrueba, sql: Ejecutar) -> None:
    """Las asesorias ya vencidas necesitan su bloque (la barrera de la base lo exige): [-100 h, -6 h)."""
    sql(
        "insert into public.horario_profesional (id_profesional, inicio, fin) "
        "values (%s, date_trunc('hour', now()) - interval '100 hours', date_trunc('hour', now()) - interval '6 hours')",
        prof.id,
    )


def cancelada(ases: Callable[..., str], sql: Ejecutar, cli: UsuarioDePrueba, desp: str) -> str:
    id_ = ases(cli, desp)
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = %s",
        UUID(id_),
    )
    return id_


async def realizada(c: AsyncClient, u: UsuarioDePrueba, id_: str) -> httpx.Response:
    return await c.post(f"{A}/{id_}/realizada", headers=con(u))


async def notas(c: AsyncClient, u: UsuarioDePrueba, id_: str, texto: object) -> httpx.Response:
    return await c.put(f"{A}/{id_}/notas", headers=con(u), json={"texto": texto})


async def constancia(c: AsyncClient, u: UsuarioDePrueba, id_: str) -> httpx.Response:
    return await c.get(f"{A}/{id_}/constancia", headers=con(u))


# --- CA-12: Realizada ---


async def test_realizada_desde_el_inicio_por_su_profesional(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    futura, pasada = ases(cliente_a, "4 hours"), ases(cliente_a, "-3 hours")
    r = await realizada(cliente, prof, futura)
    assert (r.status_code, codigo(r)) == (409, "antes_del_inicio")
    assert sql("select estado from public.reserva where id = %s", UUID(futura)) == [("confirmada",)]
    r = await realizada(cliente, prof, pasada)
    a = r.json()
    assert r.status_code == 200, r.text
    assert a["estado"] == "realizada" and a["constancia_disponible"] is True and a["realizada_en"]
    assert "cuotas" not in a and "pagado" not in a  # el profesional no ve dinero
    r = await realizada(cliente, prof, pasada)
    assert (r.status_code, codigo(r)) == (409, "no_aplicable")
    assert sql(
        "select count(*) from public.notificacion where tipo = 'asesoria_realizada' and datos ->> 'id_reserva' = %s",
        pasada,
    ) == [(1,)]


async def test_realizada_sin_limite_posterior_y_por_el_administrador(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    ases: Callable[..., str],
) -> None:
    vieja = ases(cliente_a, "-60 hours")
    r = await realizada(cliente, administrador, vieja)
    assert r.status_code == 200 and r.json()["estado"] == "realizada", r.text


async def test_realizada_solo_en_una_confirmada(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    for estado in ("pre_reservada", "cancelada", "no_asistio"):
        if estado == "cancelada":
            id_ = cancelada(ases, sql, cliente_a, "-20 hours")
        else:
            id_ = ases(cliente_a, "-8 hours" if estado == "pre_reservada" else "-10 hours", estado)
        r = await realizada(cliente, prof, id_)
        assert (r.status_code, codigo(r)) == (409, "no_aplicable"), estado


async def test_realizada_ajena_404_cliente_403_y_fila_intacta(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = ases(cliente_a, "-3 hours")
    for u in (cliente_b, otro_profesional, personal):
        r = await realizada(cliente, u, id_)
        assert r.status_code == 404, (u, r.text)
    r = await realizada(cliente, cliente_a, id_)
    assert r.status_code == 403
    r = await realizada(cliente, cliente_a, str(UUID(int=1)))
    assert r.status_code == 404
    assert sql("select estado from public.reserva where id = %s", UUID(id_)) == [("confirmada",)]
    assert sql(
        "select realizada_en, constancia from public.asesoria where id_reserva = %s", UUID(id_)
    ) == [(None, None)]


# --- CA-12: No asistio (ruta de RF-18, ventana de la asesoria) ---


async def test_no_asistio_en_pre_reservada_y_sin_limite_posterior(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    ases: Callable[..., str],
) -> None:
    sin_pagar, vieja, antes = (
        ases(cliente_a, "-8 hours", "pre_reservada"),
        ases(cliente_a, "-60 hours"),
        ases(cliente_a, "4 hours", "pre_reservada"),
    )
    r = await cliente.post(f"{R}/{antes}/inasistencia", headers=con(prof), json={})
    assert (r.status_code, codigo(r)) == (409, "tolerancia_no_cumplida")
    for id_ in (sin_pagar, vieja):
        r = await cliente.post(f"{R}/{id_}/inasistencia", headers=con(prof), json={})
        assert r.status_code == 200 and r.json()["estado"] == "no_asistio", r.text
    r = await realizada(cliente, prof, vieja)
    assert (r.status_code, codigo(r)) == (409, "no_aplicable")


# --- CA-13: notas ---


async def test_notas_del_profesional_y_del_administrador_nunca_al_cliente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    ases: Callable[..., str],
) -> None:
    id_ = ases(cliente_a, "4 hours")
    r = await notas(cliente, prof, id_, "Quiere mezclar su EP")
    assert r.status_code == 200 and r.json()["notas"] == "Quiere mezclar su EP", r.text
    r = await cliente.get(f"{A}/{id_}", headers=con(prof))
    assert r.json()["notas"] == "Quiere mezclar su EP"
    r = await cliente.get(f"{A}/{id_}", headers=con(cliente_a))
    assert "notas" not in r.json() and "Quiere mezclar" not in r.text
    r = await cliente.get(f"{A}/mias", headers=con(cliente_a))
    assert "Quiere mezclar" not in r.text
    r = await notas(cliente, administrador, id_, "Nota del administrador")
    assert r.status_code == 200 and r.json()["notas"] == "Nota del administrador"
    r = await notas(cliente, prof, id_, "")
    assert r.status_code == 200 and r.json()["notas"] == ""  # vacio borra
    r = await notas(cliente, prof, id_, "x" * 5000)
    assert r.status_code == 200


async def test_notas_422_409_y_ajenas(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = ases(cliente_a, "4 hours")
    for texto in ("x" * 5001, None, 5):
        r = await notas(cliente, prof, id_, texto)
        assert (r.status_code, codigo(r)) == (422, "datos_invalidos"), texto
    r = await cliente.put(f"{A}/{id_}/notas", headers=con(prof), json={})
    assert r.status_code == 422
    r = await notas(cliente, prof, cancelada(ases, sql, cliente_a, "-20 hours"), "tarde")
    assert (r.status_code, codigo(r)) == (409, "no_editable")
    for u, esperado in (
        (cliente_b, 404),
        (otro_profesional, 404),
        (personal, 404),
        (cliente_a, 403),
    ):
        r = await notas(cliente, u, id_, "intruso")
        assert r.status_code == esperado, (u, r.text)
        if esperado == 403:
            assert "cierra" not in r.json()["error"]["mensaje"]
    assert sql("select notas from public.asesoria where id_reserva = %s", UUID(id_)) == [(None,)]
    r = await notas(cliente, prof, str(UUID(int=1)), "x")
    assert r.status_code == 404


# --- CA-13: constancia ---


async def test_constancia_solo_a_su_dueno_su_profesional_y_el_administrador(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    ases: Callable[..., str],
) -> None:
    id_ = ases(cliente_a, "-3 hours")
    r = await constancia(cliente, cliente_a, id_)
    assert (r.status_code, codigo(r)) == (409, "constancia_no_disponible")
    assert (await realizada(cliente, prof, id_)).status_code == 200
    await notas(cliente, prof, id_, "No debe salir en la constancia")
    for u in (cliente_a, prof, administrador):
        r = await constancia(cliente, u, id_)
        c = r.json()
        assert r.status_code == 200, (u, r.text)
        assert set(c) == {
            "folio",
            "cliente",
            "profesional",
            "inicio",
            "fin",
            "duracion",
            "modalidad",
            "emitida_en",
        }
        assert c["folio"].startswith("A-") and c["duracion"] == 30 and c["modalidad"] == "virtual"
        assert set(c["cliente"]) <= {"nombre", "nombre_artistico"} and "nombre" in c["cliente"]
        assert set(c["profesional"]) <= {"nombre", "nombre_artistico", "especialidades"}
        assert c["profesional"]["especialidades"] and c["inicio"].endswith("-05:00")
        assert "No debe salir" not in r.text
    r = await cliente.get(f"{A}/{id_}", headers=con(cliente_a))
    assert r.json()["constancia_disponible"] is True
    for u in (cliente_b, otro_profesional, personal):
        r = await constancia(cliente, u, id_)
        assert r.status_code == 404, (u, r.text)
    r = await constancia(cliente, cliente_a, str(UUID(int=1)))
    assert r.status_code == 404


# --- CA-15: el ensayo ---


async def test_una_asesoria_confirmada_o_realizada_habilita_el_ensayo(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    ensayo = catalogo["Ensayo"]
    ases(cliente_b, "100 days")  # de otro cliente: no cuenta
    ases(cliente_a, "101 days", "pre_reservada")
    cancelada(ases, sql, cliente_a, "102 days")
    r = await reservar(cliente, cliente_a, sala, ensayo)
    assert r.status_code == 403 and codigo(r) == "ensayo_no_disponible", r.text
    previa = ases(cliente_a, "103 days")
    r = await reservar(cliente, cliente_a, sala, ensayo)
    assert r.status_code == 201, r.text
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = %s",
        UUID(previa),
    )
    r = await reservar(
        cliente, cliente_a, sala, ensayo, "2027-03-11T10:00:00-05:00", "2027-03-11T12:00:00-05:00"
    )
    assert r.status_code == 403 and codigo(r) == "ensayo_no_disponible", r.text
    ases(cliente_a, "-3 hours", "realizada")
    r = await reservar(
        cliente, cliente_a, sala, ensayo, "2027-03-11T10:00:00-05:00", "2027-03-11T12:00:00-05:00"
    )
    assert r.status_code == 201, r.text


# --- seguridad: 401 y 503 ---


async def test_401_con_token_manipulado_y_503_con_la_base_caida(
    monkeypatch: pytest.MonkeyPatch, cliente: AsyncClient, cliente_a: UsuarioDePrueba
) -> None:
    ruta = f"{A}/{UUID(int=1)}"
    rutas = [
        ("POST", f"{ruta}/realizada", None),
        ("PUT", f"{ruta}/notas", {"texto": "x"}),
        ("GET", f"{ruta}/constancia", None),
    ]
    for token in (_con_alg(cliente_a, "HS256"), _con_alg(cliente_a, "none"), _caducado(cliente_a)):
        for metodo, r_, c in rutas:
            r = await cliente.request(
                metodo, r_, json=c, headers={"Authorization": f"Bearer {token}"}
            )
            assert r.status_code == 401, (metodo, r_, r.status_code)
    for metodo, r_, c in rutas:
        assert (await cliente.request(metodo, r_, json=c)).status_code == 401
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c_,
    ):
        for metodo, r_, c in rutas:
            r = await c_.request(metodo, r_, json=c, headers=con(cliente_a))
            assert (r.status_code, codigo(r)) == (503, "base_de_datos_no_disponible"), (metodo, r_)
