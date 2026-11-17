"""RF-17 etapa A (CA-05, CA-07, CA-08): lo que exige `POST /reservas` y la aceptacion que deja."""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

RESERVAS = "/api/v1/reservas"
INICIO, FIN = "2027-04-14T10:00:00-05:00", "2027-04-14T12:00:00-05:00"


@pytest.fixture
def dia(franja: Callable[[str, str], str]) -> str:
    return franja("2027-04-14 08:00-05", "2027-04-14 20:00-05")


@pytest.fixture
def ensayo(sql: Ejecutar) -> str:
    return str(sql("select id from public.servicio where nombre = 'Grabación de voces'")[0][0])


async def _reservar(
    cliente: AsyncClient, usuario: UsuarioDePrueba, sala: str, servicio: str, **extra: Any
) -> Any:
    cuerpo = {
        "id_sala": sala,
        "id_servicio": servicio,
        "inicio": INICIO,
        "fin": FIN,
        "especialistas": [],
        "version_condiciones": "1.0.0",
        **extra,
    }
    cuerpo = {k: v for k, v in cuerpo.items() if v is not None}
    return await cliente.post(RESERVAS, json=cuerpo, headers=con(usuario))


def _codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


def _aceptaciones(sql: Ejecutar, u: UsuarioDePrueba, contexto: str) -> list[tuple[Any, ...]]:
    return sql(
        "select tipo, version, id_operacion from public.aceptacion "
        "where id_usuario = %s and contexto = %s",
        u.id,
        contexto,
    )


def _reservas(sql: Ejecutar, u: UsuarioDePrueba) -> int:
    return int(sql("select count(*) from public.reserva where id_cliente = %s", u.id)[0][0])


