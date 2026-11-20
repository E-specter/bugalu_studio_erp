# ruff: noqa: E501, F811 - cuerpos JSON de prueba y fixtures compartidas
"""RF-15 B1 contra el stack local: agendar, doble agendamiento, pago, caducidad y encuentro."""

import asyncio
import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.base_datos import crear_pool
from bugalu.compartido.configuracion import Configuracion, obtener_configuracion
from bugalu.main import crear_app
from bugalu.modulos.notificaciones.aplicacion.enviar_pendientes.caso_de_uso import enviar_pendientes
from bugalu.modulos.notificaciones.dominio.correo import Correo
from bugalu.modulos.notificaciones.infraestructura.salida.bandeja_postgres import BandejaPostgres
from tests.conftest import UsuarioDePrueba
from tests.modulos.asesorias.infraestructura.conftest import Ejecutar, con
from tests.modulos.asesorias.infraestructura.test_api_asesorias import (
    PROF,
    crear_especialidad,
    publicar,
)

pytestmark = pytest.mark.integracion

ASE = "/api/v1/asesorias"
PNG = b"\x89PNG\r\n\x1a\n" + b"contenido-de-prueba" * 10


def codigo(r: httpx.Response) -> str:
    return str(r.json()["error"]["codigo"])


def hora(dia: int, h: int, m: int = 0) -> datetime:
    return datetime(2027, 3, dia, h, m, tzinfo=timezone_lima())


def timezone_lima():  # type: ignore[no-untyped-def]
    from datetime import timezone

    return timezone(timedelta(hours=-5))


def cuerpo(prof: UsuarioDePrueba, inicio: datetime, **extra: Any) -> dict[str, Any]:
    return {
        "id_profesional": str(prof.id),
        "inicio": inicio.isoformat(),
        "duracion": 30,
        "modalidad": "virtual",
        "version_condiciones": "1.0.0",
        **extra,
    }


@pytest.fixture
async def listo(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
) -> UsuarioDePrueba:
    """Profesional publicado con un bloque el 2027-03-10 de 09:00 a 13:00 (Lima)."""
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    await publicar(cliente, administrador, profesional, esp)
    r = await cliente.post(
        f"{PROF}/{profesional.id}/horarios",
        headers=con(profesional),
        json={"horarios": [{"inicio": hora(10, 9).isoformat(), "fin": hora(10, 13).isoformat()}]},
    )
    assert r.status_code == 201, r.text
    return profesional


@pytest.fixture
def cliente_c(
    crear_usuario: Callable[[], UsuarioDePrueba], completar_perfil: Callable[..., UsuarioDePrueba]
) -> UsuarioDePrueba:
    return completar_perfil(crear_usuario(), "Carla Paz")


async def agendar(
    c: AsyncClient, u: UsuarioDePrueba, prof: UsuarioDePrueba, inicio: datetime, **extra: Any
) -> httpx.Response:
    return await c.post(ASE, headers=con(u), json=cuerpo(prof, inicio, **extra))


# --- CA-06: agendar ---


async def test_agendar_crea_la_asesoria_pendiente_con_folio_precio_y_una_cuota(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba, listo: UsuarioDePrueba, sql: Ejecutar
) -> None:
    r = await agendar(cliente, cliente_a, listo, hora(10, 10))
    assert r.status_code == 201, r.text
    a = r.json()
    assert (
        a["folio"].startswith("A-") and a["estado"] == "pre_reservada" and a["tipo"] == "asesoria"
    )
    assert (a["duracion"], a["modalidad"], a["precio"]["total"]) == (30, "virtual", "50.00")
    assert a["precio"]["impuesto"]["incluido"] is True
    assert [(c["hito"], c["monto"], c["pagable"]) for c in a["cuotas"]] == [
        ("al_reservar", "50.00", True)
    ]
    assert a["version_condiciones"] == "1.0.0" and a["vence_pago"]
    assert "cliente" not in a and "notas" not in a  # el cliente no ve ni su contacto ni notas
    assert a["politica"]["horas_nivel_1"] > 0
    assert sql(  # aceptacion `asesoria` y aviso para pagar en la misma operacion
        "select count(*) from public.aceptacion where contexto = 'asesoria' and id_operacion = %s",
        UUID(a["id"]),
    ) == [(1,)]
    assert sql(
        "select count(*) from public.notificacion where tipo = 'reserva_creada' and datos ->> 'id_reserva' = %s",
        a["id"],
    ) == [(1,)]


