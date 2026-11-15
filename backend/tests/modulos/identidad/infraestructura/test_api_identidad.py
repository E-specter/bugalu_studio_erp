"""API de RF-01: perfil, solicitudes de acceso y usuarios (contra el stack local con RLS real)."""

import base64
import json
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.compartido.autenticacion import obtener_resolutor_clave
from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba

pytestmark = pytest.mark.integracion

CrearUsuario = Callable[[], UsuarioDePrueba]
PonerRol = Callable[[UsuarioDePrueba, str, str | None], None]

PERFIL = {
    "id", "correo", "correo_confirmado", "nombre", "telefono", "nombre_artistico", "rol",
    "especialidad",
}  # fmt: skip
SOLICITUD = {
    "id", "id_usuario", "nombre", "correo", "especialidad", "mensaje", "estado", "motivo",
    "creada_en", "revisada_en",
}  # fmt: skip
ID = uuid4()
# (metodo, ruta, cuerpo, es_de_administrador)
ENDPOINTS: list[tuple[str, str, dict[str, Any] | None, bool]] = [
    ("GET", "/perfil", None, False),
    ("PATCH", "/perfil", {"nombre": "x"}, False),
    ("POST", "/perfil/verificar-correo", None, False),
    ("POST", "/solicitudes-acceso", {"especialidad": "mezcla"}, False),
    ("GET", "/solicitudes-acceso/mia", None, False),
    ("GET", "/solicitudes-acceso", None, True),
    ("POST", f"/solicitudes-acceso/{ID}/aprobar", {"rol": "personal", "especialidad": "x"}, True),
    ("POST", f"/solicitudes-acceso/{ID}/rechazar", {"motivo": "x"}, True),
    ("GET", "/usuarios", None, True),
    ("PATCH", f"/usuarios/{ID}", {"rol": "personal"}, True),
]
CODIGOS = {
    ("GET", "/perfil"): {"200", "401", "404", "503"},
    ("PATCH", "/perfil"): {"200", "401", "404", "422", "503"},
    ("POST", "/perfil/verificar-correo"): {"200", "401", "404", "409", "503"},
    ("POST", "/solicitudes-acceso"): {"201", "401", "409", "422", "503"},
    ("GET", "/solicitudes-acceso/mia"): {"200", "401", "404", "503"},
    ("GET", "/solicitudes-acceso"): {"200", "401", "403", "422", "503"},
    ("POST", "/solicitudes-acceso/{id_solicitud}/aprobar"): {
        "200",
        "401",
        "403",
        "404",
        "409",
        "422",
        "503",
    },  # fmt: skip
    ("POST", "/solicitudes-acceso/{id_solicitud}/rechazar"): {
        "200",
        "401",
        "403",
        "404",
        "409",
        "422",
        "503",
    },  # fmt: skip
    ("GET", "/usuarios"): {"200", "401", "403", "422", "503"},
    ("PATCH", "/usuarios/{id_usuario}"): {"200", "401", "403", "404", "409", "422", "503"},
}


