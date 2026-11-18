# ruff: noqa: E501, F811 - cuerpos JSON de prueba y fixtures compartidas
"""RF-15 etapa A contra el stack local: rol, especialidades, perfil, precios, foto y horarios."""

import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from bugalu.compartido.configuracion import obtener_configuracion
from bugalu.main import crear_app
from tests.conftest import UsuarioDePrueba
from tests.modulos.asesorias.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

ESP, PROF = "/api/v1/especialidades-asesoria", "/api/v1/profesionales"
JPEG = b"\xff\xd8\xff\xe0" + b"foto-de-prueba" * 20
PDF = b"%PDF-1.7\n" + b"x" * 100


def codigo(r: httpx.Response) -> str:
    return str(r.json()["error"]["codigo"])


async def crear_especialidad(c: AsyncClient, admin: UsuarioDePrueba, nombre: str) -> str:
    r = await c.post(ESP, headers=con(admin), json={"nombre": nombre})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def publicar(
    c: AsyncClient, admin: UsuarioDePrueba, prof: UsuarioDePrueba, especialidad: str
) -> None:
    """Deja el perfil publico: especialidad (del profesional), precio (flujo RF-20) y activo."""
    r = await c.patch(
        f"{PROF}/{prof.id}", headers=con(prof), json={"especialidades": [especialidad]}
    )
    assert r.status_code == 200, r.text
    await fijar_precios(c, admin, prof, {"30": "50.00", "60": "90.00"})
    r = await c.patch(f"{PROF}/{prof.id}", headers=con(admin), json={"activo": True})
    assert r.status_code == 200 and r.json()["publicado"] is True, r.text


async def fijar_precios(
    c: AsyncClient, admin: UsuarioDePrueba, prof: UsuarioDePrueba, precios: dict[str, Any]
) -> httpx.Response:
    p = await c.post(
        "/api/v1/cambios-sensibles/previsualizar",
        headers=con(admin),
        json={
            "recurso": "profesional",
            "id_recurso": str(prof.id),
            "cambios": {"precios": precios},
        },
    )
    assert p.status_code == 200, p.text
    r = await c.post(
        "/api/v1/cambios-sensibles/confirmar",
        headers=con(admin),
        json={"token": p.json()["token"], "palabra": "CONFIRMAR"},
    )
    assert r.status_code == 200, r.text
    return r


def bloque(dias: int, hora: int, horas: int = 1) -> dict[str, str]:
    base = (datetime.now(UTC) + timedelta(days=dias)).replace(
        minute=0, second=0, microsecond=0
    ) + timedelta(hours=hora - datetime.now(UTC).hour)
    return {"inicio": base.isoformat(), "fin": (base + timedelta(hours=horas)).isoformat()}


# --- CA-01: el rol ---


async def test_asignar_el_rol_crea_un_perfil_inactivo_y_no_da_acceso_de_personal(
    cliente: AsyncClient, administrador: UsuarioDePrueba, profesional: UsuarioDePrueba
) -> None:
    r = await cliente.get(f"{PROF}/{profesional.id}", headers=con(administrador))
    assert r.status_code == 200 and (r.json()["activo"], r.json()["publicado"]) == (False, False)
    for ruta in ("reservas", "pagos", "usuarios", "registro-cambios", "reclamaciones"):
        r = await cliente.get(
            f"/api/v1/{ruta}",
            headers=con(profesional),
            params={"desde": "2026-12-01T00:00:00-05:00", "hasta": "2026-12-02T00:00:00-05:00"},
        )
        assert r.status_code == 403, (ruta, r.status_code, r.text)
    r = await cliente.get("/api/v1/parametros", headers=con(profesional))
    assert r.status_code == 403


async def test_un_cliente_no_asigna_el_rol_profesional(
    cliente: AsyncClient, profesional: UsuarioDePrueba
) -> None:
    r = await cliente.patch(
        f"/api/v1/usuarios/{profesional.id}", headers=con(profesional), json={"rol": "profesional"}
    )
    assert r.status_code == 403


