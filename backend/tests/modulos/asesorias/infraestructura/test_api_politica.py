# ruff: noqa: E501, F811 - cuerpos JSON de prueba y fixtures compartidas
"""RF-15 B2 contra el stack local: la politica de RF-18 (rutas de /reservas) con asesorias."""

from collections.abc import Callable, Iterator
from typing import Any
from uuid import UUID

import httpx
import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from psycopg.types.json import Jsonb

from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba
from tests.modulos.asesorias.infraestructura.conftest import Ejecutar, con
from tests.modulos.asesorias.infraestructura.test_api_agendar import _caducado, _con_alg
from tests.modulos.asesorias.infraestructura.test_api_asesorias import (
    PROF,
    crear_especialidad,
    publicar,
)

pytestmark = pytest.mark.integracion

PRECIO = {
    "total": "50.00",
    "impuesto": {
        "nombre": "IGV",
        "porcentaje": "18.00",
        "incluido": True,
        "base": "42.37",
        "monto": "7.63",
    },
}
R = "/api/v1/reservas"
H = "date_trunc('hour', now())"


def codigo(r: httpx.Response) -> str:
    return str(r.json()["error"]["codigo"])


@pytest.fixture(autouse=True)
def sin_asesorias_cercanas(configuracion: Configuracion) -> Iterator[None]:
    """Estas pruebas crean asesorias cercanas por SQL (la limpieza de 2027 no las alcanza)."""
    yield
    with psycopg.connect(configuracion.url_base_datos_admin, autocommit=True) as c:
        c.execute(
            "delete from public.reserva where tipo = 'asesoria' and id_cliente in "
            "(select id from auth.users where email like '%@prueba.bugalu.pe')"
        )


@pytest.fixture
async def prof(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
    sql: Ejecutar,
) -> UsuarioDePrueba:
    """Profesional publicado con un solo bloque [hora actual - 6 h, + 120 dias): 30 min = 50.00."""
    await publicar(
        cliente,
        administrador,
        profesional,
        await crear_especialidad(cliente, administrador, nombre_especialidad()),
    )
    sql(
        f"insert into public.horario_profesional (id_profesional, inicio, fin) "
        f"values (%s, {H} - interval '6 hours', {H} + interval '120 days')",
        profesional.id,
    )
    return profesional


@pytest.fixture
def ases(sql: Ejecutar, prof: UsuarioDePrueba) -> Callable[..., str]:
    """Una asesoria de 30 min con su cuota pagada: `desplazamiento` respecto de la hora actual."""

    def crear(
        cli: UsuarioDePrueba,
        desplazamiento: str,
        estado: str = "confirmada",
        profesional: UsuarioDePrueba | None = None,
    ) -> str:
        id_ = str(
            sql(
                "insert into public.reserva (tipo, id_cliente, id_profesional, inicio, fin, total, estado, vence_pago, precio) "
                f"values ('asesoria', %s, %s, {H} + %s::interval, {H} + %s::interval + interval '30 minutes', 50, %s, now() + interval '300 days', %s) returning id",
                cli.id,
                (profesional or prof).id,
                desplazamiento,
                desplazamiento,
                estado,
                Jsonb(PRECIO),
            )[0][0]
        )
        sql("insert into public.asesoria (id_reserva, modalidad) values (%s, 'virtual')", UUID(id_))
        sql(
            "insert into public.cuota (id_reserva, hito, monto, estado, pagado) values (%s, 'al_reservar', 50, 'pagada', 50)",
            UUID(id_),
        )
        return id_

    return crear


async def post(
    c: AsyncClient, u: UsuarioDePrueba, ruta: str, cuerpo: dict[str, Any] | None = None
) -> httpx.Response:
    return await c.post(f"{R}/{ruta}", headers=con(u), json=cuerpo if cuerpo is not None else {})


# --- niveles 1, 2 y 3 ---