def _con(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _llamar(
    cliente: AsyncClient, metodo: str, ruta: str, usuario: UsuarioDePrueba | str | None, cuerpo=None
):  # type: ignore[no-untyped-def]
    token = usuario.token if isinstance(usuario, UsuarioDePrueba) else usuario
    return await cliente.request(metodo, f"/api/v1{ruta}", headers=_con(token), json=cuerpo)


def _admin(crear: CrearUsuario, poner_rol: PonerRol) -> UsuarioDePrueba:
    u = crear()
    poner_rol(u, "administrador", None)
    return u


def _unico_administrador(
    crear: CrearUsuario, poner_rol: PonerRol, configuracion: Configuracion
) -> UsuarioDePrueba:
    admin = _admin(crear, poner_rol)
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        conexion.execute(
            "update public.usuario set rol = 'cliente' where rol = 'administrador' and id <> %s",
            (admin.id,),
        )
    return admin


def _fila(configuracion: Configuracion, sql: str, *args: Any) -> tuple[Any, ...] | None:
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        return conexion.execute(sql, args).fetchone()


# ---------- 401 en todos los endpoints ----------


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "_"), ENDPOINTS)
async def test_401_sin_token(
    cliente: AsyncClient, metodo: str, ruta: str, cuerpo: Any, _: bool
) -> None:
    r = await _llamar(cliente, metodo, ruta, None, cuerpo)
    assert r.status_code == 401
    assert r.json()["error"]["codigo"] == "no_autenticado"


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "_"), ENDPOINTS)
async def test_401_token_con_alg_cambiado(
    cliente: AsyncClient, crear_usuario: CrearUsuario, metodo: str, ruta: str, cuerpo: Any, _: bool
) -> None:
    cabecera, carga, firma = crear_usuario().token.split(".")
    datos = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    datos["alg"] = "HS256"
    falsa = base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()
    r = await _llamar(cliente, metodo, ruta, f"{falsa}.{carga}.{firma}", cuerpo)
    assert r.status_code == 401


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "_"), ENDPOINTS)
async def test_401_token_caducado(
    app: FastAPI,
    cliente: AsyncClient,
    configuracion: Configuracion,
    metodo: str,
    ruta: str,
    cuerpo: Any,
    _: bool,
) -> None:
    clave = ec.generate_private_key(ec.SECP256R1())
    app.dependency_overrides[obtener_resolutor_clave] = lambda: lambda _t: clave.public_key()
    caducado = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "iss": configuracion.emisor_jwt,
            "exp": time.time() - 60,
        },
        clave,
        algorithm="ES256",
    )
    r = await _llamar(cliente, metodo, ruta, caducado, cuerpo)
    assert r.status_code == 401


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "_"), [e for e in ENDPOINTS if e[3]])
async def test_403_un_cliente_no_usa_los_endpoints_de_administracion(
    cliente: AsyncClient, crear_usuario: CrearUsuario, metodo: str, ruta: str, cuerpo: Any, _: bool
) -> None:
    r = await _llamar(cliente, metodo, ruta, crear_usuario(), cuerpo)
    assert r.status_code == 403
    assert r.json()["error"]["codigo"] == "sin_permiso"


# ---------- perfil ----------


async def test_patch_perfil_cambia_nombre_telefono_y_nombre_artistico_del_cliente(
    cliente: AsyncClient, crear_usuario: CrearUsuario
) -> None:
    a, b = crear_usuario(), crear_usuario()
    cambios = {"nombre": "Ana", "telefono": "+51999888777", "nombre_artistico": "Ana MC"}
    r = await _llamar(cliente, "PATCH", "/perfil", a, cambios)
    assert r.status_code == 200
    assert set(r.json()) == PERFIL
    assert {k: r.json()[k] for k in cambios} == cambios
    assert r.json()["correo"] == a.correo
    assert (await _llamar(cliente, "GET", "/perfil", a)).json()["nombre"] == "Ana"
    assert (await _llamar(cliente, "GET", "/perfil", b)).json()["nombre"] is None  # B intacto


@pytest.mark.parametrize("campo", [{"rol": "administrador"}, {"especialidad": "x"}, {"id": "x"}])
async def test_patch_perfil_con_campos_de_administracion_es_422_y_no_cambia_nada(
    cliente: AsyncClient,
    crear_usuario: CrearUsuario,
    configuracion: Configuracion,
    campo: dict[str, str],
) -> None:
    a = crear_usuario()
    r = await _llamar(cliente, "PATCH", "/perfil", a, {"nombre": "Hack", **campo})
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "datos_invalidos"
    assert _fila(
        configuracion, "select nombre, rol, especialidad from public.usuario where id = %s", a.id
    ) == (None, "cliente", None)


