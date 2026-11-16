"""Storage directo con el token de un cliente y la clave publicable: mandan la RLS y el bucket."""

from collections.abc import Callable, Iterator
from uuid import uuid4

import httpx
import pytest

from bugalu.compartido.configuracion import Configuracion
from tests.conftest import UsuarioDePrueba
from tests.modulos.pagos.infraestructura.conftest import PDF, PNG, _clave_de_servicio
from tests.modulos.reservas.infraestructura.conftest import Ejecutar

pytestmark = pytest.mark.integracion

DENEGADO = range(400, 500)


class Storage:
    def __init__(self, configuracion: Configuracion, token: str) -> None:
        self.base = f"{configuracion.url_supabase}/storage/v1"
        self.cabeceras = {
            "Authorization": f"Bearer {token}",
            "apikey": configuracion.clave_publicable_supabase,
        }

    def pedir(self, metodo: str, ruta: str, **datos: object) -> httpx.Response:
        cabeceras = {**self.cabeceras, **datos.pop("headers", {})}  # type: ignore[call-overload]
        return httpx.request(metodo, f"{self.base}{ruta}", headers=cabeceras, **datos)  # type: ignore[arg-type]

    def subir(
        self, ruta: str, contenido: bytes = PNG, mime: str = "image/png", upsert: bool = False
    ) -> httpx.Response:
        return self.pedir(
            "POST",
            f"/object/comprobantes/{ruta}",
            content=contenido,
            headers={"Content-Type": mime, "x-upsert": "true" if upsert else "false"},
        )


@pytest.fixture
def storage(configuracion: Configuracion) -> Callable[[str], Storage]:
    return lambda token: Storage(configuracion, token)


@pytest.fixture
def servicio(configuracion: Configuracion) -> Iterator[Storage]:
    """Solo pruebas: limpia con la clave de servicio lo que un intento fallido dejara."""
    s = Storage(configuracion, _clave_de_servicio())
    sucias: list[str] = []
    s.sucias = sucias  # type: ignore[attr-defined]
    yield s
    if sucias:
        s.pedir("DELETE", "/object/comprobantes", json={"prefixes": sucias})


def _huella(sql: Ejecutar, ruta: str) -> list[tuple[object, ...]]:
    return sql(
        "select id, metadata->>'eTag', metadata->>'size', version from storage.objects "
        "where bucket_id = 'comprobantes' and name = %s",
        ruta,
    )


def _existe(sql: Ejecutar, ruta: str) -> bool:
    return bool(_huella(sql, ruta))