async def test_el_administrador_crea_su_perfil_una_sola_vez_y_solo_con_rol_admitido(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    crear_usuario: Callable[[], UsuarioDePrueba],
) -> None:
    r = await cliente.post(
        PROF, headers=con(administrador), json={"id_usuario": str(administrador.id)}
    )
    assert r.status_code == 201 and r.json()["activo"] is False
    r = await cliente.post(
        PROF, headers=con(administrador), json={"id_usuario": str(administrador.id)}
    )
    assert (r.status_code, codigo(r)) == (409, "perfil_existente")
    r = await cliente.post(
        PROF, headers=con(administrador), json={"id_usuario": str(crear_usuario().id)}
    )
    assert (r.status_code, codigo(r)) == (422, "rol_no_admitido")
    r = await cliente.post(
        PROF,
        headers=con(administrador),
        json={"id_usuario": "0" * 8 + "-0000-0000-0000-" + "0" * 12},
    )
    assert r.status_code == 404
    r = await cliente.post(
        PROF, headers=con(crear_usuario()), json={"id_usuario": str(administrador.id)}
    )
    assert r.status_code == 403


# --- CA-02: especialidades ---


async def test_especialidades_unicas_sin_mayusculas_ni_tildes_y_se_desactivan(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    crear_usuario: Callable[[], UsuarioDePrueba],
    nombre_especialidad: Callable[[], str],
) -> None:
    nombre = nombre_especialidad() + " ñandú"
    id_ = await crear_especialidad(cliente, administrador, nombre)
    for repetido in (nombre.upper(), nombre.replace("ú", "u")):
        r = await cliente.post(ESP, headers=con(administrador), json={"nombre": repetido})
        assert (r.status_code, codigo(r)) == (409, "especialidad_duplicada"), repetido
    for malo in ("x", "y" * 61, "  "):
        r = await cliente.post(ESP, headers=con(administrador), json={"nombre": malo})
        assert r.status_code == 422, malo
    r = await cliente.post(ESP, headers=con(crear_usuario()), json={"nombre": "Prueba cliente"})
    assert r.status_code == 403
    r = await cliente.post(ESP, json={"nombre": "Prueba anon"})
    assert r.status_code == 401
    assert id_ in [x["id"] for x in (await cliente.get(ESP)).json()]
    r = await cliente.patch(f"{ESP}/{id_}", headers=con(administrador), json={"activa": False})
    assert r.status_code == 200 and r.json()["activa"] is False
    assert id_ not in [x["id"] for x in (await cliente.get(ESP)).json()]
    assert id_ in [
        x["id"]
        for x in (
            await cliente.get(ESP, params={"todas": "true"}, headers=con(administrador))
        ).json()
    ]
    assert (await cliente.get(ESP, params={"todas": "true"})).status_code == 401
    r = await cliente.get(ESP, params={"todas": "true"}, headers=con(crear_usuario()))
    assert r.status_code == 403
    r = await cliente.patch(
        f"{ESP}/{'0' * 8}-0000-0000-0000-{'0' * 12}",
        headers=con(administrador),
        json={"activa": True},
    )
    assert r.status_code == 404


# --- CA-03 y CA-04: perfil, publicacion y precios ---


async def test_el_perfil_es_publico_solo_con_activo_especialidad_y_precio(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
) -> None:
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    assert (await cliente.get(f"{PROF}/{profesional.id}")).status_code == 404  # inactivo
    await publicar(cliente, administrador, profesional, esp)
    r = await cliente.get(f"{PROF}/{profesional.id}")  # sin sesion
    assert r.status_code == 200
    cuerpo = r.json()
    assert "activo" not in cuerpo and cuerpo["id"] == str(profesional.id)
    assert [d["minutos"] for d in cuerpo["duraciones"]] == [30, 60]
    assert cuerpo["duraciones"][0]["precio"] == "50.00"
    assert cuerpo["duraciones"][0]["igv"] == {
        "nombre": "IGV", "porcentaje": "18.00", "incluido": True, "base": "42.37", "monto": "7.63",
    }  # fmt: skip
    lista = (await cliente.get(PROF, params={"especialidad": esp})).json()
    assert [p["id"] for p in lista] == [str(profesional.id)]
    # Desactivar la especialidad lo saca de la lista y de los filtros (CA-02).
    await cliente.patch(f"{ESP}/{esp}", headers=con(administrador), json={"activa": False})
    assert (await cliente.get(f"{PROF}/{profesional.id}")).status_code == 404
    assert (await cliente.get(PROF, params={"especialidad": esp})).json() == []
    propio = await cliente.get(f"{PROF}/{profesional.id}", headers=con(profesional))
    assert propio.json()["publicado"] is False and propio.json()["especialidades"] == []