async def test_los_codigos_de_error_de_agendar(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    crear_usuario: Callable[[], UsuarioDePrueba],
) -> None:
    async def pide(inicio: datetime, **extra: Any) -> tuple[int, str]:
        r = await agendar(cliente, cliente_a, listo, inicio, **extra)
        return r.status_code, ("" if r.status_code == 201 else codigo(r))

    assert await pide(hora(10, 14)) == (422, "fuera_de_horario")
    assert await pide(hora(10, 12, 30), duracion=60) == (422, "fuera_de_horario")
    assert await pide(hora(10, 10, 15)) == (422, "datos_invalidos")
    assert await pide(hora(10, 10), duracion=45) == (422, "datos_invalidos")
    assert await pide(hora(10, 10), modalidad="en la luna") == (422, "datos_invalidos")
    assert await pide(hora(10, 10), version_condiciones="9.9.9") == (409, "texto_desactualizado")
    r = await cliente.post(
        ASE, headers=con(cliente_a), json={**cuerpo(listo, hora(10, 10)), "precio": "1"}
    )
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    cercano = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    assert await pide(cercano) == (422, "anticipacion_insuficiente")
    lejano = hora(10, 10).replace(year=2030)
    assert await pide(lejano) == (422, "anticipacion_excesiva")
    r = await cliente.post(
        ASE,
        headers=con(cliente_a),
        json={**cuerpo(listo, hora(10, 10)), "id_profesional": str(uuid4())},
    )
    assert (r.status_code, codigo(r)) == (404, "no_encontrado")
    r = await cliente.post(ASE, headers=con(crear_usuario()), json=cuerpo(listo, hora(10, 10)))
    assert (r.status_code, codigo(r)) == (
        409,
        "reaceptacion_requerida",
    )  # el registro sin aceptar va primero
    r = await cliente.post(ASE, json=cuerpo(listo, hora(10, 10)))
    assert r.status_code == 401


async def test_duracion_no_ofrecida_y_perfil_no_publicado(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    completar_perfil: Callable[..., UsuarioDePrueba],
    sql: Ejecutar,
) -> None:
    sql("delete from public.precio_asesoria where id_profesional = %s and minutos = 60", listo.id)
    r = await agendar(cliente, cliente_a, listo, hora(10, 10), duracion=60)
    assert (r.status_code, codigo(r)) == (409, "duracion_no_ofrecida")
    sql("update public.perfil_profesional set activo = false where id = %s", listo.id)
    r = await agendar(cliente, cliente_a, listo, hora(10, 10))
    assert (r.status_code, codigo(r)) == (404, "no_encontrado")
    r = await agendar(
        cliente, completar_perfil(administrador), listo, hora(10, 10)
    )  # ni el administrador agenda un perfil inactivo
    assert (r.status_code, codigo(r)) == (404, "no_encontrado")


async def test_el_profesional_no_agenda_y_personal_y_administrador_si_para_si(
    cliente: AsyncClient,
    listo: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    completar_perfil: Callable[..., UsuarioDePrueba],
    otro_profesional: UsuarioDePrueba,
) -> None:
    r = await agendar(cliente, listo, listo, hora(10, 10))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    r = await agendar(cliente, otro_profesional, listo, hora(10, 10))
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    for u in (
        completar_perfil(personal, "Pepe Staff"),
        completar_perfil(administrador, "Ada Admin"),
    ):
        r = await agendar(cliente, u, listo, hora(10, 10, 30) if u is personal else hora(10, 12))
        assert r.status_code == 201, r.text


# --- CA-07: doble agendamiento ---