@pytest.mark.parametrize("cuerpo", [{"telefono": "123"}, {"telefono": "abc"}, {"nombre": ""}])
async def test_patch_perfil_con_datos_invalidos_es_422(
    cliente: AsyncClient, crear_usuario: CrearUsuario, cuerpo: dict[str, str]
) -> None:
    r = await _llamar(cliente, "PATCH", "/perfil", crear_usuario(), cuerpo)
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "datos_invalidos"


async def test_el_personal_no_cambia_su_nombre_artistico(
    cliente: AsyncClient,
    crear_usuario: CrearUsuario,
    poner_rol: PonerRol,
    configuracion: Configuracion,
) -> None:
    p = crear_usuario()
    poner_rol(p, "personal", "mezcla")
    r = await _llamar(cliente, "PATCH", "/perfil", p, {"nombre": "Pepe", "nombre_artistico": "DJ"})
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "campo_no_permitido"
    assert _fila(
        configuracion, "select nombre, nombre_artistico from public.usuario where id = %s", p.id
    ) == (None, None)
    ok = await _llamar(cliente, "PATCH", "/perfil", p, {"nombre": "Pepe"})
    assert ok.status_code == 200 and ok.json()["nombre"] == "Pepe"


async def test_verificar_correo_con_sesion_por_contrasena_es_409(
    cliente: AsyncClient, crear_usuario: CrearUsuario
) -> None:
    a = crear_usuario()
    r = await _llamar(cliente, "POST", "/perfil/verificar-correo", a)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "verificacion_no_valida"
    assert (await _llamar(cliente, "GET", "/perfil", a)).json()["correo_confirmado"] is False


async def test_verificar_correo_con_sesion_por_enlace_es_200_y_solo_afecta_al_propio(
    cliente: AsyncClient,
    crear_usuario: CrearUsuario,
    sesion_por_enlace: Callable[[UsuarioDePrueba], str],
) -> None:
    a, b = crear_usuario(), crear_usuario()
    r = await _llamar(cliente, "POST", "/perfil/verificar-correo", sesion_por_enlace(a))
    assert r.status_code == 200
    assert r.json()["correo_confirmado"] is True and r.json()["id"] == str(a.id)
    assert (await _llamar(cliente, "GET", "/perfil", a)).json()["correo_confirmado"] is True
    assert (await _llamar(cliente, "GET", "/perfil", b)).json()["correo_confirmado"] is False


# ---------- solicitudes de acceso ----------


async def test_crear_solicitud_201_y_segunda_pendiente_409(
    cliente: AsyncClient, crear_usuario: CrearUsuario
) -> None:
    a = crear_usuario()
    r = await _llamar(
        cliente, "POST", "/solicitudes-acceso", a, {"especialidad": "mezcla", "mensaje": "hola"}
    )
    assert r.status_code == 201
    assert set(r.json()) == SOLICITUD
    assert (r.json()["estado"], r.json()["especialidad"], r.json()["mensaje"]) == (
        "pendiente", "mezcla", "hola",
    )  # fmt: skip
    assert (r.json()["id_usuario"], r.json()["correo"]) == (str(a.id), a.correo)
    otra = await _llamar(cliente, "POST", "/solicitudes-acceso", a, {"especialidad": "otra"})
    assert otra.status_code == 409 and otra.json()["error"]["codigo"] == "conflicto"


@pytest.mark.parametrize(
    "cuerpo", [{}, {"especialidad": "   "}, {"especialidad": "x", "estado": "aprobada"}]
)
async def test_crear_solicitud_con_datos_invalidos_es_422(
    cliente: AsyncClient, crear_usuario: CrearUsuario, cuerpo: dict[str, str]
) -> None:
    r = await _llamar(cliente, "POST", "/solicitudes-acceso", crear_usuario(), cuerpo)
    assert r.status_code == 422


async def test_quien_ya_es_personal_no_solicita_acceso(
    cliente: AsyncClient, crear_usuario: CrearUsuario, poner_rol: PonerRol
) -> None:
    p = crear_usuario()
    poner_rol(p, "personal", "mezcla")
    r = await _llamar(cliente, "POST", "/solicitudes-acceso", p, {"especialidad": "x"})
    assert r.status_code == 409