async def test_el_profesional_edita_lo_suyo_con_sus_limites(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
    sql: Ejecutar,
    crear_usuario: Callable[[], UsuarioDePrueba],
) -> None:
    esp = [
        await crear_especialidad(cliente, administrador, nombre_especialidad()) for _ in range(6)
    ]
    ruta = f"{PROF}/{profesional.id}"
    redes = [{"red": "instagram", "valor": "@pablo"}]
    r = await cliente.patch(
        ruta,
        headers=con(profesional),
        json={
            "nombre_artistico": "Pab",
            "presentacion": "Ingeniero",
            "redes": redes,
            "especialidades": esp[:5],
        },
    )
    assert r.status_code == 200, r.text
    assert (r.json()["nombre_artistico"], r.json()["redes"], len(r.json()["especialidades"])) == (
        "Pab",
        redes,
        5,
    )
    malos: list[dict[str, Any]] = [
        {"nombre_artistico": "x" * 81}, {"presentacion": "x" * 601}, {"especialidades": esp},
        {"especialidades": []}, {"redes": [redes[0]] * 6}, {"redes": [{"red": "otra red", "valor": "x"}]},
        {"rol": "administrador"}, {"activo": None},
    ]  # fmt: skip
    for cuerpo in malos:
        r = await cliente.patch(ruta, headers=con(profesional), json=cuerpo)
        assert r.status_code == 422, (cuerpo, r.text)
    r = await cliente.patch(ruta, headers=con(profesional), json={"especialidades": [str(uuid4())]})
    assert r.status_code == 422
    # No toca su estado ni sus precios; no toca el perfil de otro; la fila ajena queda intacta.
    for cuerpo in ({"activo": True}, {"precios": {"30": "10.00"}}):
        assert (await cliente.patch(ruta, headers=con(profesional), json=cuerpo)).status_code == 403
    r = await cliente.patch(ruta, headers=con(otro_profesional), json={"presentacion": "Hackeada"})
    assert r.status_code in (403, 404)
    assert sql(
        "select presentacion from public.perfil_profesional where id = %s", profesional.id
    ) == [("Ingeniero",)]
    r = await cliente.patch(ruta, json={"presentacion": "anon"})
    assert r.status_code == 401
    assert (
        await cliente.patch(ruta, headers=con(crear_usuario()), json={"presentacion": "x"})
    ).status_code in (403, 404)


