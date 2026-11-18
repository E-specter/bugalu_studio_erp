# ruff: noqa: E501, F811 - cuerpos JSON de prueba y fixtures compartidas
"""Correcciones de la auditoria de RF-15 etapa A (ronda 1): B1, perfil sin rol, foto y 401/503."""

import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from fastapi import FastAPI
from httpx import AsyncClient

from bugalu.compartido.autenticacion import obtener_resolutor_clave
from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.asesorias.infraestructura.entrada.http import router as router_asesorias
from bugalu.modulos.asesorias.infraestructura.salida.almacen_storage import AlmacenFotosStorage
from tests.conftest import UsuarioDePrueba
from tests.modulos.asesorias.infraestructura.conftest import con
from tests.modulos.asesorias.infraestructura.test_api_asesorias import (
    JPEG,
    PROF,
    bloque,
    codigo,
    crear_especialidad,
    publicar,
)

pytestmark = pytest.mark.integracion

API = "/api/v1"
UN_ID = "00000000-0000-0000-0000-0000000000aa"


# --- B1: el profesional no es cliente de sala ni de pagos ---


async def test_un_profesional_recibe_403_en_las_rutas_de_cliente_de_sala_y_pagos(
    cliente: AsyncClient, profesional: UsuarioDePrueba
) -> None:
    captura = {"archivo": ("c.png", b"\x89PNG\r\n\x1a\n" + b"x" * 40, "image/png")}
    pago = {"id_cuota": UN_ID, "metodo": "yape", "monto": "10.00", "numero_operacion": "OP-1234"}
    llamadas: list[tuple[str, str, dict[str, Any]]] = [
        (
            "POST",
            "/reservas",
            {"json": {"inicio": "2027-01-10T10:00:00-05:00", "fin": "2027-01-10T12:00:00-05:00"}},
        ),
        ("GET", "/reservas/mias", {}),
        ("GET", f"/reservas/{UN_ID}", {}),
        ("GET", f"/reservas/{UN_ID}/cancelacion", {}),
        ("POST", f"/reservas/{UN_ID}/cancelar", {"json": {}}),
        ("POST", f"/reservas/{UN_ID}/reprogramar/simular", {"json": {}}),
        ("POST", f"/reservas/{UN_ID}/reprogramar", {"json": {}}),
        ("POST", f"/reservas/{UN_ID}/eleccion-estudio", {"json": {}}),
        ("POST", "/pagos", {"data": pago, "files": captura}),
        ("GET", f"/pagos/{UN_ID}", {}),
        ("GET", f"/pagos/{UN_ID}/captura", {}),
        ("GET", "/creditos", {}),
        ("POST", f"/cuotas/{UN_ID}/credito", {"json": {"monto": "5.00"}}),
        ("POST", f"/creditos/{UN_ID}/devolucion", {"json": {"motivo": "motivo suficiente"}}),
        ("GET", f"/devoluciones/{UN_ID}", {}),
    ]
    for metodo, ruta, extra in llamadas:
        r = await cliente.request(metodo, API + ruta, headers=con(profesional), **extra)
        assert (r.status_code, codigo(r)) == (403, "sin_permiso"), (
            metodo,
            ruta,
            r.status_code,
            r.text,
        )


async def test_un_cliente_sigue_llegando_a_sus_rutas(
    cliente: AsyncClient, crear_usuario: Callable[[], UsuarioDePrueba]
) -> None:
    c = crear_usuario()
    assert (await cliente.get(f"{API}/reservas/mias", headers=con(c))).status_code == 200
    assert (await cliente.get(f"{API}/creditos", headers=con(c))).status_code == 200


# --- No bloqueante 1: perfil solo de quien conserva el rol ---