async def test_mi_solicitud_404_luego_200_y_otro_usuario_no_la_ve(
    cliente: AsyncClient, crear_usuario: CrearUsuario
) -> None:
    a, b = crear_usuario(), crear_usuario()
    sin = await _llamar(cliente, "GET", "/solicitudes-acceso/mia", a)
    assert sin.status_code == 404 and sin.json()["error"]["codigo"] == "no_encontrado"
    creada = await _llamar(cliente, "POST", "/solicitudes-acceso", a, {"especialidad": "mezcla"})
    mia = await _llamar(cliente, "GET", "/solicitudes-acceso/mia", a)
    assert mia.status_code == 200 and mia.json() == creada.json()
    assert (await _llamar(cliente, "GET", "/solicitudes-acceso/mia", b)).status_code == 404


async def test_listar_solicitudes_filtra_por_estado(
    cliente: AsyncClient, crear_usuario: CrearUsuario, poner_rol: PonerRol
) -> None:
    admin, a, b = _admin(crear_usuario, poner_rol), crear_usuario(), crear_usuario()
    sa = (await _llamar(cliente, "POST", "/solicitudes-acceso", a, {"especialidad": "x"})).json()
    sb = (await _llamar(cliente, "POST", "/solicitudes-acceso", b, {"especialidad": "y"})).json()
    await _llamar(
        cliente, "POST", f"/solicitudes-acceso/{sb['id']}/rechazar", admin, {"motivo": "m"}
    )
    pendientes = await _llamar(cliente, "GET", "/solicitudes-acceso?estado=pendiente", admin)
    assert pendientes.status_code == 200
    ids = {s["id"] for s in pendientes.json()}
    assert sa["id"] in ids and sb["id"] not in ids
    assert all(s["estado"] == "pendiente" and set(s) == SOLICITUD for s in pendientes.json())
    todas = {s["id"] for s in (await _llamar(cliente, "GET", "/solicitudes-acceso", admin)).json()}
    assert {sa["id"], sb["id"]} <= todas
    invalido = await _llamar(cliente, "GET", "/solicitudes-acceso?estado=otro", admin)
    assert invalido.status_code == 422


async def test_aprobar_asigna_rol_y_especialidad_y_la_segunda_vez_es_409(
    cliente: AsyncClient, crear_usuario: CrearUsuario, poner_rol: PonerRol
) -> None:
    admin, a = _admin(crear_usuario, poner_rol), crear_usuario()
    s = (
        await _llamar(cliente, "POST", "/solicitudes-acceso", a, {"especialidad": "mezcla"})
    ).json()
    cuerpo = {"rol": "personal", "especialidad": "ingenieria"}
    r = await _llamar(cliente, "POST", f"/solicitudes-acceso/{s['id']}/aprobar", admin, cuerpo)
    assert r.status_code == 200 and set(r.json()) == SOLICITUD
    assert r.json()["estado"] == "aprobada" and r.json()["revisada_en"] is not None
    perfil = (await _llamar(cliente, "GET", "/perfil", a)).json()
    assert (perfil["rol"], perfil["especialidad"]) == ("personal", "ingenieria")
    de_nuevo = await _llamar(
        cliente, "POST", f"/solicitudes-acceso/{s['id']}/aprobar", admin, cuerpo
    )
    assert de_nuevo.status_code == 409 and de_nuevo.json()["error"]["codigo"] == "conflicto"
    rechazar = await _llamar(
        cliente, "POST", f"/solicitudes-acceso/{s['id']}/rechazar", admin, {"motivo": "m"}
    )
    assert rechazar.status_code == 409