async def test_cambiar_un_precio_es_sensible_y_queda_registrado(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    ruta = f"{PROF}/{profesional.id}"
    r = await cliente.patch(ruta, headers=con(administrador), json={"precios": {"30": "50.00"}})
    assert (r.status_code, codigo(r)) == (428, "confirmacion_requerida")
    assert r.json()["error"]["detalles"] == {"campos": ["precio_30"]}
    assert sql(
        "select count(*) from public.precio_asesoria where id_profesional = %s", profesional.id
    ) == [(0,)]
    p = await cliente.post(
        "/api/v1/cambios-sensibles/previsualizar",
        headers=con(administrador),
        json={
            "recurso": "profesional",
            "id_recurso": str(profesional.id),
            "cambios": {"precios": {"30": "50.00"}},
        },
    )
    assert p.status_code == 200 and p.json()["impacto"]["operaciones_vigentes"] == 0
    assert [(x["campo"], x["anterior"], x["nuevo"]) for x in p.json()["cambios"]] == [
        ("precio_30", "no_ofrece", "50.00")
    ]
    assert p.json()["impacto"]["ejemplos"][0]["concepto"] == "Asesoría de 30 min"
    # La API directa no cambia nada hasta confirmar; el mismo valor ya no pide confirmacion.
    c = await cliente.post(
        "/api/v1/cambios-sensibles/confirmar",
        headers=con(administrador),
        json={"token": p.json()["token"], "palabra": "CONFIRMAR"},
    )
    assert c.status_code == 200
    assert sql(
        "select precio from public.precio_asesoria where id_profesional = %s", profesional.id
    ) == [(50,)]
    assert (
        await cliente.patch(ruta, headers=con(administrador), json={"precios": {"30": "50"}})
    ).status_code == 200
    registro = await cliente.get(
        "/api/v1/registro-cambios", headers=con(administrador), params={"recurso": "profesional"}
    )
    assert [
        (x["campo"], x["nuevo"]) for x in registro.json() if x["id_recurso"] == str(profesional.id)
    ] == [("precio_30", "50.00")]
    # Quitar la duracion: null = no ofrece, tambien sensible.
    r = await cliente.patch(ruta, headers=con(administrador), json={"precios": {"30": None}})
    assert r.status_code == 428
    for malo in ({"30": "0"}, {"45": "10"}, {"30": "abc"}, {"30": "1.234"}):
        r = await cliente.patch(ruta, headers=con(administrador), json={"precios": malo})
        assert r.status_code == 422, malo


# --- CA-03: foto ---


async def test_la_foto_se_valida_por_su_contenido_y_se_reemplaza_y_borra(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
) -> None:
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    await publicar(cliente, administrador, profesional, esp)
    ruta = f"{PROF}/{profesional.id}/foto"
    r = await cliente.put(
        ruta, headers=con(profesional), files={"archivo": ("f.jpg", JPEG, "image/jpeg")}
    )
    assert r.status_code == 200, r.text
    url = r.json()["foto_url"]
    assert url.endswith("/foto-1") and httpx.get(url).content == JPEG  # bucket publico
    # Un PDF con nombre y mime de imagen, o una foto de mas de 2 MB, no entran y la foto sigue.
    r = await cliente.put(
        ruta, headers=con(profesional), files={"archivo": ("f.png", PDF, "image/png")}
    )
    assert (r.status_code, codigo(r)) == (422, "formato_no_admitido")
    r = await cliente.put(
        ruta,
        headers=con(profesional),
        files={"archivo": ("f.jpg", JPEG + b"0" * 2 * 1024 * 1024, "image/jpeg")},
    )
    assert (r.status_code, codigo(r)) == (413, "archivo_muy_grande")
    r = await cliente.put(
        ruta, headers=con(otro_profesional), files={"archivo": ("f.jpg", JPEG, "image/jpeg")}
    )
    assert r.status_code in (403, 404)
    assert (await cliente.get(f"{PROF}/{profesional.id}")).json()["foto_url"] == url
    # Reemplazar: la anterior se borra del almacenamiento.
    png = b"\x89PNG\r\n\x1a\n" + b"otra" * 30
    r = await cliente.put(
        ruta, headers=con(administrador), files={"archivo": ("g.png", png, "image/png")}
    )
    assert r.status_code == 200 and r.json()["foto_url"] != url
    assert httpx.get(url).status_code in (400, 404)
    assert httpx.get(r.json()["foto_url"]).content == png
    nueva = r.json()["foto_url"]
    assert (await cliente.delete(ruta, headers=con(otro_profesional))).status_code in (403, 404)
    assert (await cliente.delete(ruta, headers=con(profesional))).status_code == 204
    assert "foto_url" not in (await cliente.get(f"{PROF}/{profesional.id}")).json()
    assert httpx.get(nueva).status_code in (400, 404)
    assert (
        await cliente.put(ruta, files={"archivo": ("f.jpg", JPEG, "image/jpeg")})
    ).status_code == 401


# --- CA-05: horarios y disponibilidad ---


async def test_horarios_sugerencia_solape_retiro_y_disponibilidad(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
) -> None:
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    await publicar(cliente, administrador, profesional, esp)
    ruta = f"{PROF}/{profesional.id}/horarios"
    lote = [bloque(3, 10, 2), bloque(3, 15, 1)]
    r = await cliente.post(ruta, headers=con(profesional), json={"horarios": lote})
    assert r.status_code == 201 and len(r.json()) == 2, r.text
    id_horario = r.json()[0]["id"]
    # Solape: 409 y el lote entero no se guarda; contiguo, si.
    r = await cliente.post(
        ruta, headers=con(profesional), json={"horarios": [bloque(4, 10), bloque(3, 11)]}
    )
    assert (r.status_code, codigo(r)) == (409, "horario_solapado")
    assert (
        await cliente.post(ruta, headers=con(profesional), json={"horarios": [bloque(3, 12)]})
    ).status_code == 201
    pasado = {"inicio": "2020-01-01T10:00:00-05:00", "fin": "2020-01-01T11:00:00-05:00"}
    suelto = {"inicio": "2099-01-01T10:10:00-05:00", "fin": "2099-01-01T11:00:00-05:00"}
    sin_zona = {"inicio": "2099-01-01T10:00:00", "fin": "2099-01-01T11:00:00"}
    for malo in ([pasado], [suelto], [sin_zona], [], [bloque(5, 10)] * 201):
        r = await cliente.post(ruta, headers=con(profesional), json={"horarios": malo})
        assert r.status_code == 422, malo
    # Otro profesional o un cliente no publican ni retiran lo ajeno.
    assert (
        await cliente.post(ruta, headers=con(otro_profesional), json={"horarios": [bloque(6, 10)]})
    ).status_code == 403
    assert (
        await cliente.delete(f"{ruta}/{id_horario}", headers=con(otro_profesional))
    ).status_code in (403, 404)
    assert (await cliente.post(ruta, json={"horarios": [bloque(6, 10)]})).status_code == 401
    # Disponibilidad publica: bloques con id, minutos libres por dia y duraciones.
    desde = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0)
    params = {"desde": desde.isoformat(), "hasta": (desde + timedelta(days=3)).isoformat()}
    d = (await cliente.get(f"{PROF}/{profesional.id}/disponibilidad", params=params)).json()
    assert len(d["horarios"]) == 3 and d["ocupados"] == [] and d["horarios"][0]["id"]
    assert sum(x["minutos_libres"] for x in d["dias"]) == 240
    assert [x["minutos"] for x in d["duraciones"]] == [30, 60] and {"desde", "hasta"} == set(
        d["limites"]
    )
    # Retirar el bloque: desaparece de la disponibilidad.
    assert (
        await cliente.delete(f"{ruta}/{id_horario}", headers=con(profesional))
    ).status_code == 204
    assert (
        await cliente.delete(f"{ruta}/{id_horario}", headers=con(profesional))
    ).status_code == 404
    d = (await cliente.get(f"{PROF}/{profesional.id}/disponibilidad", params=params)).json()
    assert sum(x["minutos_libres"] for x in d["dias"]) == 120
    # Rango invalido y perfil inexistente.
    malo = {"desde": params["hasta"], "hasta": params["desde"]}
    r = await cliente.get(f"{PROF}/{profesional.id}/disponibilidad", params=malo)
    assert (r.status_code, codigo(r)) == (422, "rango_invalido")
    r = await cliente.get(
        f"{PROF}/{'0' * 8}-0000-0000-0000-{'0' * 12}/disponibilidad", params=params
    )
    assert r.status_code == 404


