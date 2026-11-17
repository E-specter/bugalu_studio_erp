"""API de RF-04: reservar, cancelar y leer reservas (stack local con RLS real)."""

import asyncio
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import UsuarioDePrueba
from tests.modulos.reservas.infraestructura.conftest import Ejecutar, con

pytestmark = pytest.mark.integracion

Crear = Callable[..., str]
RESERVAS = "/api/v1/reservas"
INICIO, FIN = "2027-03-10T10:00:00-05:00", "2027-03-10T12:00:00-05:00"


@pytest.fixture
def catalogo(sql: Ejecutar) -> dict[str, str]:
    filas = sql(
        "select nombre, id from public.servicio "
        "union all select nombre, id from public.especialista"
    )
    return {nombre: str(id_) for nombre, id_ in filas}


@pytest.fixture
def dia(franja: Crear) -> str:
    """Franjas del 10 y el 11 de marzo de 08:00 a 20:00."""
    franja("2027-03-11 08:00-05", "2027-03-11 20:00-05")
    return franja("2027-03-10 08:00-05", "2027-03-10 20:00-05")


async def reservar(
    cliente: AsyncClient,
    usuario: UsuarioDePrueba | None,
    sala: str,
    servicio: str,
    inicio: str = INICIO,
    fin: str = FIN,
    **extra: Any,
) -> Any:
    cuerpo = {
        "id_sala": sala,
        "id_servicio": servicio,
        "inicio": inicio,
        "fin": fin,
        "especialistas": [],
        "version_condiciones": "1.0.0",
        **extra,
    }
    return await cliente.post(RESERVAS, json=cuerpo, headers=con(usuario) if usuario else None)


def codigo(r: Any) -> str:
    return str(r.json()["error"]["codigo"])


def filas_de(sql: Ejecutar, usuario: UsuarioDePrueba) -> int:
    return int(sql("select count(*) from public.reserva where id_cliente = %s", usuario.id)[0][0])


# --- crear: exito --------------------------------------------------------------------------------


