"""RF-18 (parte A): creditos, su uso al pagar (CA-05, CA-06) y devoluciones (CA-07), RLS real."""

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.test_api_pagos import pagar
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

PRECIO = '{"lineas": [], "recargos": [], "total": "200", "anticipo": "100"}'
CAMPOS_CREDITO = {"id", "monto", "saldo", "vence", "estado", "tipo", "origen"}
MOTIVO = {"motivo": "Cambie de planes y necesito el dinero"}


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


@pytest.fixture
def reserva_para_pagar(
    sql: Ejecutar, reservar: Callable[..., str]
) -> Callable[..., tuple[str, str]]:
    """Reserva pre_reservada (2027) con cuota `al_reservar` de 100; devuelve (reserva, cuota)."""
    dias = iter(range(1, 28))

    def crear(usuario: UsuarioDePrueba, estado: str = "pre_reservada") -> tuple[str, str]:
        dia = next(dias)
        id_ = reservar(
            usuario.id,
            f"2027-08-{dia:02d}T10:00:00-05:00",
            f"2027-08-{dia:02d}T12:00:00-05:00",
            estado,
        )
        sql(
            "update public.reserva set precio = %s::jsonb, total = 200 where id = %s",
            PRECIO,
            UUID(id_),
        )
        cuota = sql(
            "insert into public.cuota (id_reserva, hito, monto) values (%s, 'al_reservar', 100) "
            "returning id",
            UUID(id_),
        )[0][0]
        return id_, str(cuota)

    return crear


@pytest.fixture
def credito(sql: Ejecutar, reservar: Callable[..., str]) -> Callable[..., str]:
    """Credito de origen una reserva cancelada (2027) del cliente."""
    origenes: dict[UUID, str] = {}

    def crear(
        usuario: UsuarioDePrueba, monto: str = "100.00", tipo: str = "nivel_1", dias: int = 10
    ) -> str:
        if usuario.id not in origenes:
            n = len(origenes) + 1
            origenes[usuario.id] = reservar(
                usuario.id,
                f"2027-02-{n:02d}T10:00:00-05:00",
                f"2027-02-{n:02d}T11:00:00-05:00",
                "cancelada",
            )
        return str(
            sql(
                "insert into public.credito (id_cliente, id_reserva, tipo, monto, saldo, vence) "
                "values (%s, %s, %s, %s, %s, now() + %s * interval '1 day') returning id",
                usuario.id,
                UUID(origenes[usuario.id]),
                tipo,
                monto,
                monto,
                dias,
            )[0][0]
        )

    return crear