async def test_dos_solicitudes_simultaneas_que_se_solapan_una_gana_y_la_otra_409(
    app: Any,
    cliente_a: UsuarioDePrueba,
    cliente_c: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c1,
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c2,
    ):
        r1, r2 = await asyncio.gather(
            agendar(c1, cliente_a, listo, hora(10, 11)),
            agendar(c2, cliente_c, listo, hora(10, 11, 0)),
        )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]
    perdedora = r1 if r1.status_code == 409 else r2
    assert codigo(perdedora) == "horario_no_disponible"
    assert sql(
        "select count(*) from public.reserva where id_profesional = %s and inicio = %s",
        listo.id,
        hora(10, 11),
    ) == [(1,)]


async def test_solape_parcial_409_y_la_siguiente_sin_margen_si(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_c: UsuarioDePrueba,
    listo: UsuarioDePrueba,
) -> None:
    assert (await agendar(cliente, cliente_a, listo, hora(10, 10), duracion=60)).status_code == 201
    r = await agendar(cliente, cliente_c, listo, hora(10, 10, 30))
    assert (r.status_code, codigo(r)) == (409, "horario_no_disponible")
    assert (await agendar(cliente, cliente_c, listo, hora(10, 11))).status_code == 201


async def test_la_disponibilidad_marca_lo_ocupado_y_lo_propio(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_c: UsuarioDePrueba,
    listo: UsuarioDePrueba,
) -> None:
    assert (await agendar(cliente, cliente_a, listo, hora(10, 10))).status_code == 201
    params = {"desde": hora(10, 0).isoformat(), "hasta": hora(11, 0).isoformat()}
    r = await cliente.get(
        f"{PROF}/{listo.id}/disponibilidad", params=params, headers=con(cliente_a)
    )
    assert [o["propia"] for o in r.json()["ocupados"]] == [True]
    r = await cliente.get(f"{PROF}/{listo.id}/disponibilidad", params=params)
    assert [o["propia"] for o in r.json()["ocupados"]] == [False]
    assert "id_cliente" not in r.text and "folio" not in r.text


# --- lecturas y CA-16 ---


