# ruff: noqa: E501, F811 - cuerpos JSON de prueba y fixtures compartidas
"""Retoques de la auditoria de RF-15 etapa A (ronda 2): mensajes, rol con operaciones, foto vigente y bloqueo."""

from collections.abc import Callable
from uuid import UUID

import httpx
import psycopg
import pytest
from httpx import AsyncClient
from psycopg_pool import AsyncConnectionPool

from bugalu.compartido.base_datos import transaccion_con_identidad
from bugalu.compartido.configuracion import Configuracion
from bugalu.modulos.asesorias.infraestructura.salida.repositorio_postgres import (
    RepositorioAsesoriasPostgres,
)
from tests.conftest import UsuarioDePrueba
from tests.modulos.asesorias.infraestructura.conftest import Ejecutar, con
from tests.modulos.asesorias.infraestructura.test_api_asesorias import (
    JPEG,
    PROF,
    codigo,
    crear_especialidad,
    publicar,
)

pytestmark = pytest.mark.integracion

API = "/api/v1"


async def test_cada_error_del_alta_del_perfil_tiene_su_mensaje(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    crear_usuario: Callable[[], UsuarioDePrueba],
) -> None:
    body = {"id_usuario": str(administrador.id)}
    assert (await cliente.post(PROF, headers=con(administrador), json=body)).status_code == 201
    repetido = await cliente.post(PROF, headers=con(administrador), json=body)
    sin_rol = await cliente.post(
        PROF, headers=con(administrador), json={"id_usuario": str(crear_usuario().id)}
    )
    assert (codigo(repetido), codigo(sin_rol)) == ("perfil_existente", "rol_no_admitido")
    assert "ya tiene" in repetido.json()["error"]["mensaje"]
    assert "no admite" in sin_rol.json()["error"]["mensaje"]


async def test_un_cliente_con_operaciones_vivas_no_pasa_a_profesional(
    cliente: AsyncClient,
    administrador: UsuarioDePrueba,
    crear_usuario: Callable[[], UsuarioDePrueba],
    sql: Ejecutar,
) -> None:
    c = crear_usuario()
    reserva = sql(
        "insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, vence_pago) "
        "select %s, (select id from public.sala_tecnica limit 1), se.id, '2099-03-01 10:00-05', '2099-03-01 11:00-05', 100, '2099-02-01' "
        "from public.servicio se where se.nombre = 'Ensayo' limit 1 returning id",
        c.id,
    )[0][0]
    try:
        r = await cliente.patch(
            f"{API}/usuarios/{c.id}", headers=con(administrador), json={"rol": "profesional"}
        )
        assert (r.status_code, codigo(r)) == (409, "cliente_con_operaciones")
        assert r.json()["error"]["detalles"] == {
            "reservas_vivas": 1,
            "creditos_vigentes": 0,
            "pagos_en_validacion": 0,
            "devoluciones_pendientes": 0,
        }
        assert sql("select rol from public.usuario where id = %s", c.id)[0][0] == "cliente"
        sql(
            "update public.reserva set estado = 'cancelada', motivo_cancelacion = 'cliente' where id = %s",
            reserva,
        )
        r = await cliente.patch(
            f"{API}/usuarios/{c.id}", headers=con(administrador), json={"rol": "profesional"}
        )
        assert r.status_code == 200, r.text
    finally:
        sql("delete from public.reserva where id = %s", reserva)


async def test_el_profesional_no_sobrescribe_directo_su_foto_vigente(
    cliente: AsyncClient,
    configuracion: Configuracion,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
    nombre_especialidad: Callable[[], str],
) -> None:
    esp = await crear_especialidad(cliente, administrador, nombre_especialidad())
    await publicar(cliente, administrador, profesional, esp)
    r = await cliente.put(
        f"{PROF}/{profesional.id}/foto",
        headers=con(profesional),
        files={"archivo": ("f.jpg", JPEG, "image/jpeg")},
    )
    assert r.status_code == 200, r.text
    base = f"{configuracion.url_supabase}/storage/v1/object/profesionales/{profesional.id}"
    cab = {
        "Authorization": f"Bearer {profesional.token}",
        "apikey": configuracion.clave_publicable_supabase,
        "Content-Type": "image/jpeg",
        "x-upsert": "true",
    }
    vigente = httpx.post(f"{base}/foto-1", headers=cab, content=b"\xff\xd8\xff" + b"MALO" * 10)
    assert vigente.status_code in (400, 403), vigente.text
    assert httpx.get(r.json()["foto_url"]).content == JPEG  # la vigente quedo intacta
    assert httpx.post(f"{base}/foto-2", headers=cab, content=JPEG).status_code == 200  # la libre si
    r2 = await cliente.put(  # y la API sigue reemplazando
        f"{PROF}/{profesional.id}/foto",
        headers=con(profesional),
        files={"archivo": ("g.jpg", JPEG, "image/jpeg")},
    )
    assert r2.status_code == 200, r2.text


async def test_leer_el_perfil_para_actualizar_bloquea_la_fila(
    pool: AsyncConnectionPool,
    configuracion: Configuracion,
    administrador: UsuarioDePrueba,
    profesional: UsuarioDePrueba,
) -> None:
    claims = {"sub": str(administrador.id), "role": "authenticated"}
    async with transaccion_con_identidad(pool, claims) as conexion:
        perfil = await RepositorioAsesoriasPostgres(conexion).obtener_profesional(
            UUID(str(profesional.id)), para_actualizar=True
        )
        assert perfil is not None
        with psycopg.connect(configuracion.url_base_datos_admin) as otra:
            with pytest.raises(psycopg.errors.LockNotAvailable):
                otra.execute(
                    "select 1 from public.perfil_profesional where id = %s for update nowait",
                    (profesional.id,),
                )