async def test_vista_previa_y_cancelacion_en_los_tres_niveles(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, ases: Callable[..., str], sql: Ejecutar
) -> None:
    n1, n2, n3 = (
        ases(cliente_a, "100 days"),
        ases(cliente_a, "30 hours"),
        ases(cliente_a, "5 hours"),
    )
    for id_, nivel, retenido, credito in (
        (n1, 1, "0.00", "50.00"),
        (n2, 2, "12.50", "37.50"),
        (n3, 3, "50.00", "0.00"),
    ):
        v = await cliente.get(f"{R}/{id_}/cancelacion", headers=con(cliente_a))
        assert v.status_code == 200 and (
            v.json()["nivel"],
            v.json()["retenido"],
            v.json()["credito"],
        ) == (nivel, retenido, credito), v.text
    r = await post(cliente, cliente_a, f"{n2}/cancelar", {"nivel_esperado": 1})
    assert (r.status_code, codigo(r)) == (409, "nivel_cambiado") and r.json()["error"]["detalles"][
        "nivel"
    ] == 2
    for id_, nivel in ((n1, 1), (n2, 2), (n3, 3)):
        r = await post(cliente, cliente_a, f"{id_}/cancelar", {"nivel_esperado": nivel})
        a = r.json()
        assert r.status_code == 200 and a["tipo"] == "asesoria" and a["estado"] == "cancelada", (
            r.text
        )
        assert a["cancelacion"]["nivel"] == nivel and "profesional" in a and "sala" not in a
    assert sql("select tipo, saldo from public.credito where id_reserva = %s", UUID(n1)) == [
        ("nivel_1", 50)
    ]
    assert sql("select tipo, saldo from public.credito where id_reserva = %s", UUID(n2)) == [
        ("nivel_2", 37.5)
    ]


async def test_el_cliente_no_cancela_tras_el_inicio_y_el_estudio_si_con_eleccion(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    ases: Callable[..., str],
) -> None:
    empezada = ases(cliente_a, "0 hours")
    r = await post(cliente, cliente_a, f"{empezada}/cancelar", {"nivel_esperado": 3})
    assert (r.status_code, codigo(r)) == (409, "no_cancelable")
    r = await cliente.get(f"{R}/{empezada}/cancelacion", headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "no_cancelable")
    r = await post(cliente, administrador, f"{empezada}/cancelar", {"por": "estudio"})
    assert (r.status_code, codigo(r)) == (422, "nota_requerida")
    r = await post(
        cliente,
        administrador,
        f"{empezada}/cancelar",
        {"por": "estudio", "nota": "No vino el profesional"},
    )
    assert r.status_code == 200 and r.json()["eleccion_estudio"] == "pendiente", r.text
    r = await post(cliente, cliente_b, f"{empezada}/eleccion-estudio", {"opcion": "devolucion"})
    assert r.status_code == 404
    r = await post(cliente, cliente_a, f"{empezada}/eleccion-estudio", {"opcion": "devolucion"})
    a = r.json()
    assert r.status_code == 200 and a["eleccion_estudio"] == "devolucion", r.text
    assert (
        a["devolucion"]["tipo"],
        a["devolucion"]["monto_aprobado"],
        a["devolucion"]["reserva"]["tipo"],
    ) == ("estudio", "50.00", "asesoria")