async def test_la_reserva_guarda_la_aceptacion_de_las_condiciones_en_la_misma_operacion(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    r = await _reservar(cliente, cliente_a, sala, ensayo)
    assert r.status_code == 201, r.text
    assert r.json()["version_condiciones"] == "1.0.0"
    assert [(t, v, str(o)) for t, v, o in _aceptaciones(sql, cliente_a, "reserva")] == [
        ("condiciones_contratacion", "1.0.0", r.json()["id"])
    ]
    leida = await cliente.get(f"{RESERVAS}/{r.json()['id']}", headers=con(cliente_a))
    assert leida.json()["version_condiciones"] == "1.0.0"


async def test_sin_version_de_condiciones_es_422_y_no_hay_reserva(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    cuerpo = {"id_sala": sala, "id_servicio": ensayo, "inicio": INICIO, "fin": FIN}
    r = await cliente.post(RESERVAS, json=cuerpo, headers=con(cliente_a))
    assert (r.status_code, _codigo(r), r.json()["error"]["detalles"]) == (
        422,
        "datos_invalidos",
        {"campo": "version_condiciones"},
    )
    assert (_reservas(sql, cliente_a), _aceptaciones(sql, cliente_a, "reserva")) == (0, [])


async def test_version_distinta_de_la_vigente_es_409_con_la_vigente_y_no_deja_nada(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    r = await _reservar(cliente, cliente_a, sala, ensayo, version_condiciones="0.9.0")
    assert (r.status_code, _codigo(r)) == (409, "texto_desactualizado")
    assert r.json()["error"]["detalles"]["vigente"]["version"] == "1.0.0"
    assert (_reservas(sql, cliente_a), _aceptaciones(sql, cliente_a, "reserva")) == (0, [])


async def test_perfil_incompleto_es_409_con_los_campos_que_faltan(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql(
        "update public.usuario set telefono = null, documento_tipo = null, documento_numero = null "
        "where id = %s",
        cliente_a.id,
    )
    r = await _reservar(cliente, cliente_a, sala, ensayo)
    assert (r.status_code, _codigo(r)) == (409, "perfil_incompleto")
    assert r.json()["error"]["detalles"] == {"campos": ["documento", "telefono"]}
    assert (_reservas(sql, cliente_a), _aceptaciones(sql, cliente_a, "reserva")) == (0, [])


async def test_registro_pendiente_o_version_mayor_de_terminos_es_409_reaceptacion(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql(
        "insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) "
        "values ('terminos_uso', '2.0.0', 'mayor', 'x', now())"
    )
    r = await _reservar(cliente, cliente_a, sala, ensayo)
    assert (r.status_code, _codigo(r)) == (409, "reaceptacion_requerida")
    assert r.json()["error"]["detalles"]["textos"] == [
        {
            "tipo": "terminos_uso",
            "version": "2.0.0",
            "contexto": "registro",
            "motivo": "version_mayor",
        }
    ]
    assert _reservas(sql, cliente_a) == 0
    # Aceptarla la destraba.
    aceptada = await cliente.post(
        "/api/v1/aceptaciones",
        headers=con(cliente_a),
        json={"contexto": "registro", "textos": [{"tipo": "terminos_uso", "version": "2.0.0"}]},
    )
    assert aceptada.status_code == 201
    assert (await _reservar(cliente, cliente_a, sala, ensayo)).status_code == 201


async def test_una_agrupacion_sin_la_declaracion_aceptada_no_reserva(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql(
        "update public.usuario set modalidad = 'agrupacion' where id = %s",
        cliente_a.id,
    )  # ahora debe ademas la declaracion
    r = await _reservar(cliente, cliente_a, sala, ensayo)
    assert (r.status_code, _codigo(r)) == (409, "reaceptacion_requerida")
    assert [t["tipo"] for t in r.json()["error"]["detalles"]["textos"]] == [
        "declaracion_agrupacion"
    ]


async def test_quien_se_declara_menor_no_reserva_en_la_etapa_a(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql("update public.usuario set es_menor = true where id = %s", cliente_a.id)
    r = await _reservar(cliente, cliente_a, sala, ensayo)
    assert (r.status_code, _codigo(r)) == (409, "autorizacion_menor_pendiente")
    assert (_reservas(sql, cliente_a), _aceptaciones(sql, cliente_a, "reserva")) == (0, [])


async def test_con_pendientes_se_ve_se_paga_y_se_cancela_lo_existente(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    creada = await _reservar(cliente, cliente_a, sala, ensayo)
    id_reserva = creada.json()["id"]
    sql(
        "insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) "
        "values ('terminos_uso', '2.0.0', 'mayor', 'x', now())"
    )
    assert (
        await cliente.get(f"{RESERVAS}/{id_reserva}", headers=con(cliente_a))
    ).status_code == 200
    assert (await cliente.get(f"{RESERVAS}/mias", headers=con(cliente_a))).status_code == 200
    cancelada = await cliente.post(f"{RESERVAS}/{id_reserva}/cancelar", headers=con(cliente_a))
    assert cancelada.status_code in (200, 204), cancelada.text


async def test_si_la_reserva_falla_no_queda_aceptacion(
    cliente: AsyncClient,
    sala: str,
    ensayo: str,
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    # Sin franja publicada la reserva falla (fuera_de_franja) y la aceptacion no debe quedar.
    r = await _reservar(cliente, cliente_a, sala, ensayo)
    assert r.status_code == 422
    assert _aceptaciones(sql, cliente_a, "reserva") == []


@pytest.mark.parametrize("sesion", ["sin", "malo"])
async def test_401_sin_sesion(cliente: AsyncClient, sala: str, ensayo: str, sesion: str) -> None:
    cuerpo = {
        "id_sala": sala,
        "id_servicio": ensayo,
        "inicio": INICIO,
        "fin": FIN,
        "version_condiciones": "1.0.0",
    }
    cabeceras = {} if sesion == "sin" else {"Authorization": "Bearer x.y.z"}
    r = await cliente.post(RESERVAS, json=cuerpo, headers=cabeceras)
    assert r.status_code == 401