async def test_aprobar_404_y_422(
    cliente: AsyncClient, crear_usuario: CrearUsuario, poner_rol: PonerRol
) -> None:
    admin, a = _admin(crear_usuario, poner_rol), crear_usuario()
    s = (await _llamar(cliente, "POST", "/solicitudes-acceso", a, {"especialidad": "x"})).json()
    ok = {"rol": "personal", "especialidad": "x"}
    assert (
        await _llamar(cliente, "POST", f"/solicitudes-acceso/{uuid4()}/aprobar", admin, ok)
    ).status_code == 404
    for malo in (
        {"rol": "cliente", "especialidad": "x"},
        {"rol": "personal"},
        {"rol": "personal", "especialidad": " "},
    ):
        r = await _llamar(cliente, "POST", f"/solicitudes-acceso/{s['id']}/aprobar", admin, malo)
        assert r.status_code == 422
    assert (await _llamar(cliente, "GET", "/perfil", a)).json()["rol"] == "cliente"


async def test_rechazar_guarda_el_motivo_que_ve_el_solicitante(
    cliente: AsyncClient, crear_usuario: CrearUsuario, poner_rol: PonerRol
) -> None:
    admin, a = _admin(crear_usuario, poner_rol), crear_usuario()
    s = (await _llamar(cliente, "POST", "/solicitudes-acceso", a, {"especialidad": "x"})).json()
    r = await _llamar(
        cliente, "POST", f"/solicitudes-acceso/{s['id']}/rechazar", admin, {"motivo": "sin cupo"}
    )
    assert r.status_code == 200 and r.json()["estado"] == "rechazada"
    mia = (await _llamar(cliente, "GET", "/solicitudes-acceso/mia", a)).json()
    assert (mia["estado"], mia["motivo"]) == ("rechazada", "sin cupo")
    assert (await _llamar(cliente, "GET", "/perfil", a)).json()["rol"] == "cliente"
    assert (
        await _llamar(
            cliente, "POST", f"/solicitudes-acceso/{s['id']}/rechazar", admin, {"motivo": "m"}
        )
    ).status_code == 409
    assert (
        await _llamar(
            cliente, "POST", f"/solicitudes-acceso/{uuid4()}/rechazar", admin, {"motivo": "m"}
        )
    ).status_code == 404
    for malo in ({}, {"motivo": " "}):
        assert (
            await _llamar(cliente, "POST", f"/solicitudes-acceso/{s['id']}/rechazar", admin, malo)
        ).status_code == 422


async def test_si_asignar_el_rol_falla_la_solicitud_sigue_pendiente(
    cliente: AsyncClient,
    crear_usuario: CrearUsuario,
    poner_rol: PonerRol,
    configuracion: Configuracion,
) -> None:
    # El unico administrador tiene una solicitud pendiente y se aprueba a si mismo como personal.
    admin = _unico_administrador(crear_usuario, poner_rol, configuracion)
    with psycopg.connect(configuracion.url_base_datos_admin) as conexion:
        id_solicitud = conexion.execute(
            "insert into public.solicitud_acceso (id_usuario, especialidad) "
            "values (%s, 'x') returning id",
            (admin.id,),
        ).fetchone()
    assert id_solicitud is not None
    r = await _llamar(
        cliente, "POST", f"/solicitudes-acceso/{id_solicitud[0]}/aprobar", admin,
        {"rol": "personal", "especialidad": "x"},
    )  # fmt: skip
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "ultimo_administrador"
    assert _fila(
        configuracion,
        "select estado, revisada_en from public.solicitud_acceso where id = %s",
        id_solicitud[0],
    ) == ("pendiente", None)


# ---------- usuarios ----------


async def test_listar_usuarios_por_rol(
    cliente: AsyncClient, crear_usuario: CrearUsuario, poner_rol: PonerRol
) -> None:
    admin, p, c = _admin(crear_usuario, poner_rol), crear_usuario(), crear_usuario()
    poner_rol(p, "personal", "mezcla")
    r = await _llamar(cliente, "GET", "/usuarios?rol=personal", admin)
    assert r.status_code == 200
    por_id = {u["id"]: u for u in r.json()}
    assert str(p.id) in por_id and str(c.id) not in por_id
    assert set(por_id[str(p.id)]) == PERFIL and por_id[str(p.id)]["correo"] == p.correo
    todos = {u["id"] for u in (await _llamar(cliente, "GET", "/usuarios", admin)).json()}
    assert {str(p.id), str(c.id), str(admin.id)} <= todos
    assert (await _llamar(cliente, "GET", "/usuarios?rol=jefe", admin)).status_code == 422


