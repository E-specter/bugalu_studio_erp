from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from bugalu.compartido.errores import (
    AlmacenamientoNoDisponible,
    ArchivoMuyGrande,
    FormatoNoAdmitido,
    NoEncontrado,
    SinPermiso,
)
from bugalu.modulos.pagos.aplicacion.obtener_captura.caso_de_uso import ObtenerCaptura
from bugalu.modulos.pagos.aplicacion.obtener_pago.caso_de_uso import ObtenerPago
from bugalu.modulos.pagos.aplicacion.registrar_pago.caso_de_uso import RegistrarPago
from bugalu.modulos.pagos.aplicacion.validar_pago.caso_de_uso import (
    AprobarPago,
    ListarPagos,
    RechazarPago,
)
from bugalu.modulos.pagos.dominio.captura import LIMITE_BYTES
from bugalu.modulos.pagos.dominio.modelos import Pago
from tests.modulos.pagos.aplicacion.falsos import AlmacenFalso, PagosFalso

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20
CLIENTE, CUOTA = uuid4(), uuid4()


async def registrar(repo: PagosFalso, almacen: AlmacenFalso, contenido: bytes = PNG) -> Pago:
    return await RegistrarPago(repo, almacen).ejecutar(
        CLIENTE, CUOTA, "yape", Decimal("25.00"), "ab-123", contenido
    )


async def test_inserta_antes_de_subir_y_sube_con_la_ruta_del_cliente() -> None:
    eventos: list[str] = []
    repo, almacen = PagosFalso(eventos=eventos), AlmacenFalso(eventos)
    pago = await registrar(repo, almacen)
    assert eventos == ["insertar", "subir"]
    assert pago.estado == "pendiente_validacion"
    ruta = f"{CLIENTE}/{pago.id}.png"
    assert almacen.subidos == {ruta: (PNG, "image/png")}
    assert repo.pagos[pago.id].ruta_captura == ruta
    assert repo.pagos[pago.id].numero_operacion == "AB-123"


async def test_un_formato_no_admitido_no_inserta_ni_sube() -> None:
    eventos: list[str] = []
    with pytest.raises(FormatoNoAdmitido):
        await registrar(PagosFalso(eventos=eventos), AlmacenFalso(eventos), b"MZ" + b"\0" * 50)
    assert eventos == []


async def test_mas_de_cinco_megas_no_inserta_ni_sube() -> None:
    eventos: list[str] = []
    grande = PNG + b"\0" * LIMITE_BYTES
    with pytest.raises(ArchivoMuyGrande):
        await registrar(PagosFalso(eventos=eventos), AlmacenFalso(eventos), grande)
    assert eventos == []


async def test_si_la_subida_falla_el_error_sale_para_deshacer_la_transaccion() -> None:
    with pytest.raises(AlmacenamientoNoDisponible):
        await registrar(PagosFalso(), AlmacenFalso(falla=True))


async def _con_pago() -> tuple[PagosFalso, AlmacenFalso, UUID]:
    repo, almacen = PagosFalso(), AlmacenFalso()
    pago = await registrar(repo, almacen)
    return repo, almacen, pago.id


async def test_obtener_pago_distingue_ajeno_de_inexistente() -> None:
    repo, _, id_pago = await _con_pago()
    assert (await ObtenerPago(repo).ejecutar(id_pago)).id == id_pago
    repo.ocultos.add(id_pago)
    repo.pagos.pop(id_pago)
    with pytest.raises(SinPermiso):
        await ObtenerPago(repo).ejecutar(id_pago)
    with pytest.raises(NoEncontrado):
        await ObtenerPago(repo).ejecutar(uuid4())


async def test_captura_devuelve_url_firmada_de_300_segundos_y_el_tipo() -> None:
    repo, almacen, id_pago = await _con_pago()
    ahora = datetime(2027, 1, 1, tzinfo=UTC)
    captura = await ObtenerCaptura(repo, almacen).ejecutar(id_pago, ahora)
    assert captura.url.endswith("?ttl=300")
    assert (captura.expira_en - ahora).total_seconds() == 300
    assert captura.tipo == "imagen"


async def test_solo_el_administrador_lista_y_el_cliente_no_llega_al_repositorio() -> None:
    with pytest.raises(SinPermiso):
        await ListarPagos(PagosFalso()).ejecutar("pendiente_validacion")
    repo = PagosFalso(administrador=True)
    pago = await registrar(repo, AlmacenFalso())
    assert await ListarPagos(repo).ejecutar("pendiente_validacion") == [repo.pagos[pago.id]]


async def test_aprobar_y_rechazar_devuelven_el_pago_ya_validado() -> None:
    repo = PagosFalso(administrador=True)
    uno, dos = await registrar(repo, AlmacenFalso()), await registrar(repo, AlmacenFalso())
    assert (await AprobarPago(repo).ejecutar(uno.id)).estado == "aprobado"
    rechazado = await RechazarPago(repo).ejecutar(dos.id, "monto errado")
    assert (rechazado.estado, rechazado.motivo_rechazo) == ("rechazado", "monto errado")
