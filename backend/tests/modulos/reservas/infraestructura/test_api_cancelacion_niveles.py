"""RF-18 (parte A): vista previa y cancelacion por niveles (CA-01 a CA-04, CA-15)."""

import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

RESERVAS = "/api/v1/reservas"
PRECIO = '{"lineas": [], "recargos": [], "total": "200", "anticipo": "100"}'
# Los plazos guardados mandan: con estos, una reserva de 2027 cae en el nivel que se pide.
PLAZOS = {1: (48, 24), 2: (10_000_000, 100), 3: (20_000_000, 10_000_000)}


@pytest.fixture
def reserva_con_pagos(sql: Ejecutar, reservar: Callable[..., str]) -> Callable[..., str]:
    """Reserva (2027) de total 200 con el adelanto pagado; `nivel` fija los plazos guardados."""
    dias = iter(range(1, 28))

    def crear(
        usuario: UsuarioDePrueba, nivel: int = 1, estado: str = "confirmada", pagada: bool = True
    ) -> str:
        dia = next(dias)
        id_ = reservar(
            usuario.id,
            f"2027-06-{dia:02d}T10:00:00-05:00",
            f"2027-06-{dia:02d}T12:00:00-05:00",
            estado,
        )
        h1, h2 = PLAZOS[nivel]
        sql(
            "update public.reserva set precio = %s::jsonb, total = 200, "
            "creada_en = now() - interval '30 days', "
            "parametros_aplicados = parametros_aplicados || "
            "jsonb_build_object('horas_nivel_1', %s::int, 'horas_nivel_2', %s::int) where id = %s",
            PRECIO,
            h1,
            h2,
            UUID(id_),
        )
        sql(
            "insert into public.cuota (id_reserva, hito, monto, estado, pagado) "
            "values (%s, 'al_reservar', 100, %s, %s), (%s, 'al_terminar', 100, 'pendiente', 0)",
            UUID(id_),
            "pagada" if pagada else "pendiente",
            100 if pagada else 0,
            UUID(id_),
        )
        return id_

    return crear


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


CLAVES_VISTA = {
    "nivel",
    "anticipacion_horas",
    "pagado",
    "en_validacion",
    "retenido",
    "credito",
    "credito_vence",
    "puede_reprogramar",
    "reprogramaciones_restantes",
}