async def test_crea_pre_reservada_con_precio_del_motor_cuotas_y_plazo(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    voces, ejecutante = catalogo["Grabación de voces"], catalogo["Ejecutante"]
    r = await reservar(
        cliente, cliente_a, sala, voces, especialistas=[ejecutante], detalle="Voz y guitarra"
    )
    assert r.status_code == 201, r.text
    reserva = r.json()
    assert reserva["estado"] == "pre_reservada" and reserva["motivo_cancelacion"] is None
    assert re.fullmatch(r"R-\d{4}-\d{5}", reserva["folio"])
    assert reserva["fin_buffer"] == "2027-03-10T12:30:00-05:00"
    assert reserva["sala"]["nombre"] == "Sala principal"
    assert reserva["servicio"] == {
        "id": voces,
        "nombre": "Grabación de voces",
        "categoria": "grabacion",
    }
    assert {e["nombre"] for e in reserva["especialistas"]} == {"Ingeniero de sonido", "Ejecutante"}
    assert "cliente" not in reserva
    # El precio es el de la simulacion publica: el mismo motor.
    simulacion = await cliente.post(
        "/api/v1/simulaciones",
        json={
            "id_sala": sala,
            "id_servicio": voces,
            "inicio": INICIO,
            "fin": FIN,
            "especialistas": [ejecutante],
        },
    )
    assert reserva["precio"] == simulacion.json()
    total, anticipo = Decimal(reserva["precio"]["total"]), Decimal(reserva["precio"]["anticipo"])
    cuotas = {c["hito"]: c for c in reserva["cuotas"]}
    assert set(cuotas) == {"al_reservar", "al_terminar"}
    assert Decimal(cuotas["al_reservar"]["monto"]) == anticipo
    assert Decimal(cuotas["al_terminar"]["monto"]) == total - anticipo
    assert all(c["estado"] == "pendiente" and c["id"] for c in cuotas.values())
    assert reserva["vence_pago"] == "2027-03-07T10:00:00-05:00"  # 3 dias antes del inicio
    assert sql("select detalle from public.reserva where id = %s", reserva["id"]) == [
        ("Voz y guitarra",)
    ]


async def test_el_cliente_no_puede_enviar_precios(
    cliente: AsyncClient, dia: str, sala: str, catalogo: dict[str, str], cliente_a: UsuarioDePrueba
) -> None:
    for campo, valor in (
        ("precio", {"total": "1.00"}),
        ("total", "1.00"),
        ("estado", "confirmada"),
    ):
        r = await reservar(
            cliente, cliente_a, sala, catalogo["Grabación de voces"], **{campo: valor}
        )
        assert r.status_code == 422, campo
        assert r.json()["error"]["detalles"] == {"campo": campo}


async def test_encola_el_aviso_con_la_fecha_limite(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    r = await reservar(cliente, cliente_a, sala, catalogo["Grabación de voces"])
    [(tipo, destinatario, datos, enviada)] = sql(
        "select tipo, destinatario, datos, enviada_en from public.notificacion "
        "where datos ->> 'id_reserva' = %s",
        r.json()["id"],
    )
    assert (tipo, destinatario, enviada) == ("reserva_creada", cliente_a.correo, None)
    assert datos["folio"] == r.json()["folio"]
    assert datetime.fromisoformat(datos["vence_pago"]) == datetime.fromisoformat(
        r.json()["vence_pago"]
    )


async def test_si_faltan_menos_de_los_dias_del_plazo_vence_1_hora_despues(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql("update public.parametro set valor = 1000 where clave = 'dias_limite_pago'")
    r = await reservar(cliente, cliente_a, sala, catalogo["Grabación de voces"])
    assert r.status_code == 201
    vence = datetime.fromisoformat(r.json()["vence_pago"])
    assert abs(vence - (datetime.now(UTC) + timedelta(hours=1))) < timedelta(minutes=2)


# --- crear: seguridad y validacion ---------------------------------------------------------------


async def test_sin_sesion_es_401_y_no_crea_nada(
    cliente: AsyncClient, dia: str, sala: str, catalogo: dict[str, str], sql: Ejecutar
) -> None:
    r = await reservar(cliente, None, sala, catalogo["Grabación de voces"])
    assert r.status_code == 401 and codigo(r) == "no_autenticado"
    assert sql("select count(*) from public.reserva where inicio >= '2027-01-01'") == [(0,)]


@pytest.mark.parametrize(
    ("cambios", "esperado", "campo"),
    [
        (
            {"inicio": "2027-03-10T10:15:00-05:00", "fin": "2027-03-10T11:15:00-05:00"},
            "duracion_invalida",
            "fin",
        ),
        ({"fin": "2027-03-10T10:00:00-05:00"}, "duracion_invalida", "fin"),
        ({"fin": "2027-03-10T18:30:00-05:00"}, "duracion_invalida", "fin"),
        (
            {"inicio": "2027-03-10T07:00:00-05:00", "fin": "2027-03-10T08:00:00-05:00"},
            "fuera_de_franja",
            "inicio",
        ),
        (
            {"inicio": "2027-03-10T18:30:00-05:00", "fin": "2027-03-10T20:00:00-05:00"},
            "fuera_de_franja",
            "inicio",
        ),
        (
            {"inicio": "2027-03-12T10:00:00-05:00", "fin": "2027-03-12T11:00:00-05:00"},
            "fuera_de_franja",
            "inicio",
        ),
        (
            {"inicio": "2027-03-10T10:00:00", "fin": "2027-03-10T11:00:00"},
            "datos_invalidos",
            "inicio",
        ),
        ({"detalle": "hola\x00mundo"}, "datos_invalidos", "detalle"),
        ({"detalle": "x\x07y"}, "datos_invalidos", "detalle"),
        ({"detalle": "x" * 501}, "datos_invalidos", "detalle"),
        ({"id_servicio": "no-es-uuid"}, "datos_invalidos", "id_servicio"),
        ({"especialistas": ["00000000-0000-0000-0000-000000000000"]}, "datos_invalidos", None),
        ({"id_servicio": "00000000-0000-0000-0000-000000000000"}, "datos_invalidos", None),
        ({"id_sala": "00000000-0000-0000-0000-000000000000"}, "datos_invalidos", None),
    ],
)
async def test_cada_422_del_contrato(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
    cambios: dict[str, Any],
    esperado: str,
    campo: str | None,
) -> None:
    cuerpo = {"id_servicio": catalogo["Grabación de voces"], **cambios}
    r = await cliente.post(
        RESERVAS,
        json={
            "id_sala": sala,
            "inicio": INICIO,
            "fin": FIN,
            "especialistas": [],
            "version_condiciones": "1.0.0",
            **cuerpo,
        },
        headers=con(cliente_a),
    )
    assert r.status_code == 422, r.text
    assert codigo(r) == esperado
    if campo:
        assert r.json()["error"]["detalles"]["campo"] == campo
    assert filas_de(sql, cliente_a) == 0


async def test_servicio_que_no_ocupa_sala_no_es_reservable(
    cliente: AsyncClient, dia: str, sala: str, catalogo: dict[str, str], cliente_a: UsuarioDePrueba
) -> None:
    r = await reservar(cliente, cliente_a, sala, catalogo["Mezcla"])
    assert r.status_code == 422 and codigo(r) == "servicio_no_reservable"


async def test_servicio_inactivo_no_es_reservable(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql("update public.servicio set activo = false where nombre = 'Grabación de voces'")
    try:
        r = await reservar(cliente, cliente_a, sala, catalogo["Grabación de voces"])
    finally:
        sql("update public.servicio set activo = true where nombre = 'Grabación de voces'")
    assert r.status_code == 422 and codigo(r) == "servicio_no_reservable"


async def test_un_cierre_que_toca_el_tramo_es_fuera_de_franja(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql(
        "insert into public.cierre_sala (id_sala, inicio, fin, motivo) "
        "values (%s, '2027-03-10 12:00-05', '2027-03-10 14:00-05', 'Mantenimiento')",
        sala,
    )
    r = await reservar(
        cliente, cliente_a, sala, catalogo["Grabación de voces"]
    )  # buffer hasta 12:30
    assert r.status_code == 422 and codigo(r) == "fuera_de_franja"


async def test_anticipacion_insuficiente_y_excesiva_segun_los_parametros(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    sql("update public.parametro set valor = 100000 where clave = 'anticipacion_minima_horas'")
    r = await reservar(cliente, cliente_a, sala, catalogo["Grabación de voces"])
    assert r.status_code == 422 and codigo(r) == "anticipacion_insuficiente"
    sql("update public.parametro set valor = 2 where clave = 'anticipacion_minima_horas'")
    sql("update public.parametro set valor = 1 where clave = 'anticipacion_maxima_semanas'")
    r = await reservar(cliente, cliente_a, sala, catalogo["Grabación de voces"])
    assert r.status_code == 422 and codigo(r) == "anticipacion_excesiva"
    assert filas_de(sql, cliente_a) == 0


# --- ensayo (RN-13) ------------------------------------------------------------------------------


def _previa(sql: Ejecutar, cliente: UsuarioDePrueba, sala: str, estado: str, dia: int = 20) -> None:
    sql(
        "insert into public.reserva (id_cliente, id_sala, id_servicio, inicio, fin, total, estado, "
        "motivo_cancelacion) select %s, %s, id, %s, %s, 10, %s, %s from public.servicio "
        "where nombre = 'Grabación de voces'",
        cliente.id,
        sala,
        f"2027-03-{dia} 10:00-05",
        f"2027-03-{dia} 11:00-05",
        estado,
        "cliente" if estado == "cancelada" else None,
    )


async def test_el_ensayo_exige_un_servicio_previo_confirmado_o_posterior(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    ensayo = catalogo["Ensayo"]
    _previa(sql, cliente_b, sala, "confirmada")  # de otro cliente: no cuenta
    _previa(sql, cliente_a, sala, "pre_reservada", 21)
    _previa(sql, cliente_a, sala, "cancelada", 22)
    r = await reservar(cliente, cliente_a, sala, ensayo)
    assert r.status_code == 403 and codigo(r) == "ensayo_no_disponible"
    _previa(sql, cliente_a, sala, "confirmada", 23)
    r = await reservar(cliente, cliente_a, sala, ensayo)
    assert r.status_code == 201, r.text
    assert r.json()["servicio"]["nombre"] == "Ensayo"


# --- solapes y concurrencia ----------------------------------------------------------------------


async def test_el_tramo_ocupado_o_su_buffer_es_409_y_no_deja_rastro(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    voces = catalogo["Grabación de voces"]
    assert (await reservar(cliente, cliente_a, sala, voces)).status_code == 201
    for inicio, fin in (
        (INICIO, FIN),
        ("2027-03-10T11:00:00-05:00", "2027-03-10T13:00:00-05:00"),
        ("2027-03-10T12:00:00-05:00", "2027-03-10T13:00:00-05:00"),  # dentro del buffer
    ):
        r = await reservar(cliente, cliente_b, sala, voces, inicio, fin)
        assert r.status_code == 409 and codigo(r) == "tramo_no_disponible", (inicio, r.text)
    assert filas_de(sql, cliente_b) == 0
    assert sql(
        "select count(*) from public.cuota where id_reserva in "
        "(select id from public.reserva where id_cliente = %s)",
        cliente_b.id,
    ) == [(0,)]
    assert (
        await reservar(
            cliente,
            cliente_b,
            sala,
            voces,
            "2027-03-10T12:30:00-05:00",
            "2027-03-10T13:30:00-05:00",
        )
    ).status_code == 201


async def test_dos_peticiones_a_la_vez_una_gana_y_la_otra_es_409(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    voces = catalogo["Grabación de voces"]
    for _ in range(3):  # varias rondas: el solape lo decide la base, no el orden de llegada
        a, b = await asyncio.gather(
            reservar(cliente, cliente_a, sala, voces), reservar(cliente, cliente_b, sala, voces)
        )
        assert sorted([a.status_code, b.status_code]) == [201, 409], (a.text, b.text)
        assert {codigo(x) for x in (a, b) if x.status_code == 409} == {"tramo_no_disponible"}
        assert sql(
            "select count(*) from public.reserva where estado <> 'cancelada' "
            "and inicio = '2027-03-10 10:00-05'"
        ) == [(1,)]
        sql("delete from public.reserva where inicio = '2027-03-10 10:00-05'")


# --- caducidad (RN-18) ---------------------------------------------------------------------------


async def test_una_pre_reservada_vencida_libera_el_tramo_y_otro_cliente_lo_toma(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    voces = catalogo["Grabación de voces"]
    a = await reservar(cliente, cliente_a, sala, voces)
    sql(
        "update public.reserva set vence_pago = now() - interval '1 minute' where id = %s",
        a.json()["id"],
    )
    b = await reservar(cliente, cliente_b, sala, voces)
    assert b.status_code == 201, b.text
    assert sql(
        "select estado, motivo_cancelacion from public.reserva where id = %s", a.json()["id"]
    ) == [("cancelada", "caducada")]
    assert sql("select count(*) from public.notificacion where tipo = 'reserva_caducada'") == [(1,)]
    vista = await cliente.get(f"{RESERVAS}/{a.json()['id']}", headers=con(cliente_a))
    assert (
        vista.json()["estado"] == "cancelada" and vista.json()["motivo_cancelacion"] == "caducada"
    )


async def test_el_proceso_de_caducidad_cancela_las_vencidas_sin_pagos_y_respeta_las_pagadas(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    voces = catalogo["Grabación de voces"]
    sin_pago = (await reservar(cliente, cliente_a, sala, voces)).json()["id"]
    con_pago = (
        await reservar(
            cliente,
            cliente_a,
            sala,
            voces,
            "2027-03-10T14:00:00-05:00",
            "2027-03-10T15:00:00-05:00",
        )
    ).json()["id"]
    sql(
        "update public.cuota set estado = 'pagada' where id_reserva = %s and hito = 'al_reservar'",
        con_pago,
    )
    sql(
        "update public.reserva set vence_pago = now() - interval '1 minute' "
        "where id = any(%s::uuid[])",
        [sin_pago, con_pago],
    )
    assert sql("select public.caducar_reservas()") == [(1,)]
    assert sql("select estado from public.reserva where id = %s", con_pago) == [("pre_reservada",)]


# --- cancelar ------------------------------------------------------------------------------------


async def _crear(
    cliente: AsyncClient, usuario: UsuarioDePrueba, sala: str, catalogo: dict[str, str]
) -> str:
    r = await reservar(cliente, usuario, sala, catalogo["Grabación de voces"])
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def test_el_dueno_cancela_sin_pagos_y_libera_el_tramo(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
) -> None:
    id_ = await _crear(cliente, cliente_a, sala, catalogo)
    r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(cliente_a))
    assert r.status_code == 200, r.text
    assert (r.json()["estado"], r.json()["motivo_cancelacion"]) == ("cancelada", "cliente")
    assert (await _crear(cliente, cliente_b, sala, catalogo)) != id_  # el tramo quedo libre
    repetida = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(cliente_a))
    assert repetida.status_code == 409 and codigo(repetida) == "no_cancelable"


async def test_nadie_cancela_la_reserva_ajena_y_la_fila_queda_intacta(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    id_ = await _crear(cliente, cliente_a, sala, catalogo)
    antes = sql("select * from public.reserva where id = %s", id_)
    for intruso in (cliente_b, personal):
        r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(intruso))
        assert r.status_code == 403 and codigo(r) == "sin_permiso"
    assert sql("select * from public.reserva where id = %s", id_) == antes


async def test_con_pagos_el_cliente_recibe_tiene_pagos_y_el_administrador_exige_nota(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    id_ = await _crear(cliente, cliente_a, sala, catalogo)
    sql(
        "update public.cuota set estado = 'pagada' where id_reserva = %s and hito = 'al_reservar'",
        id_,
    )
    r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(cliente_a))
    assert r.status_code == 409 and codigo(r) == "tiene_pagos"
    r = await cliente.post(
        f"{RESERVAS}/{id_}/cancelar", json={"nota": "reembolso"}, headers=con(cliente_a)
    )
    assert r.status_code == 409 and codigo(r) == "tiene_pagos"
    r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(administrador))
    assert r.status_code == 422 and codigo(r) == "nota_requerida"
    assert r.json()["error"]["detalles"] == {"campo": "nota"}
    assert sql("select estado from public.reserva where id = %s", id_) == [("pre_reservada",)]


async def test_el_administrador_cancela_la_de_otro_con_motivo_administrador(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
) -> None:
    id_ = await _crear(cliente, cliente_a, sala, catalogo)
    r = await cliente.post(f"{RESERVAS}/{id_}/cancelar", headers=con(administrador))
    assert r.status_code == 200
    assert (r.json()["estado"], r.json()["motivo_cancelacion"]) == ("cancelada", "administrador")
    assert r.json()["cliente"]["nombre"] == "Ana Torres"


async def test_cancelar_inexistente_anonimo_o_id_invalido(
    cliente: AsyncClient, cliente_a: UsuarioDePrueba
) -> None:
    inexistente = "00000000-0000-0000-0000-000000000000"
    r = await cliente.post(f"{RESERVAS}/{inexistente}/cancelar", headers=con(cliente_a))
    assert r.status_code == 404 and codigo(r) == "no_encontrado"
    r = await cliente.post(f"{RESERVAS}/{inexistente}/cancelar")
    assert r.status_code == 401
    r = await cliente.post(f"{RESERVAS}/no-es-uuid/cancelar", headers=con(cliente_a))
    assert r.status_code == 422 and codigo(r) == "datos_invalidos"


# --- lecturas ------------------------------------------------------------------------------------


async def test_mias_solo_devuelve_las_propias_con_precio_y_cuotas(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
) -> None:
    mia = await _crear(cliente, cliente_a, sala, catalogo)
    await reservar(
        cliente, cliente_b, sala, catalogo["Grabación de voces"],
        "2027-03-11T10:00:00-05:00", "2027-03-11T11:00:00-05:00",
    )  # fmt: skip
    r = await cliente.get(f"{RESERVAS}/mias", headers=con(cliente_a))
    assert r.status_code == 200
    [reserva] = r.json()
    assert reserva["id"] == mia and len(reserva["cuotas"]) == 2 and "lineas" in reserva["precio"]
    assert "cliente" not in reserva
    assert (await cliente.get(f"{RESERVAS}/mias")).status_code == 401
    de_b = await cliente.get(f"{RESERVAS}/mias", headers=con(cliente_b))
    assert [x["id"] for x in de_b.json()] != [mia] and len(de_b.json()) == 1


async def test_ver_una_reserva_segun_quien_la_pide(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
) -> None:
    id_ = await _crear(cliente, cliente_a, sala, catalogo)
    url = f"{RESERVAS}/{id_}"
    propia = await cliente.get(url, headers=con(cliente_a))
    assert propia.status_code == 200 and "cliente" not in propia.json()
    for staff in (personal, administrador):
        r = await cliente.get(url, headers=con(staff))
        assert r.status_code == 200
        assert r.json()["cliente"] == {"id": str(cliente_a.id), "nombre": "Ana Torres"}
        assert {k: v for k, v in r.json().items() if k != "cliente"} == {
            **propia.json(),
            # solo el dueno y el administrador ven la version aceptada
            "version_condiciones": r.json()["version_condiciones"],
        }
    ajena = await cliente.get(url, headers=con(cliente_b))
    assert ajena.status_code == 403 and codigo(ajena) == "sin_permiso"
    assert id_ not in ajena.text and "Ana" not in ajena.text
    assert (await cliente.get(url)).status_code == 401
    r = await cliente.get(
        f"{RESERVAS}/00000000-0000-0000-0000-000000000000", headers=con(cliente_b)
    )
    assert r.status_code == 404 and codigo(r) == "no_encontrado"
    r = await cliente.get(f"{RESERVAS}/no-es-uuid", headers=con(cliente_b))
    assert r.status_code == 422 and codigo(r) == "datos_invalidos"


async def test_el_precio_guardado_no_cambia_si_cambian_las_tarifas(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    r = await reservar(cliente, cliente_a, sala, catalogo["Grabación de voces"])
    sql("update public.servicio set tarifa_hora = 999 where nombre = 'Grabación de voces'")
    try:
        otra = await cliente.get(f"{RESERVAS}/{r.json()['id']}", headers=con(cliente_a))
    finally:
        sql("update public.servicio set tarifa_hora = 80 where nombre = 'Grabación de voces'")
    assert otra.json()["precio"] == r.json()["precio"]


RANGO = {"desde": "2027-03-10T00:00:00-05:00", "hasta": "2027-03-12T00:00:00-05:00"}


async def test_el_personal_y_el_administrador_listan_por_rango_con_cliente(
    cliente: AsyncClient,
    dia: str,
    sala: str,
    catalogo: dict[str, str],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    administrador: UsuarioDePrueba,
) -> None:
    voces = catalogo["Grabación de voces"]
    a = await reservar(cliente, cliente_a, sala, voces)
    await reservar(
        cliente, cliente_b, sala, voces, "2027-03-11T10:00:00-05:00", "2027-03-11T11:00:00-05:00"
    )
    for staff in (personal, administrador):
        r = await cliente.get(RESERVAS, params=RANGO, headers=con(staff))
        assert r.status_code == 200
        assert [x["inicio"] for x in r.json()] == [
            "2027-03-10T10:00:00-05:00",
            "2027-03-11T10:00:00-05:00",
        ]
        assert (
            r.json()[0]["cliente"]["nombre"] == "Ana Torres" and r.json()[0]["id"] == a.json()["id"]
        )
    solo_el_11 = {"desde": "2027-03-11T00:00:00-05:00", "hasta": "2027-03-12T00:00:00-05:00"}
    r = await cliente.get(RESERVAS, params=solo_el_11, headers=con(personal))
    assert len(r.json()) == 1


async def test_listar_por_rango_exige_personal_y_rango_valido(
    cliente: AsyncClient,
    cliente_a: UsuarioDePrueba,
    personal: UsuarioDePrueba,
    sql: Ejecutar,
) -> None:
    r = await cliente.get(RESERVAS, params=RANGO, headers=con(cliente_a))
    assert r.status_code == 403 and codigo(r) == "sin_permiso"
    assert (await cliente.get(RESERVAS, params=RANGO)).status_code == 401
    malos = [
        {"desde": RANGO["hasta"], "hasta": RANGO["desde"]},
        {"desde": "2027-03-01T00:00:00-05:00", "hasta": "2027-06-01T00:00:00-05:00"},
        {"desde": "2027-03-01T00:00:00", "hasta": "2027-03-02T00:00:00"},
        {"desde": "ayer", "hasta": "hoy"},
        {},
    ]
    for params in malos:
        r = await cliente.get(RESERVAS, params=params, headers=con(personal))
        assert r.status_code == 422 and codigo(r) in {"datos_invalidos", "rango_invalido"}, params


# --- OpenAPI -------------------------------------------------------------------------------------

CONTRATO = {
    ("post", "/api/v1/reservas"): {401, 403, 409, 422, 503},
    ("get", "/api/v1/reservas"): {401, 403, 422, 503},
    ("get", "/api/v1/reservas/mias"): {401, 503},
    ("get", "/api/v1/reservas/{id_reserva}"): {401, 403, 404, 422, 503},
    ("post", "/api/v1/reservas/{id_reserva}/cancelar"): {401, 403, 404, 409, 422, 503},
}


def test_openapi_declara_los_codigos_del_contrato_con_respuesta_error(app: FastAPI) -> None:
    rutas = app.openapi()["paths"]
    for (metodo, ruta), codigos in CONTRATO.items():
        respuestas = rutas[ruta][metodo]["responses"]
        for c in codigos:
            esquema = respuestas[str(c)]["content"]["application/json"]["schema"]
            assert esquema == {"$ref": "#/components/schemas/RespuestaError"}, (metodo, ruta, c)
    assert rutas["/api/v1/reservas"]["post"]["responses"]["201"]