async def test_tras_la_cancelacion_del_estudio_se_reprograma_sin_costo_con_el_mismo_profesional(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    ases: Callable[..., str],
) -> None:
    id_ = ases(cliente_a, "0 hours")
    await post(
        cliente,
        administrador,
        f"{id_}/cancelar",
        {"por": "estudio", "nota": "No vino el profesional"},
    )
    from datetime import UTC, datetime, timedelta

    inicio = (datetime.now(UTC) + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
    nuevo = {"inicio": inicio.isoformat()}
    r = await post(cliente, cliente_a, f"{id_}/reprogramar/simular", nuevo)
    assert r.status_code == 200 and (
        r.json()["nivel"],
        r.json()["saldo"],
        r.json()["precio"]["total"],
    ) == (None, "0.00", "50.00"), r.text
    r = await post(cliente, cliente_a, f"{id_}/reprogramar", nuevo)
    a = r.json()
    assert (
        r.status_code == 200
        and a["estado"] == "confirmada"
        and a["eleccion_estudio"] == "reprogramada"
    ), r.text
    assert a["reprogramaciones"][0].get("nivel") is None and a["precio"]["total"] == "50.00"


# --- reprogramar ---


async def test_reprogramar_nivel_2_crea_la_cuota_al_terminar_del_25_por_ciento(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    ases: Callable[..., str],
    prof: UsuarioDePrueba,
) -> None:
    from datetime import UTC, datetime, timedelta

    id_ = ases(cliente_a, "30 hours")
    otra = ases(cliente_a, "60 hours")
    base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    nuevo = {"inicio": (base + timedelta(days=10)).isoformat()}
    r = await post(cliente, cliente_a, f"{id_}/reprogramar/simular", nuevo)
    assert r.status_code == 200 and (
        r.json()["nivel"],
        r.json()["penalizacion"],
        r.json()["saldo"],
        r.json()["credito"],
    ) == (2, "12.50", "12.50", "0.00"), r.text
    assert r.json()["precio"]["total"] == "50.00"
    r = await post(
        cliente,
        cliente_a,
        f"{id_}/reprogramar",
        {**nuevo, "nivel_esperado": 1, "total_esperado": "50.00"},
    )
    assert (r.status_code, codigo(r)) == (409, "nivel_cambiado")
    r = await post(
        cliente,
        cliente_a,
        f"{id_}/reprogramar",
        {**nuevo, "nivel_esperado": 2, "total_esperado": "60.00"},
    )
    assert (r.status_code, codigo(r)) == (409, "precio_cambiado")
    r = await post(
        cliente,
        cliente_a,
        f"{id_}/reprogramar",
        {**nuevo, "nivel_esperado": 2, "total_esperado": "50.00"},
    )
    a = r.json()
    assert r.status_code == 200 and a["estado"] == "confirmada" and a["duracion"] == 30, r.text
    cuotas = {c["hito"]: c for c in a["cuotas"]}
    assert (
        cuotas["al_terminar"]["monto"],
        cuotas["al_terminar"]["estado"],
        cuotas["al_terminar"]["pagable"],
    ) == ("12.50", "pendiente", True)
    assert a["reprogramaciones"][0]["penalizacion"] == "12.50" and a["precio"]["total"] == "50.00"
    # errores: fuera de horario, ocupado, y el limite de anticipacion
    lejos = {
        "inicio": (base + timedelta(days=200)).isoformat(),
        "nivel_esperado": 1,
        "total_esperado": "50.00",
    }
    r = await post(cliente, cliente_a, f"{otra}/reprogramar", {**lejos, "nivel_esperado": 1})
    assert r.status_code == 422, r.text
    ocupado = {
        "inicio": (base + timedelta(days=10)).isoformat(),
        "nivel_esperado": 1,
        "total_esperado": "50.00",
    }
    r = await post(cliente, cliente_a, f"{otra}/reprogramar", ocupado)
    assert (r.status_code, codigo(r)) == (409, "horario_no_disponible")


async def test_reprogramar_fuera_del_horario_del_profesional_es_422(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
    prof: UsuarioDePrueba,
) -> None:
    from datetime import UTC, datetime, timedelta

    id_ = ases(cliente_a, "100 hours")
    sql("update public.parametro set valor = 400 where clave = 'anticipacion_maxima_semanas'")
    inicio = (datetime.now(UTC) + timedelta(days=150)).replace(minute=0, second=0, microsecond=0)
    r = await post(
        cliente,
        cliente_a,
        f"{id_}/reprogramar",
        {"inicio": inicio.isoformat(), "nivel_esperado": 1, "total_esperado": "50.00"},
    )
    assert (r.status_code, codigo(r)) == (422, "fuera_de_horario")


# --- excepcion, sin devolucion e inasistencia ---


async def test_excepcion_credito_sin_devolucion_en_dinero(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = ases(cliente_a, "5 hours")
    await post(cliente, cliente_a, f"{id_}/cancelar", {"nivel_esperado": 3})
    r = await post(
        cliente, administrador, f"{id_}/excepcion", {"motivo": "Emergencia medica del cliente"}
    )
    a = r.json()
    assert (
        r.status_code == 200 and a["tipo"] == "asesoria" and a["cancelacion"]["excepcion"]["motivo"]
    ), r.text
    [(id_credito, tipo)] = sql(
        "select id, tipo from public.credito where id_reserva = %s", UUID(id_)
    )
    assert tipo == "excepcion"
    r = await cliente.post(
        f"/api/v1/creditos/{id_credito}/devolucion",
        headers=con(cliente_a),
        json={"motivo": "Quiero mi dinero de vuelta"},
    )
    assert (r.status_code, codigo(r)) == (409, "devolucion_no_permitida")
    r = await post(
        cliente, cliente_a, f"{id_}/excepcion", {"motivo": "Emergencia medica del cliente"}
    )
    assert r.status_code == 403


async def test_inasistencia_por_su_profesional_o_el_administrador(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    pasada, otra, futura = (
        ases(cliente_a, "-3 hours"),
        ases(cliente_a, "-2 hours"),
        ases(cliente_a, "4 hours"),
    )
    r = await post(cliente, prof, f"{futura}/inasistencia")
    assert (r.status_code, codigo(r)) == (409, "tolerancia_no_cumplida")
    for u, esperado in ((personal, 404), (otro_profesional, 404), (cliente_a, 403)):
        r = await post(cliente, u, f"{pasada}/inasistencia")
        assert r.status_code == esperado, (u, r.text)
    assert sql("select estado from public.reserva where id = %s", UUID(pasada)) == [
        ("confirmada",)
    ]  # intacta
    r = await post(cliente, prof, f"{pasada}/inasistencia")
    a = r.json()
    assert r.status_code == 200 and a["estado"] == "no_asistio", r.text
    assert (
        "cuotas" not in a and "pagado" not in a and "cancelacion" not in a
    )  # el profesional no ve dinero
    r = await post(cliente, prof, f"{pasada}/inasistencia")
    assert (r.status_code, codigo(r)) == (409, "no_aplicable")
    r = await post(cliente, administrador, f"{otra}/inasistencia")
    assert r.status_code == 200 and r.json()["cancelacion"]["retenido"] == "50.00"


# --- seguridad ---


async def test_ajena_404_con_fila_intacta_profesional_403_y_sala_intacta(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = ases(cliente_a, "100 days")
    nuevo = {"inicio": "2027-03-10T10:00:00-05:00"}
    rutas = [
        ("GET", f"{R}/{id_}/cancelacion", None),
        ("POST", f"{R}/{id_}/cancelar", {"nivel_esperado": 1}),
        ("POST", f"{R}/{id_}/reprogramar/simular", nuevo),
        (
            "POST",
            f"{R}/{id_}/reprogramar",
            {**nuevo, "nivel_esperado": 1, "total_esperado": "50.00"},
        ),
        ("POST", f"{R}/{id_}/eleccion-estudio", {"opcion": "devolucion"}),
    ]
    for metodo, ruta, c in rutas:
        for u in (cliente_b, personal):
            r = await cliente.request(metodo, ruta, json=c, headers=con(u))
            assert r.status_code == 404, (metodo, ruta, r.status_code, r.text)
        r = await cliente.request(metodo, ruta, json=c, headers=con(prof))
        assert r.status_code == 403, (metodo, ruta, r.status_code)
    assert (
        sql("select estado, inicio from public.reserva where id = %s", UUID(id_))[0][0]
        == "confirmada"
    )
    # la sala sigue igual: una reserva inexistente de sala responde como antes
    r = await cliente.get(f"{R}/{UUID(int=1)}/cancelacion", headers=con(cliente_a))
    assert r.status_code == 404


async def test_401_con_token_manipulado_y_503_con_la_base_caida(
    monkeypatch: pytest.MonkeyPatch, cliente: AsyncClient, cliente_a: UsuarioDePrueba
) -> None:
    rutas = [
        ("GET", f"{R}/{UUID(int=1)}/cancelacion", None),
        ("POST", f"{R}/{UUID(int=1)}/cancelar", {}),
        ("POST", f"{R}/{UUID(int=1)}/inasistencia", None),
        ("POST", f"{R}/{UUID(int=1)}/excepcion", {"motivo": "Un motivo largo"}),
        ("POST", f"{R}/{UUID(int=1)}/reprogramar/simular", {"inicio": "2027-03-10T10:00:00-05:00"}),
        ("POST", f"{R}/{UUID(int=1)}/reprogramar", {"inicio": "2027-03-10T10:00:00-05:00"}),
        ("POST", f"{R}/{UUID(int=1)}/eleccion-estudio", {"opcion": "devolucion"}),
    ]
    for token in (_con_alg(cliente_a, "HS256"), _con_alg(cliente_a, "none"), _caducado(cliente_a)):
        for metodo, ruta, c in rutas:
            r = await cliente.request(
                metodo, ruta, json=c, headers={"Authorization": f"Bearer {token}"}
            )
            assert r.status_code == 401, (metodo, ruta, r.status_code)
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c_,
    ):
        for metodo, ruta, c in rutas:
            r = await c_.request(metodo, ruta, json=c, headers=con(cliente_a))
            assert (r.status_code, codigo(r)) == (503, "base_de_datos_no_disponible"), (
                metodo,
                ruta,
            )


# --- horario_con_asesorias y profesional_con_asesorias ---


async def test_409_horario_con_asesorias_y_profesional_con_asesorias(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    prof: UsuarioDePrueba,
    ases: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = ases(cliente_a, "100 days")
    [(id_horario,)] = sql(
        "select id from public.horario_profesional where id_profesional = %s", prof.id
    )
    r = await cliente.delete(f"{PROF}/{prof.id}/horarios/{id_horario}", headers=con(prof))
    assert (r.status_code, codigo(r)) == (409, "horario_con_asesorias")
    vivas = r.json()["error"]["detalles"]["asesorias"]
    assert (
        [v["id"] for v in vivas] == [id_]
        and vivas[0]["folio"].startswith("A-")
        and vivas[0]["inicio"]
    )
    r = await cliente.patch(
        f"/api/v1/usuarios/{prof.id}", headers=con(administrador), json={"rol": "cliente"}
    )
    assert (r.status_code, codigo(r)) == (409, "profesional_con_asesorias")
    assert r.json()["error"]["detalles"]["asesorias"][0]["id"] == id_
    assert sql("select rol from public.usuario where id = %s", prof.id) == [("profesional",)]
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = %s",
        UUID(id_),
    )
    r = await cliente.delete(f"{PROF}/{prof.id}/horarios/{id_horario}", headers=con(prof))
    assert r.status_code == 204
    r = await cliente.patch(
        f"/api/v1/usuarios/{prof.id}", headers=con(administrador), json={"rol": "cliente"}
    )
    assert r.status_code == 200


async def test_el_profesional_no_lee_el_dinero_de_reserva_por_sql(
    configuracion: Configuracion,
    prof: UsuarioDePrueba,
    cliente_a: UsuarioDePrueba,
    ases: Callable[..., str],
) -> None:
    ases(cliente_a, "100 days")
    with psycopg.connect(configuracion.url_base_datos, autocommit=False) as c:
        c.execute("set local role authenticated")
        c.execute(
            "select set_config('request.jwt.claims', %s, true)",
            (f'{{"sub":"{prof.id}","role":"authenticated"}}',),
        )
        assert c.execute("select count(*) from public.reserva").fetchone() == (0,)
        assert c.execute(
            "select total, retenido, credito_generado from public.asesoria_vista"
        ).fetchall() == [(None, None, None)]