async def test_la_disponibilidad_de_un_perfil_no_publicado_es_del_propio_y_del_administrador(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    otro_profesional: UsuarioDePrueba,
) -> None:
    ahora = datetime.now(UTC)
    params = {"desde": ahora.isoformat(), "hasta": (ahora + timedelta(days=2)).isoformat()}
    ruta = f"{PROF}/{profesional.id}/disponibilidad"
    assert (await cliente.get(ruta, params=params)).status_code == 404
    assert (
        await cliente.get(ruta, params=params, headers=con(otro_profesional))
    ).status_code == 404
    assert (await cliente.get(ruta, params=params, headers=con(profesional))).status_code == 200
    assert (await cliente.get(ruta, params=params, headers=con(administrador))).status_code == 200


async def test_la_sugerencia_copia_la_ultima_semana_publicada(
    cliente: AsyncClient, profesional: UsuarioDePrueba, otro_profesional: UsuarioDePrueba
) -> None:
    ruta = f"{PROF}/{profesional.id}/horarios"
    publicado = bloque(3, 10, 2)
    assert (
        await cliente.post(ruta, headers=con(profesional), json={"horarios": [publicado]})
    ).status_code == 201
    inicio = datetime.fromisoformat(publicado["inicio"])
    siguiente = (inicio + timedelta(days=7)).astimezone(timezone_lima()).isocalendar()
    semana = f"{siguiente.year}-W{siguiente.week:02d}"
    r = await cliente.get(f"{ruta}/sugerencia", headers=con(profesional), params={"semana": semana})
    assert r.status_code == 200
    esperado = datetime.fromisoformat(publicado["inicio"]) + timedelta(days=7)
    assert [datetime.fromisoformat(t["inicio"]) for t in r.json()] == [esperado]
    for semana_mala in ("2026-W99", "2026W01", "x"):
        r = await cliente.get(
            f"{ruta}/sugerencia", headers=con(profesional), params={"semana": semana_mala}
        )
        assert r.status_code == 422
    r = await cliente.get(
        f"{ruta}/sugerencia", headers=con(otro_profesional), params={"semana": semana}
    )
    assert r.status_code in (403, 404)
    assert (await cliente.get(f"{ruta}/sugerencia", params={"semana": semana})).status_code == 401