async def test_quitar_el_rol_impide_reactivar_el_perfil_y_lo_saca_del_directorio(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
) -> None:
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    await publicar(cliente, administrador, profesional, esp)
    assert any(p["id"] == str(profesional.id) for p in (await cliente.get(PROF)).json())
    r = await cliente.patch(
        f"{API}/usuarios/{profesional.id}", headers=con(administrador), json={"rol": "cliente"}
    )
    assert r.status_code == 200, r.text
    assert not any(p["id"] == str(profesional.id) for p in (await cliente.get(PROF)).json())
    r = await cliente.patch(
        f"{PROF}/{profesional.id}", headers=con(administrador), json={"activo": True}
    )
    assert (r.status_code, codigo(r)) == (422, "rol_no_admitido")
    r = await cliente.patch(
        f"{PROF}/{profesional.id}", headers=con(administrador), json={"activo": False}
    )
    assert r.status_code == 200 and r.json()["publicado"] is False


# --- No bloqueante 2: la foto anterior se borra solo tras confirmar la transaccion ---


def _url_a_ruta(url: str) -> str:
    return url.split("/profesionales/", 1)[1]


async def test_si_la_base_falla_despues_de_guardar_la_foto_la_nueva_se_borra_y_la_anterior_sigue(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    await publicar(cliente, administrador, profesional, esp)
    ruta = f"{PROF}/{profesional.id}/foto"
    r = await cliente.put(
        ruta, headers=con(profesional), files={"archivo": ("f.jpg", JPEG, "image/jpeg")}
    )
    assert r.status_code == 200, r.text
    anterior = r.json()["foto_url"]
    assert httpx.get(anterior).content == JPEG

    async def falla(*_: Any, **__: Any) -> Any:
        raise RuntimeError("la base fallo despues de fijar_foto")

    monkeypatch.setattr(router_asesorias, "_perfil", falla)
    png = b"\x89PNG\r\n\x1a\n" + b"otra" * 30
    with pytest.raises(RuntimeError):
        await cliente.put(
            ruta, headers=con(profesional), files={"archivo": ("g.png", png, "image/png")}
        )
    monkeypatch.undo()
    assert (await cliente.get(f"{PROF}/{profesional.id}")).json()["foto_url"] == anterior
    assert httpx.get(anterior).content == JPEG  # la anterior sigue intacta
    otra = anterior.replace("foto-1", "foto-2")
    assert httpx.get(otra).status_code in (400, 404)  # la nueva no quedo huerfana


# --- No bloqueante 3: Storage solo admite las rutas que fija la API ---


async def test_storage_solo_admite_dos_rutas_de_foto_por_perfil_con_el_token_del_usuario(
    cliente: AsyncClient,
    configuracion: Configuracion,
    profesional: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
) -> None:
    base = f"{configuracion.url_supabase}/storage/v1/object/profesionales"
    cab = {
        "Authorization": f"Bearer {profesional.token}",
        "apikey": configuracion.clave_publicable_supabase,
        "Content-Type": "image/jpeg",
    }

    def subir(nombre: str, extra: dict[str, str] | None = None) -> int:
        return httpx.post(
            f"{base}/{nombre}", headers={**cab, **(extra or {})}, content=JPEG
        ).status_code

    id_ = profesional.id
    assert subir(f"{id_}/foto-1") == 200
    assert subir(f"{id_}/foto-1", {"x-upsert": "true"}) == 200  # sobrescribe, no acumula
    for malo in (
        f"{id_}/foto-3",
        f"{id_}/{uuid4().hex}.jpg",
        f"{id_}/sub/foto-1",
        f"{otro_profesional.id}/foto-1",
    ):
        assert subir(malo) in (400, 403), malo
    # Tras la subida directa el perfil sigue sin foto: solo la API escribe `foto_ruta`.
    r = await cliente.get(f"{PROF}/{id_}", headers=con(profesional))
    assert "foto_url" not in r.json()
    httpx.delete(f"{base}/{id_}/foto-1", headers=cab)


# --- No bloqueante 6: 401 con tokens reales de otro algoritmo, kid falso, caducado y sin sub; 503 con Storage caido ---

_RSA = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_P384 = ec.generate_private_key(ec.SECP384R1())
_ED = ed25519.Ed25519PrivateKey.generate()
_P256 = ec.generate_private_key(ec.SECP256R1())


def _token(
    clave: Any,
    alg: str,
    configuracion: Configuracion,
    *,
    kid: str | None = None,
    caduca: float = 60,
    sub: str | None = None,
) -> str:
    claims: dict[str, Any] = {
        "aud": "authenticated",
        "iss": configuracion.emisor_jwt,
        "exp": time.time() + caduca,
    }
    claims["sub"] = sub or str(uuid4())
    if sub == "":
        del claims["sub"]
    return jwt.encode(claims, clave, algorithm=alg, headers={"kid": kid} if kid else None)


CASOS_401 = {
    "rs256": (_RSA, "RS256", {}),
    "ps256": (_RSA, "PS256", {}),
    "es384": (_P384, "ES384", {}),
    "eddsa": (_ED, "EdDSA", {}),
    "caducado": (_P256, "ES256", {"caduca": -60}),
    "sin_sub": (_P256, "ES256", {"sub": ""}),
}


@pytest.mark.parametrize("caso", list(CASOS_401))
async def test_401_con_token_real_de_otro_algoritmo_caducado_o_sin_sub(
    app: FastAPI,
    cliente: AsyncClient,
    configuracion: Configuracion,
    profesional: UsuarioDePrueba,
    caso: str,
) -> None:
    clave, alg, extra = CASOS_401[caso]
    # El resolutor acepta la clave publica del firmante: lo que rechaza es la lista de algoritmos, la fecha o el `sub`.
    app.dependency_overrides[obtener_resolutor_clave] = lambda: lambda _t: clave.public_key()
    token = _token(clave, alg, configuracion, **extra)
    for metodo, ruta, cuerpo in _RUTAS_PROTEGIDAS(profesional.id):
        r = await cliente.request(
            metodo, ruta, json=cuerpo, headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 401, (caso, metodo, ruta, r.status_code)
        assert codigo(r) == "no_autenticado"


async def test_401_con_kid_falso(
    cliente: AsyncClient, configuracion: Configuracion, profesional: UsuarioDePrueba
) -> None:
    token = _token(_P256, "ES256", configuracion, kid="no-existe")
    for metodo, ruta, cuerpo in _RUTAS_PROTEGIDAS(profesional.id):
        r = await cliente.request(
            metodo, ruta, json=cuerpo, headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 401, (metodo, ruta, r.status_code)


def _RUTAS_PROTEGIDAS(id_: Any) -> list[tuple[str, str, Any]]:  # noqa: N802
    return [
        ("PATCH", f"{PROF}/{id_}", {"presentacion": "x"}),
        ("PUT", f"{PROF}/{id_}/foto", None),
        ("DELETE", f"{PROF}/{id_}/foto", None),
        ("POST", f"{PROF}/{id_}/horarios", {"horarios": [bloque(3, 10)]}),
        ("GET", f"{PROF}/{id_}/horarios/sugerencia?semana=2026-W50", None),
        ("POST", f"{API}/especialidades-asesoria", {"nombre": "Prueba x"}),
    ]


async def test_503_con_storage_caido_en_la_foto_y_la_base_queda_intacta(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    await publicar(cliente, administrador, profesional, esp)
    ruta = f"{PROF}/{profesional.id}/foto"
    r = await cliente.put(
        ruta, headers=con(profesional), files={"archivo": ("f.jpg", JPEG, "image/jpeg")}
    )
    assert r.status_code == 200, r.text
    anterior = r.json()["foto_url"]

    def caido(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("storage caido")

    monkeypatch.setattr(
        router_asesorias,
        "_almacen",
        lambda token: AlmacenFotosStorage("http://s", "k", token, httpx.MockTransport(caido)),
    )
    r = await cliente.put(
        ruta, headers=con(profesional), files={"archivo": ("g.jpg", JPEG, "image/jpeg")}
    )
    assert (r.status_code, codigo(r)) == (503, "almacenamiento_no_disponible")
    r = await cliente.delete(ruta, headers=con(profesional))
    assert (r.status_code, codigo(r)) == (503, "almacenamiento_no_disponible")
    monkeypatch.undo()
    assert (await cliente.get(f"{PROF}/{profesional.id}")).json()[
        "foto_url"
    ] == anterior  # el DELETE se revirtio
    assert httpx.get(anterior).content == JPEG