async def test_listar_mis_creditos_solo_los_propios_con_su_forma(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    credito: Callable[..., str],
) -> None:
    lejano = credito(cliente_a, "10.00", dias=20)
    cercano = credito(cliente_a, "40.00", dias=5)
    ajeno = credito(cliente_b)
    r = await cliente.get("/api/v1/creditos", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    assert [c["id"] for c in r.json()] == [cercano, lejano]  # vigentes por vencimiento
    primero = r.json()[0]
    assert set(primero) >= CAMPOS_CREDITO and "devolucion" not in primero
    assert (primero["monto"], primero["saldo"], primero["estado"], primero["tipo"]) == (
        "40.00",
        "40.00",
        "vigente",
        "nivel_1",
    )
    assert primero["origen"]["folio"].startswith("R-")
    assert ajeno not in [c["id"] for c in r.json()]


async def test_listar_creditos_permisos(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    credito: Callable[..., str],
) -> None:
    mio = credito(cliente_a)
    url = "/api/v1/creditos"
    assert (await cliente.get(url)).status_code == 401
    assert (await cliente.get(url, headers=con(personal))).status_code == 403
    ajeno = {"id_cliente": str(cliente_b.id)}
    assert (await cliente.get(url, params=ajeno, headers=con(cliente_a))).status_code == 403
    propio = {"id_cliente": str(cliente_a.id)}
    r = await cliente.get(url, params=propio, headers=con(cliente_a))
    assert [c["id"] for c in r.json()] == [mio]
    r = await cliente.get(url, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    r = await cliente.get(url, params=propio, headers=con(administrador))
    assert [c["id"] for c in r.json()] == [mio]


async def test_un_credito_vencido_sin_marcar_se_ve_vencido(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, credito: Callable[..., str]
) -> None:
    credito(cliente_a, dias=-1)
    r = await cliente.get("/api/v1/creditos", headers=con(cliente_a))
    assert [c["estado"] for c in r.json()] == ["vencido"]


async def test_usar_credito_parcial_y_total_confirma_la_reserva(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    credito: Callable[..., str],
    reserva_para_pagar: Callable[..., tuple[str, str]],
    sql: Ejecutar,
) -> None:
    corto = credito(cliente_a, "30.00", dias=3)
    largo = credito(cliente_a, "100.00", dias=9)
    _, cuota = reserva_para_pagar(cliente_a)
    url = f"/api/v1/cuotas/{cuota}/credito"
    r = await cliente.post(url, json={"monto": "30.00"}, headers=con(cliente_a))
    assert r.status_code == 200, r.text
    c = r.json()["cuotas"][0]
    assert (c["estado"], c["pagado"], c["pagable"]) == ("pendiente", "30.00", True)
    assert r.json()["estado"] == "pre_reservada" and r.json()["pagado"] == "30.00"
    cuerpo = {"monto": "70.00", "id_credito": largo}
    r = await cliente.post(url, json=cuerpo, headers=con(cliente_a))
    assert r.status_code == 200, r.text
    assert (r.json()["estado"], r.json()["cuotas"][0]["estado"]) == ("confirmada", "pagada")
    saldos = {str(i): s for i, s in sql("select id, saldo from public.credito")}
    assert (saldos[corto], saldos[largo]) == (0, 30)  # primero el que vence antes


async def test_el_pago_con_captura_tras_un_credito_parcial_exige_el_monto_restante(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    credito: Callable[..., str],
    reserva_para_pagar: Callable[..., tuple[str, str]],
    sql: Ejecutar,
) -> None:
    credito(cliente_a, "30.00")
    _, cuota = reserva_para_pagar(cliente_a)
    url = f"/api/v1/cuotas/{cuota}/credito"
    await cliente.post(url, json={"monto": "30.00"}, headers=con(cliente_a))
    sql("update public.instruccion_pago set texto = 'x', activo = true where metodo = 'yape'")
    r = await pagar(cliente, cliente_a, cuota, monto="100.00")
    assert (r.status_code, codigo(r)) == (422, "monto_invalido")
    assert (await pagar(cliente, cliente_a, cuota, monto="70.00")).status_code == 201


async def test_errores_de_usar_credito(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    credito: Callable[..., str],
    reserva_para_pagar: Callable[..., tuple[str, str]],
    sql: Ejecutar,
) -> None:
    mio = credito(cliente_a, "20.00")
    ajeno = credito(cliente_b)
    reserva, cuota = reserva_para_pagar(cliente_a)
    url = f"/api/v1/cuotas/{cuota}/credito"
    r = await cliente.post(url, json={"monto": "50.00"}, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "credito_insuficiente")
    for monto in ("0", "-5", "100.01", "10.005"):
        r = await cliente.post(url, json={"monto": monto}, headers=con(cliente_a))
        assert (r.status_code, codigo(r)) == (422, "monto_invalido"), monto
    cuerpo = {"monto": "10.00", "id_credito": ajeno}
    assert (await cliente.post(url, json=cuerpo, headers=con(cliente_a))).status_code == 404
    assert (await cliente.post(url, json={"monto": "10.00"})).status_code == 401
    assert (await cliente.post(url, json={}, headers=con(cliente_a))).status_code == 422
    for quien in (personal, administrador):
        r = await cliente.post(url, json={"monto": "10.00"}, headers=con(quien))
        assert r.status_code == 403
    r = await cliente.post(url, json={"monto": "10.00"}, headers=con(cliente_b))
    assert r.status_code == 404
    assert sql("select saldo from public.credito where id = %s", UUID(mio)) == [(20,)]
    assert sql("select pagado from public.cuota where id = %s", UUID(cuota)) == [(0,)]
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' "
        "where id = %s",
        UUID(reserva),
    )
    r = await cliente.post(url, json={"monto": "10.00"}, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "no_pagable")
    sql("update public.cuota set estado = 'pagada', pagado = 100 where id = %s", UUID(cuota))
    r = await cliente.post(url, json={"monto": "10.00"}, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "cuota_pagada")


async def test_dos_aplicaciones_simultaneas_no_dejan_saldo_negativo_ni_doble_uso(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    credito: Callable[..., str],
    reserva_para_pagar: Callable[..., tuple[str, str]],
    sql: Ejecutar,
) -> None:
    id_credito = credito(cliente_a, "100.00")
    _, c1 = reserva_para_pagar(cliente_a)
    _, c2 = reserva_para_pagar(cliente_a)
    resultados = await asyncio.gather(
        *(
            cliente.post(
                f"/api/v1/cuotas/{c}/credito", json={"monto": "100.00"}, headers=con(cliente_a)
            )
            for c in (c1, c2)
        )
    )
    assert sorted(r.status_code for r in resultados) == [200, 409]
    estado = sql("select saldo, estado from public.credito where id = %s", UUID(id_credito))
    assert estado == [(0, "agotado")]
    assert sql("select sum(monto) from public.aplicacion_credito") == [(100,)]


async def test_pedir_devolucion_decidir_y_marcarla_realizada(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    credito: Callable[..., str],
) -> None:
    id_credito = credito(cliente_a, "100.00")
    url = f"/api/v1/creditos/{id_credito}/devolucion"
    assert (await cliente.post(url, json=MOTIVO)).status_code == 401
    assert (await cliente.post(url, json=MOTIVO, headers=con(cliente_b))).status_code == 404
    assert (await cliente.post(url, json=MOTIVO, headers=con(administrador))).status_code == 403
    r = await cliente.post(url, json={"motivo": "corto"}, headers=con(cliente_a))
    assert r.status_code == 422
    r = await cliente.post(url, json=MOTIVO, headers=con(cliente_a))
    assert r.status_code == 201, r.text
    d = r.json()
    assert (d["estado"], d["tipo"], d["monto_solicitado"], d["id_credito"]) == (
        "pendiente",
        "nivel_1",
        "100.00",
        id_credito,
    )
    assert d["cliente"]["id"] == str(cliente_a.id) and d["folio"].startswith("R-")
    r = await cliente.post(url, json=MOTIVO, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "devolucion_pendiente")
    mios = await cliente.get("/api/v1/creditos", headers=con(cliente_a))
    assert mios.json()[0]["devolucion"]["id"] == d["id"]
    # Cola y lectura de una.
    lista = "/api/v1/devoluciones"
    assert (await cliente.get(lista, headers=con(cliente_a))).status_code == 403
    assert (await cliente.get(lista, headers=con(personal))).status_code == 403
    cola = await cliente.get(lista, params={"estado": "pendiente"}, headers=con(administrador))
    assert d["id"] in [x["id"] for x in cola.json()]
    r = await cliente.get(lista, params={"estado": "otra"}, headers=con(administrador))
    assert r.status_code == 422
    uno = f"{lista}/{d['id']}"
    assert (await cliente.get(uno, headers=con(cliente_a))).status_code == 200
    assert (await cliente.get(uno, headers=con(administrador))).status_code == 200
    assert (await cliente.get(uno, headers=con(cliente_b))).status_code == 404
    assert (await cliente.get(uno, headers=con(personal))).status_code == 403
    decidir = f"{uno}/decidir"
    r = await cliente.post(decidir, json={"decision": "total"}, headers=con(cliente_a))
    assert r.status_code == 403
    parcial = {"decision": "parcial", "motivo": "Se devuelve una parte"}
    for cuerpo, cod in (
        (parcial, "monto_invalido"),
        ({**parcial, "monto": "500"}, "monto_invalido"),
        ({"decision": "rechazo"}, "motivo_requerido"),
        ({"decision": "parcial", "monto": "30", "motivo": "corto"}, "motivo_requerido"),
    ):
        r = await cliente.post(decidir, json=cuerpo, headers=con(administrador))
        assert (r.status_code, codigo(r)) == (422, cod), cuerpo
    r = await cliente.post(decidir, json={**parcial, "monto": "30.00"}, headers=con(administrador))
    assert r.status_code == 200, r.text
    assert (r.json()["estado"], r.json()["monto_aprobado"]) == ("aprobada", "30.00")
    r = await cliente.post(decidir, json={"decision": "total"}, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (409, "devolucion_decidida")
    c = (await cliente.get("/api/v1/creditos", headers=con(cliente_a))).json()[0]
    assert c["saldo"] == "70.00" and c["estado"] == "vigente"
    realizada = f"{uno}/realizada"
    nota = {"nota": "Yape 998877"}
    assert (await cliente.post(realizada, json=nota, headers=con(cliente_a))).status_code == 403
    r = await cliente.post(realizada, json={"nota": " "}, headers=con(administrador))
    assert r.status_code == 422
    r = await cliente.post(realizada, json=nota, headers=con(administrador))
    assert (r.status_code, r.json()["estado"], r.json()["nota_realizada"]) == (
        200,
        "realizada",
        "Yape 998877",
    )
    r = await cliente.post(realizada, json=nota, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (409, "devolucion_no_aprobada")


async def test_devolucion_no_permitida_en_nivel_2_y_no_vigente(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, credito: Callable[..., str]
) -> None:
    n2 = credito(cliente_a, tipo="nivel_2")
    repro = credito(cliente_a, tipo="reprogramacion")
    vencido = credito(cliente_a, dias=-1)
    for id_, cod in (
        (n2, "devolucion_no_permitida"),
        (repro, "devolucion_no_permitida"),
        (vencido, "credito_no_vigente"),
    ):
        r = await cliente.post(
            f"/api/v1/creditos/{id_}/devolucion", json=MOTIVO, headers=con(cliente_a)
        )
        assert (r.status_code, codigo(r)) == (409, cod)
    r = await cliente.post(
        f"/api/v1/creditos/{UUID(int=5)}/devolucion", json=MOTIVO, headers=con(cliente_a)
    )
    assert r.status_code == 404