@pytest.mark.parametrize(
    ("nivel", "retenido", "credito"),
    [(1, "0.00", "100.00"), (2, "50.00", "50.00"), (3, "100.00", "0.00")],
)
async def test_vista_previa_con_los_ejemplos_de_ca_02(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    sql: Ejecutar,
    nivel: int,
    retenido: str,
    credito: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, nivel)
    r = await cliente.get(f"{RESERVAS}/{id_}/cancelacion", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    v = r.json()
    assert set(v) == CLAVES_VISTA
    assert (v["nivel"], v["pagado"], v["en_validacion"]) == (nivel, "100.00", "0.00")
    assert (v["retenido"], v["credito"]) == (retenido, credito)
    assert (v["credito_vence"] is None) == (credito == "0.00")
    assert v["puede_reprogramar"] is (nivel < 3)
    assert sql("select estado from public.reserva where id = %s", UUID(id_)) == [("confirmada",)]
    assert sql("select count(*) from public.credito") == [(0,)]


async def test_vista_previa_sin_pagos_no_tiene_nivel(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, reserva_con_pagos: Callable[..., str]
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1, "pre_reservada", pagada=False)
    v = (await cliente.get(f"{RESERVAS}/{id_}/cancelacion", headers=con(cliente_a))).json()
    assert (v["nivel"], v["pagado"], v["retenido"], v["credito"]) == (None, "0.00", "0.00", "0.00")


async def test_vista_previa_quien_puede_verla(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
) -> None:
    id_ = reserva_con_pagos(cliente_a)
    url = f"{RESERVAS}/{id_}/cancelacion"
    assert (await cliente.get(url)).status_code == 401
    r = await cliente.get(url, headers=con(cliente_b))
    assert (r.status_code, codigo(r)) == (404, "no_encontrado")
    r = await cliente.get(url, headers=con(personal))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert (await cliente.get(url, headers=con(administrador))).status_code == 200
    r = await cliente.get(f"{RESERVAS}/{UUID(int=7)}/cancelacion", headers=con(cliente_a))
    assert r.status_code == 404


async def test_vista_previa_no_cancelable_es_409(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, reserva_con_pagos: Callable[..., str]
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1, "finalizada")
    r = await cliente.get(f"{RESERVAS}/{id_}/cancelacion", headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (409, "no_cancelable")


async def test_aviso_en_de_la_vista_previa_solo_lo_pasa_el_administrador(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    url = f"{RESERVAS}/{id_}/cancelacion"
    antes = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    r = await cliente.get(url, params={"aviso_en": antes}, headers=con(cliente_a))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    r = await cliente.get(url, params={"aviso_en": antes}, headers=con(administrador))
    assert r.status_code == 200 and r.json()["nivel"] == 1
    futuro = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    r = await cliente.get(url, params={"aviso_en": futuro}, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (422, "aviso_invalido")
    r = await cliente.get(url, params={"aviso_en": "ayer"}, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")


@pytest.mark.parametrize(
    ("nivel", "retenido", "credito"),
    [(1, "0.00", "100.00"), (2, "50.00", "50.00"), (3, "100.00", "0.00")],
)
async def test_el_cliente_cancela_con_pagos_y_la_politica_se_aplica_en_la_base(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    sql: Ejecutar,
    nivel: int,
    retenido: str,
    credito: str,
) -> None:
    id_ = reserva_con_pagos(cliente_a, nivel)
    r = await cliente.post(
        f"{RESERVAS}/{id_}/cancelar",
        json={"nivel_esperado": nivel, "nota": "No podre ir"},
        headers=con(cliente_a),
    )
    assert r.status_code == 200, r.text
    reserva = r.json()
    assert (reserva["estado"], reserva["motivo_cancelacion"], reserva["pagado"]) == (
        "cancelada",
        "cliente",
        "100.00",
    )
    c = reserva["cancelacion"]
    assert (c["nivel"], c["por"], c["pagado"], c["retenido"], c["credito"], c["nota"]) == (
        nivel,
        "cliente",
        "100.00",
        retenido,
        credito,
        "No podre ir",
    )
    assert c["registrada_por"] is None and "excepcion" not in c and c["aviso_en"]
    cuotas = {q["hito"]: q for q in reserva["cuotas"]}
    assert (cuotas["al_reservar"]["estado"], cuotas["al_reservar"]["pagado"]) == (
        "pagada",
        "100.00",
    )
    assert (cuotas["al_terminar"]["estado"], cuotas["al_terminar"]["pagable"]) == ("anulada", False)
    assert sql("select sum(saldo) from public.credito")[0][0] == (
        None if credito == "0.00" else sql("select %s::numeric", credito)[0][0]
    )


async def test_nivel_esperado_ausente_o_distinto_da_409_con_la_vista_nueva_y_no_cambia_nada(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 2)
    for cuerpo in (None, {"nivel_esperado": 1}):
        r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", json=cuerpo, headers=con(cliente_a))
        assert (r.status_code, codigo(r)) == (409, "nivel_cambiado"), r.text
        d = r.json()["error"]["detalles"]
        assert set(d) == CLAVES_VISTA
        assert (d["nivel"], d["retenido"], d["credito"]) == (2, "50.00", "50.00")
    assert sql("select estado from public.reserva where id = %s", UUID(id_)) == [("confirmada",)]
    assert sql("select count(*) from public.credito") == [(0,)]


async def test_sin_pagos_cancela_gratis_sin_nivel_esperado_como_hoy(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 3, "pre_reservada", pagada=False)
    r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "cancelada"
    assert r.json()["cancelacion"]["nivel"] is None
    assert sql("select count(*) from public.credito") == [(0,)]
    assert {q["estado"] for q in r.json()["cuotas"]} == {"pendiente"}


async def test_otro_cliente_personal_y_anon_no_cancelan_y_la_fila_queda_intacta(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    url = f"{RESERVAS}/{id_}/cancelar"
    cuerpo = {"nivel_esperado": 1}
    r = await cliente.post(url, json=cuerpo, headers=con(cliente_b))
    assert (r.status_code, codigo(r)) == (404, "no_encontrado")
    r = await cliente.post(url, json=cuerpo, headers=con(personal))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert (await cliente.post(url, json=cuerpo)).status_code == 401
    assert sql("select estado, nivel_cancelacion from public.reserva where id = %s", UUID(id_)) == [
        ("confirmada", None)
    ]


async def test_el_cliente_no_se_fija_el_aviso_ni_cancela_por_el_estudio(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, reserva_con_pagos: Callable[..., str]
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    ayer = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    for cuerpo in ({"nivel_esperado": 1, "por": "cliente", "aviso_en": ayer}, {"por": "estudio"}):
        r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", json=cuerpo, headers=con(cliente_a))
        assert (r.status_code, codigo(r)) == (403, "sin_permiso")


async def test_el_administrador_cancela_en_nombre_del_cliente_con_aviso_en_y_nota(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
) -> None:
    id_ = reserva_con_pagos(cliente_a, 2)
    url = f"{RESERVAS}/{id_}/cancelar"
    antes = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    futuro = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    remoto = (datetime.now(UTC) - timedelta(days=400)).isoformat()
    base = {"por": "cliente", "nota": "Pidio por WhatsApp"}
    for aviso in (None, futuro, remoto):
        cuerpo = base | ({"aviso_en": aviso} if aviso else {})
        r = await cliente.post(url, json=cuerpo, headers=con(administrador))
        assert (r.status_code, codigo(r)) == (422, "aviso_invalido"), (aviso, r.text)
    r = await cliente.post(
        url, json={"por": "cliente", "aviso_en": antes}, headers=con(administrador)
    )
    assert (r.status_code, codigo(r)) == (422, "nota_requerida")
    r = await cliente.post(url, json=base | {"aviso_en": antes}, headers=con(administrador))
    assert r.status_code == 200, r.text
    c = r.json()["cancelacion"]
    assert (c["nivel"], c["retenido"], c["credito"]) == (2, "50.00", "50.00")
    assert c["registrada_por"]["id"] == str(administrador.id)
    # El cliente no ve quien la registro; el administrador si.
    vista = (await cliente.get(f"{RESERVAS}/{id_}", headers=con(cliente_a))).json()
    assert vista["cancelacion"]["registrada_por"] is None


async def test_cancelar_por_el_estudio_con_pagos_pide_nota_y_deja_la_eleccion_pendiente(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    sql: Ejecutar,
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    url = f"{RESERVAS}/{id_}/cancelar"
    r = await cliente.post(url, json={"por": "estudio"}, headers=con(administrador))
    assert (r.status_code, codigo(r)) == (422, "nota_requerida")
    r = await cliente.post(
        url, json={"por": "estudio", "nota": "Averia en la sala"}, headers=con(administrador)
    )
    assert r.status_code == 200, r.text
    reserva = r.json()
    assert (reserva["estado"], reserva["motivo_cancelacion"]) == ("cancelada", "administrador")
    assert reserva["eleccion_estudio"] == "pendiente"
    assert reserva["cancelacion"]["por"] == "estudio" and reserva["cancelacion"]["nivel"] is None
    assert sql("select count(*) from public.credito") == [(0,)]


@pytest.mark.parametrize("motivo", ["cliente", "caducada"])
async def test_solo_las_cancelaciones_de_la_politica_traen_cancelacion(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    reserva_con_pagos: Callable[..., str],
    sql: Ejecutar,
    motivo: str,
) -> None:
    """Una cancelada anterior a RF-18 (sin `aviso_en`) o por caducidad no lleva `cancelacion`."""
    id_ = reserva_con_pagos(cliente_a, 1, estado="cancelada", pagada=False)
    sql("update public.reserva set motivo_cancelacion = %s where id = %s", motivo, UUID(id_))
    r = await cliente.get(f"{RESERVAS}/{id_}", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "cancelada" and "cancelacion" not in r.json()


async def test_la_reserva_trae_pagado_politica_y_reprogramaciones(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, reserva_con_pagos: Callable[..., str]
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    r = (await cliente.get(f"{RESERVAS}/{id_}", headers=con(cliente_a))).json()
    assert r["pagado"] == "100.00" and r["reprogramaciones"] == []
    assert "cancelacion" not in r and "eleccion_estudio" not in r and "devolucion" not in r
    assert r["politica"] == {
        "horas_nivel_1": 48,
        "horas_nivel_2": 24,
        "porcentaje_penalizacion_nivel_2": 25,
        "minutos_tolerancia_inasistencia": 15,
        "dias_vigencia_credito": 30,
        "reprogramaciones_nivel_1": 2,
        "reprogramaciones_nivel_2": 1,
    }
    assert {q["hito"]: q["pagado"] for q in r["cuotas"]} == {
        "al_reservar": "100.00",
        "al_terminar": "0.00",
    }


async def test_401_con_token_de_alg_cambiado_o_caducado(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, reserva_con_pagos: Callable[..., str]
) -> None:
    id_ = reserva_con_pagos(cliente_a, 1)
    cabecera, carga, firma = cliente_a.token.split(".")
    datos = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    datos["alg"] = "HS256"
    falsa = base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()
    vencida = datos | {"alg": "none"}
    otra = base64.urlsafe_b64encode(json.dumps(vencida).encode()).rstrip(b"=").decode()
    for token in (f"{falsa}.{carga}.{firma}", f"{otra}.{carga}."):
        for metodo, ruta in (("get", "cancelacion"), ("post", "cancelar")):
            r = await cliente.request(
                metodo.upper(),
                f"{RESERVAS}/{id_}/{ruta}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 401, (metodo, r.text)


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, cliente_a: UsuarioDePrueba
) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    id_ = UUID(int=9)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        for metodo, ruta in (("GET", "cancelacion"), ("POST", "cancelar")):
            r = await c.request(metodo, f"{RESERVAS}/{id_}/{ruta}", headers=con(cliente_a))
            assert (r.status_code, codigo(r)) == (503, "base_de_datos_no_disponible")


def test_openapi_declara_los_codigos_de_cancelacion(app: FastAPI) -> None:
    rutas = app.openapi()["paths"]
    esperados = {
        ("get", "/api/v1/reservas/{id_reserva}/cancelacion"): {200, 401, 403, 404, 409, 422, 503},
        ("post", "/api/v1/reservas/{id_reserva}/cancelar"): {200, 401, 403, 404, 409, 422, 503},
    }
    for (metodo, ruta), codigos in esperados.items():
        assert codigos <= {int(c) for c in rutas[ruta][metodo]["responses"]}, ruta