def timezone_lima():  # type: ignore[no-untyped-def]
    from datetime import timezone

    return timezone(timedelta(hours=-5))


# --- CA-16 / casos de rotura ---


def _con_alg(usuario: UsuarioDePrueba, alg: str) -> str:
    cabecera, carga, firma = usuario.token.split(".")
    h = json.loads(base64.urlsafe_b64decode(cabecera + "=="))
    h["alg"] = alg
    falsa = base64.urlsafe_b64encode(json.dumps(h).encode()).rstrip(b"=").decode()
    return f"{falsa}.{carga}.{firma if alg != 'none' else ''}"


async def test_401_con_token_de_alg_cambiado_en_las_rutas_protegidas(
    cliente: AsyncClient, profesional: UsuarioDePrueba
) -> None:
    id_ = profesional.id
    rutas = [
        ("PATCH", f"{PROF}/{id_}", {"presentacion": "x"}),
        ("PUT", f"{PROF}/{id_}/foto", None),
        ("DELETE", f"{PROF}/{id_}/foto", None),
        ("POST", f"{PROF}/{id_}/horarios", {"horarios": [bloque(3, 10)]}),
        ("GET", f"{PROF}/{id_}/horarios/sugerencia?semana=2026-W50", None),
        ("POST", ESP, {"nombre": "Prueba x"}),
    ]
    for alg in ("HS256", "none"):
        for metodo, ruta, cuerpo in rutas:
            r = await cliente.request(
                metodo,
                ruta,
                json=cuerpo,
                headers={"Authorization": f"Bearer {_con_alg(profesional, alg)}"},
            )
            assert r.status_code == 401, (alg, metodo, ruta, r.status_code)
    r = await cliente.get(
        PROF, headers={"Authorization": f"Bearer {_con_alg(profesional, 'HS256')}"}
    )
    assert r.status_code == 401  # un token invalido nunca se degrada a visitante


async def test_503_con_la_base_caida_nunca_500(
    monkeypatch: pytest.MonkeyPatch, profesional: UsuarioDePrueba
) -> None:
    monkeypatch.setenv("URL_BASE_DATOS", "postgresql://u:p@127.0.0.1:1/db")
    monkeypatch.setenv("TIMEOUT_POOL_SEGUNDOS", "0.5")
    obtener_configuracion.cache_clear()
    app = crear_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c,
    ):
        for metodo, ruta in (("GET", ESP), ("GET", PROF), ("GET", f"{PROF}/{profesional.id}")):
            r = await c.request(metodo, ruta, headers=con(profesional))
            assert (r.status_code, codigo(r)) == (503, "base_de_datos_no_disponible"), ruta
        r = await c.put(
            f"{PROF}/{profesional.id}/foto",
            headers=con(profesional),
            files={"archivo": ("f.jpg", JPEG, "image/jpeg")},
        )
        assert r.status_code == 503