@pytest.fixture
def objeto_de_a(
    storage: Callable[[str], Storage], cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> tuple[str, list[tuple[object, ...]]]:
    ruta = f"{cliente_a.id}/{uuid4()}.png"
    assert storage(cliente_a.token).subir(ruta).status_code == 200
    return ruta, _huella(sql, ruta)


def _a(storage: Callable[[str], Storage], u: UsuarioDePrueba) -> Storage:
    return storage(u.token)


def test_el_dueno_sube_en_su_carpeta(
    storage: Callable[[str], Storage], cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    ruta = f"{cliente_a.id}/{uuid4()}.pdf"
    r = _a(storage, cliente_a).subir(ruta, PDF, "application/pdf")
    assert r.status_code == 200, r.text
    assert _existe(sql, ruta)


@pytest.mark.parametrize(
    "plantilla",
    [
        "{otro}/{n}.png",
        "{yo}/../{otro}/{n}.png",
        "{yo}/%2e%2e/{otro}/{n}.png",
        "%2e%2e/{otro}/{n}.png",
        "{yo}%2f..%2f{otro}/{n}.png",
        "../{n}.png",
        "{n}.png",
    ],
)
def test_subir_fuera_de_la_carpeta_propia_se_deniega(
    storage: Callable[[str], Storage],
    servicio: Storage,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    sql: Ejecutar,
    plantilla: str,
) -> None:
    n = uuid4()
    ruta = plantilla.format(yo=cliente_a.id, otro=cliente_b.id, n=n)
    r = _a(storage, cliente_a).subir(ruta)
    servicio.sucias.append(ruta)  # type: ignore[attr-defined]
    # Con `%2f..%2f` la propia API de Storage responde 500 (no confirma el rollback): no es 2xx y no
    # crea nada; lo que importa es que no exista el objeto.
    assert r.status_code >= 400, r.text
    assert sql("select count(*) from storage.objects where name like %s", f"%{n}%")[0][0] == 0


def test_upsert_y_put_no_reemplazan_su_propio_objeto(
    storage: Callable[[str], Storage],
    cliente_a: UsuarioDePrueba,
    objeto_de_a: tuple[str, list[tuple[object, ...]]],
    sql: Ejecutar,
) -> None:
    ruta, antes = objeto_de_a
    s = _a(storage, cliente_a)
    assert s.subir(ruta, PDF, "application/pdf", upsert=True).status_code in DENEGADO
    r = s.pedir(
        "PUT",
        f"/object/comprobantes/{ruta}",
        content=PDF,
        headers={"Content-Type": "application/pdf"},
    )
    assert r.status_code in DENEGADO, r.text
    assert _huella(sql, ruta) == antes


def test_mover_se_deniega_y_el_objeto_sigue_en_su_sitio(
    storage: Callable[[str], Storage],
    cliente_a: UsuarioDePrueba,
    objeto_de_a: tuple[str, list[tuple[object, ...]]],
    sql: Ejecutar,
) -> None:
    ruta, antes = objeto_de_a
    destino = f"{cliente_a.id}/{uuid4()}.png"
    r = _a(storage, cliente_a).pedir(
        "POST",
        "/object/move",
        json={"bucketId": "comprobantes", "sourceKey": ruta, "destinationKey": destino},
    )
    assert r.status_code in DENEGADO, r.text
    assert _huella(sql, ruta) == antes
    assert not _existe(sql, destino)


def test_copiar_hacia_otra_carpeta_se_deniega(
    storage: Callable[[str], Storage],
    servicio: Storage,
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    objeto_de_a: tuple[str, list[tuple[object, ...]]],
    sql: Ejecutar,
) -> None:
    ruta, _ = objeto_de_a
    destino = f"{cliente_b.id}/{uuid4()}.png"
    servicio.sucias.append(destino)  # type: ignore[attr-defined]
    r = _a(storage, cliente_a).pedir(
        "POST",
        "/object/copy",
        json={"bucketId": "comprobantes", "sourceKey": ruta, "destinationKey": destino},
    )
    assert r.status_code in DENEGADO, r.text
    assert not _existe(sql, destino)


def test_copiar_dentro_de_su_carpeta_se_permite_y_no_es_bloqueante(
    storage: Callable[[str], Storage],
    cliente_a: UsuarioDePrueba,
    objeto_de_a: tuple[str, list[tuple[object, ...]]],
    sql: Ejecutar,
) -> None:
    # Documentado: select + insert propios bastan para duplicar un objeto en la propia carpeta.
    # No es bloqueante: ocupa 5 MB como maximo, no reemplaza nada ni toca otra carpeta, y el
    # duplicado queda sin fila de comprobante (huerfano de su carpeta, borrable por servicio).
    ruta, antes = objeto_de_a
    destino = f"{cliente_a.id}/{uuid4()}.png"
    r = _a(storage, cliente_a).pedir(
        "POST",
        "/object/copy",
        json={"bucketId": "comprobantes", "sourceKey": ruta, "destinationKey": destino},
    )
    assert r.status_code == 200, r.text
    assert _huella(sql, ruta) == antes
    assert _existe(sql, destino)


def test_borrar_por_ruta_y_por_prefijos_no_borra_nada(
    storage: Callable[[str], Storage],
    cliente_a: UsuarioDePrueba,
    objeto_de_a: tuple[str, list[tuple[object, ...]]],
    sql: Ejecutar,
) -> None:
    ruta, antes = objeto_de_a
    s = _a(storage, cliente_a)
    por_ruta = s.pedir("DELETE", f"/object/comprobantes/{ruta}")
    por_prefijos = s.pedir("DELETE", "/object/comprobantes", json={"prefixes": [ruta]})
    # La API puede responder 200 con la lista vacia de borrados: manda que el objeto siga.
    assert por_ruta.status_code in DENEGADO or por_ruta.status_code == 200
    assert por_prefijos.status_code in DENEGADO or por_prefijos.json() == []
    assert _huella(sql, ruta) == antes


def test_un_cliente_no_lista_firma_ni_descarga_objetos_ajenos(
    storage: Callable[[str], Storage],
    cliente_b: UsuarioDePrueba,
    objeto_de_a: tuple[str, list[tuple[object, ...]]],
    cliente_a: UsuarioDePrueba,
) -> None:
    ruta, _ = objeto_de_a
    s = _a(storage, cliente_b)
    listado = s.pedir(
        "POST", "/object/list/comprobantes", json={"prefix": f"{cliente_a.id}/", "limit": 100}
    )
    assert listado.status_code in DENEGADO or listado.json() == []
    firma = s.pedir("POST", f"/object/sign/comprobantes/{ruta}", json={"expiresIn": 60})
    assert firma.status_code in DENEGADO, firma.text
    lote = s.pedir("POST", "/object/sign/comprobantes", json={"expiresIn": 60, "paths": [ruta]})
    assert lote.status_code in DENEGADO or all(
        f.get("error") or not f.get("signedURL") for f in lote.json()
    )
    assert s.pedir("GET", f"/object/authenticated/comprobantes/{ruta}").status_code in DENEGADO


def test_una_url_firmada_no_sirve_para_otra_ruta(
    storage: Callable[[str], Storage],
    cliente_a: UsuarioDePrueba,
    cliente_b: UsuarioDePrueba,
    servicio: Storage,
    objeto_de_a: tuple[str, list[tuple[object, ...]]],
) -> None:
    ruta, _ = objeto_de_a
    otra = f"{cliente_a.id}/{uuid4()}.png"
    assert _a(storage, cliente_a).subir(otra).status_code == 200
    firma = _a(storage, cliente_a).pedir(
        "POST", f"/object/sign/comprobantes/{ruta}", json={"expiresIn": 60}
    )
    assert firma.status_code == 200, firma.text
    url = firma.json()["signedURL"]
    propia = httpx.get(f"{servicio.base}{url}")
    assert propia.status_code == 200 and propia.content == PNG
    token = url.split("token=")[1]
    ajena = httpx.get(f"{servicio.base}/object/sign/comprobantes/{otra}?token={token}")
    assert ajena.status_code in DENEGADO, ajena.text


@pytest.mark.parametrize(
    ("contenido", "mime"),
    [
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml"),
        (b"GIF89a" + b"x" * 20, "image/gif"),
        (b"MZ" + b"x" * 20, "application/octet-stream"),
        (b"<html></html>", "text/html"),
    ],
)
def test_el_bucket_rechaza_tipos_no_admitidos_subidos_directo(
    storage: Callable[[str], Storage],
    cliente_a: UsuarioDePrueba,
    sql: Ejecutar,
    contenido: bytes,
    mime: str,
) -> None:
    ruta = f"{cliente_a.id}/{uuid4()}.bin"
    r = _a(storage, cliente_a).subir(ruta, contenido, mime)
    assert r.status_code in DENEGADO, r.text
    assert not _existe(sql, ruta)


def test_el_bucket_rechaza_mas_de_5_mb_subido_directo(
    storage: Callable[[str], Storage], cliente_a: UsuarioDePrueba, sql: Ejecutar
) -> None:
    ruta = f"{cliente_a.id}/{uuid4()}.png"
    r = _a(storage, cliente_a).subir(ruta, PNG + b"0" * (5 * 1024 * 1024))
    assert r.status_code in DENEGADO, r.text
    assert not _existe(sql, ruta)