async def test_lecturas_por_rol_y_ajena_404_con_la_fila_intacta(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_c: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    a = (await agendar(cliente, cliente_a, listo, hora(10, 10))).json()
    url = f"{ASE}/{a['id']}"
    # el dueno
    r = await cliente.get(url, headers=con(cliente_a))
    assert r.status_code == 200 and "cliente" not in r.json() and "notas" not in r.json()
    assert (
        r.json()["profesional"]["id"] == str(listo.id)
        and r.json()["constancia_disponible"] is False
    )
    # su profesional: contacto del cliente y notas, nunca cuotas ni pagado
    r = await cliente.get(url, headers=con(listo))
    p = r.json()
    assert (
        r.status_code == 200
        and p["cliente"]["nombre"] == "Ana Torres"
        and p["cliente"]["telefono"] == "987654321"
    )
    assert p["cliente"]["correo"] == cliente_a.correo and p["notas"] == ""
    assert not {"cuotas", "pagado", "version_condiciones"} & p.keys()
    assert "documento" not in r.text and "domicilio" not in r.text
    # el administrador lo ve todo
    r = await cliente.get(url, headers=con(administrador))
    assert r.status_code == 200 and r.json()["cuotas"] and r.json()["cliente"]
    # ajenos: 404 y la fila no cambia
    for u in (cliente_c, otro_profesional, personal):
        assert (await cliente.get(url, headers=con(u))).status_code == 404, u
    antes = sql("select estado, inicio from public.reserva where id = %s", UUID(a["id"]))
    r = await cliente.patch(f"{url}/encuentro", headers=con(cliente_c), json={"lugar": "x"})
    assert r.status_code == 404
    assert sql("select estado, inicio from public.reserva where id = %s", UUID(a["id"])) == antes
    # GET /reservas/{id} sigue siendo solo de sala
    assert (
        await cliente.get(f"/api/v1/reservas/{a['id']}", headers=con(cliente_a))
    ).status_code == 404
    # listas
    r = await cliente.get(f"{ASE}/mias", headers=con(cliente_a))
    assert [x["id"] for x in r.json()] == [a["id"]] and r.json()[0]["encuentro_pendiente"] is True
    assert (
        r.json()[0]["por_cerrar"] is False
        and "cliente" not in r.json()[0]
        and r.json()[0]["vence_pago"]
    )
    assert (await cliente.get(f"{ASE}/mias", headers=con(cliente_c))).json() == []
    assert (await cliente.get(f"{ASE}/mias", headers=con(administrador))).json() == []
    assert (await cliente.get(f"{ASE}/mias", headers=con(listo))).status_code == 403
    r = await cliente.get(ASE, headers=con(listo))
    assert [x["id"] for x in r.json()] == [a["id"]] and r.json()[0]["cliente"][
        "nombre"
    ] == "Ana Torres"
    assert (await cliente.get(ASE, headers=con(otro_profesional))).json() == []
    assert any(
        x["id"] == a["id"] for x in (await cliente.get(ASE, headers=con(administrador))).json()
    )
    for u in (cliente_a, personal):
        assert (await cliente.get(ASE, headers=con(u))).status_code == 403
    assert (await cliente.get(ASE, headers=con(listo), params={"estado": "x"})).status_code == 422
    assert (await cliente.get(ASE, headers=con(listo), params={"estado": "pre_reservada"})).json()
    assert (await cliente.get(ASE, headers=con(listo), params={"por_cerrar": "true"})).json() == []
    for ruta in (f"{ASE}/mias", ASE, url):
        assert (await cliente.get(ruta)).status_code == 401


# --- CA-08: pago y caducidad ---


async def test_el_pago_aprobado_confirma_la_asesoria_y_avisa_a_su_profesional(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    a = (await agendar(cliente, cliente_a, listo, hora(10, 10))).json()
    r = await cliente.post(
        "/api/v1/pagos",
        data={
            "id_cuota": a["cuotas"][0]["id"],
            "metodo": "yape",
            "monto": "50.00",
            "numero_operacion": f"PRUEBA-{uuid4().hex[:10]}",
        },
        files={"captura": ("c.png", PNG, "image/png")},
        headers=con(cliente_a),
    )
    assert r.status_code == 201, r.text
    assert r.json()["reserva"]["tipo"] == "asesoria"
    r2 = await cliente.post(f"/api/v1/pagos/{r.json()['id']}/aprobar", headers=con(administrador))
    assert r2.status_code == 200, r2.text
    assert (await cliente.get(f"{ASE}/{a['id']}", headers=con(cliente_a))).json()[
        "estado"
    ] == "confirmada"
    tipos = sorted(
        f[0]
        for f in sql(
            "select tipo from public.notificacion where datos ->> 'id_reserva' = %s", a["id"]
        )
    )
    assert "asesoria_confirmada_profesional" in tipos and "pago_aprobado" in tipos
    # el profesional no ve pagos
    assert (
        await cliente.get(f"/api/v1/pagos/{r.json()['id']}", headers=con(listo))
    ).status_code in (403, 404)


async def test_sin_pago_caduca_y_el_horario_se_libera(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    cliente_c: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    a = (await agendar(cliente, cliente_a, listo, hora(10, 10))).json()
    sql(
        "update public.reserva set vence_pago = now() - interval '1 minute' where id = %s",
        UUID(a["id"]),
    )
    disp = await cliente.get(
        f"{PROF}/{listo.id}/disponibilidad",
        params={"desde": hora(10, 0).isoformat(), "hasta": hora(11, 0).isoformat()},
    )
    assert disp.json()["ocupados"] == []  # ya libre para quien consulta
    r = await agendar(cliente, cliente_c, listo, hora(10, 10))
    assert r.status_code == 201, r.text
    assert sql(
        "select estado, motivo_cancelacion from public.reserva where id = %s", UUID(a["id"])
    ) == [("cancelada", "caducada")]
    assert sql(
        "select count(*) from public.notificacion where tipo = 'reserva_caducada' and datos ->> 'id_reserva' = %s",
        a["id"],
    ) == [(1,)]


# --- CA-09: lugar o enlace ---


async def test_el_encuentro_lo_cambia_su_profesional_o_el_administrador(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    a = (await agendar(cliente, cliente_a, listo, hora(10, 10), modalidad="presencial")).json()
    url = f"{ASE}/{a['id']}/encuentro"
    r = await cliente.patch(url, headers=con(listo), json={"lugar": "  Av. Lima 123  "})
    assert r.status_code == 200 and r.json()["lugar"] == "Av. Lima 123", r.text
    avisos = sql(
        "select destinatario from public.notificacion where tipo = 'asesoria_encuentro_cambiado' and datos ->> 'id_reserva' = %s",
        a["id"],
    )
    assert sorted(f[0] for f in avisos) == sorted([cliente_a.correo, listo.correo])
    # sin cambios: sin aviso nuevo
    assert (
        await cliente.patch(url, headers=con(listo), json={"lugar": "Av. Lima 123"})
    ).status_code == 200
    assert (
        len(
            sql(
                "select 1 from public.notificacion where tipo = 'asesoria_encuentro_cambiado' and datos ->> 'id_reserva' = %s",
                a["id"],
            )
        )
        == 2
    )
    # cambiar de modalidad borra el dato de la otra
    r = await cliente.patch(
        url,
        headers=con(administrador),
        json={"modalidad": "virtual", "enlace": "https://meet.google.com/abc-defg-hij"},
    )
    assert (r.json()["lugar"] if "lugar" in r.json() else None) is None and r.json()[
        "enlace"
    ] == "https://meet.google.com/abc-defg-hij"
    r = await cliente.patch(url, headers=con(listo), json={"enlace": None})
    assert r.status_code == 200 and "enlace" not in r.json()  # "por confirmar"
    # errores
    for malo in (
        "http://meet.google.com/x",
        "https://zoom.us/j/1",
        "https://meet.google.com.evil.pe/x",
    ):
        r = await cliente.patch(url, headers=con(listo), json={"enlace": malo})
        assert (r.status_code, codigo(r)) == (422, "enlace_invalido"), malo
    r = await cliente.patch(
        url, headers=con(listo), json={"modalidad": "presencial", "lugar": "x" * 301}
    )
    assert (r.status_code, codigo(r)) == (422, "datos_invalidos")
    r = await cliente.patch(url, headers=con(listo), json={"modalidad": "nube"})
    assert r.status_code == 422
    r = await cliente.patch(url, headers=con(cliente_a), json={"lugar": "mi casa"})
    assert (r.status_code, codigo(r)) == (403, "sin_permiso")
    assert (
        await cliente.patch(url, headers=con(otro_profesional), json={"lugar": "x"})
    ).status_code == 404
    assert (await cliente.patch(url, json={"lugar": "x"})).status_code == 401
    sql(
        "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = %s",
        UUID(a["id"]),
    )
    r = await cliente.patch(
        url, headers=con(listo), json={"modalidad": "presencial", "lugar": "otro"}
    )
    assert (r.status_code, codigo(r)) == (409, "no_editable")


# --- seguridad transversal ---


def _con_alg(usuario: UsuarioDePrueba, alg: str) -> str:
    cabecera, carga, firma = usuario.token.split(".")
    h = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    h["alg"] = alg
    falsa = base64.urlsafe_b64encode(json.dumps(h).encode()).rstrip(b"=").decode()
    return f"{falsa}.{carga}.{firma if alg != 'none' else ''}"


def _caducado(usuario: UsuarioDePrueba) -> str:
    cabecera, carga, firma = usuario.token.split(".")
    c = json.loads(base64.urlsafe_b64decode(carga + "=="))
    c["exp"] = 1000
    nueva = base64.urlsafe_b64encode(json.dumps(c).encode()).rstrip(b"=").decode()
    return f"{cabecera}.{nueva}.{firma}"


async def test_401_con_token_de_alg_cambiado_o_caducado(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba
) -> None:
    rutas = [
        ("POST", ASE, {"id_profesional": str(uuid4())}),
        ("GET", f"{ASE}/mias", None),
        ("GET", ASE, None),
        ("GET", f"{ASE}/{uuid4()}", None),
        ("PATCH", f"{ASE}/{uuid4()}/encuentro", {"lugar": "x"}),
    ]
    for token in (_con_alg(cliente_a, "HS256"), _con_alg(cliente_a, "none"), _caducado(cliente_a)):
        for metodo, ruta, c in rutas:
            r = await cliente.request(
                metodo, ruta, json=c, headers={"Authorization": f"Bearer {token}"}
            )
            assert r.status_code == 401, (metodo, ruta, r.status_code)


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, cliente_a: UsuarioDePrueba
) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        for metodo, ruta, c_ in (
            ("GET", f"{ASE}/mias", None),
            ("GET", ASE, None),
            ("GET", f"{ASE}/{uuid4()}", None),
            ("POST", ASE, cuerpo(cliente_a, hora(10, 10))),
            ("PATCH", f"{ASE}/{uuid4()}/encuentro", {"lugar": "x"}),
        ):
            r = await c.request(metodo, ruta, json=c_, headers=con(cliente_a))
            assert (r.status_code, codigo(r)) == (503, "base_de_datos_no_disponible"), (
                metodo,
                ruta,
            )


# --- correos reales al cliente: salen con los datos de la asesoria ---


async def correos_del_cliente(configuracion: Configuracion, correo: str) -> list[Correo]:
    class Recolector:
        def __init__(self) -> None:
            self.correos: list[Correo] = []

        async def enviar(self, c: Correo) -> None:
            self.correos.append(c)

    recolector = Recolector()
    async with crear_pool(configuracion.url_base_datos) as pool:
        await enviar_pendientes(BandejaPostgres(pool), recolector, limite=500)
    return [c for c in recolector.correos if c.destinatario == correo]


async def test_los_correos_de_crear_y_de_aprobar_el_pago_traen_los_datos_de_la_asesoria(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    listo: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    configuracion: Configuracion,
    sql: Ejecutar,
) -> None:
    sql("update public.usuario set nombre = 'Pablo Ríos' where id = %s", str(listo.id))
    a = (await agendar(cliente, cliente_a, listo, hora(10, 11))).json()
    (creada,) = await correos_del_cliente(configuracion, cliente_a.correo)
    assert creada.asunto.startswith(f"Asesoría {a['folio']}: paga antes del")
    assert (
        "Modalidad: Virtual (Google Meet)" in creada.cuerpo
        and "Profesional: Pablo Ríos" in creada.cuerpo
    )
    cuota = a["cuotas"][0]["id"]
    assert (
        f"Registrar pago: http://127.0.0.1:4321/app/asesorias/pagar?id={a['id']}&cuota={cuota}"
        in (creada.cuerpo)
    )
    r = await cliente.post(
        "/api/v1/pagos",
        data={
            "id_cuota": cuota,
            "metodo": "yape",
            "monto": "50.00",
            "numero_operacion": f"PRUEBA-{uuid4().hex[:10]}",
        },
        files={"captura": ("c.png", PNG, "image/png")},
        headers=con(cliente_a),
    )
    assert r.status_code == 201, r.text
    await cliente.post(f"/api/v1/pagos/{r.json()['id']}/aprobar", headers=con(administrador))
    (aprobada,) = await correos_del_cliente(configuracion, cliente_a.correo)
    assert aprobada.asunto == f"Asesoría {a['folio']} confirmada"
    assert "Modalidad: Virtual" in aprobada.cuerpo and "asesoría con Pablo Ríos" in aprobada.cuerpo
    assert f"Ver mi asesoría: http://127.0.0.1:4321/app/asesorias/detalle?id={a['id']}" in (
        aprobada.cuerpo
    )