async def test_patch_usuario_cambia_rol_y_especialidad_sin_tocar_a_otros(
    cliente: AsyncClient, crear_usuario: CrearUsuario, poner_rol: PonerRol
) -> None:
    admin, a, b = _admin(crear_usuario, poner_rol), crear_usuario(), crear_usuario()
    r = await _llamar(
        cliente, "PATCH", f"/usuarios/{a.id}", admin, {"rol": "personal", "especialidad": "mezcla"}
    )
    assert r.status_code == 200 and set(r.json()) == PERFIL
    assert (r.json()["rol"], r.json()["especialidad"]) == ("personal", "mezcla")
    solo = await _llamar(
        cliente, "PATCH", f"/usuarios/{a.id}", admin, {"especialidad": "mastering"}
    )
    assert (solo.json()["rol"], solo.json()["especialidad"]) == ("personal", "mastering")
    assert (await _llamar(cliente, "GET", "/perfil", b)).json()["rol"] == "cliente"


async def test_patch_usuario_errores(
    cliente: AsyncClient,
    crear_usuario: CrearUsuario,
    poner_rol: PonerRol,
    configuracion: Configuracion,
) -> None:
    admin, a = _admin(crear_usuario, poner_rol), crear_usuario()
    assert (
        await _llamar(cliente, "PATCH", f"/usuarios/{uuid4()}", admin, {"rol": "personal"})
    ).status_code == 404
    for malo in ({"rol": "jefe"}, {"nombre": "x"}):
        assert (
            await _llamar(cliente, "PATCH", f"/usuarios/{a.id}", admin, malo)
        ).status_code == 422
    # un cliente no se promueve a si mismo
    r = await _llamar(cliente, "PATCH", f"/usuarios/{a.id}", a, {"rol": "administrador"})
    assert r.status_code == 403
    assert _fila(configuracion, "select rol from public.usuario where id = %s", a.id) == (
        "cliente",
    )


async def test_el_ultimo_administrador_no_puede_quitarse_el_rol(
    cliente: AsyncClient,
    crear_usuario: CrearUsuario,
    poner_rol: PonerRol,
    configuracion: Configuracion,
) -> None:
    admin = _unico_administrador(crear_usuario, poner_rol, configuracion)
    r = await _llamar(cliente, "PATCH", f"/usuarios/{admin.id}", admin, {"rol": "cliente"})
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "ultimo_administrador"
    assert _fila(configuracion, "select rol from public.usuario where id = %s", admin.id) == (
        "administrador",
    )
    segundo = _admin(crear_usuario, poner_rol)
    ok = await _llamar(cliente, "PATCH", f"/usuarios/{admin.id}", segundo, {"rol": "cliente"})
    assert ok.status_code == 200 and ok.json()["rol"] == "cliente"


# ---------- OpenAPI ----------


def test_openapi_declara_los_codigos_del_contrato_con_respuesta_error(app: FastAPI) -> None:
    documento = app.openapi()
    for (metodo, ruta), esperados in CODIGOS.items():
        respuestas = documento["paths"][f"/api/v1{ruta}"][metodo.lower()]["responses"]
        assert esperados <= set(respuestas), (metodo, ruta, esperados - set(respuestas))
        for codigo in esperados - {"200", "201"}:
            assert respuestas[codigo]["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/RespuestaError"
            }, (metodo, ruta, codigo)
    esquemas = documento["components"]["schemas"]
    assert set(esquemas["Perfil"]["properties"]) == PERFIL
    assert set(esquemas["Solicitud"]["properties"]) == SOLICITUD
