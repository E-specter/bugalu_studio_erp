from collections.abc import Callable, Iterator
from uuid import UUID, uuid4

import httpx
import pytest

from bugalu.compartido.configuracion import Configuracion
from tests.modulos.reservas.infraestructura.conftest import (  # noqa: F401 - fixtures compartidas
    Ejecutar,
    administrador,
    app,
    cliente,
    cliente_a,
    cliente_b,
    reservar,
    reservas_intactas,
    sala,
    sql,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"contenido-de-prueba" * 10
PDF = b"%PDF-1.7\n" + b"contenido-de-prueba" * 10
_OBJETOS_DE_PRUEBA = (
    "select o.name from storage.objects o join auth.users u "
    "on u.id::text = (storage.foldername(o.name))[1] "
    "where o.bucket_id = 'comprobantes' and u.email like '%%@prueba.bugalu.pe'"
)


@pytest.fixture(autouse=True)
def pagos_limpios(
    request: pytest.FixtureRequest,
    configuracion: Configuracion,
    sql: Ejecutar,  # noqa: F811
    reservas_intactas: None,  # noqa: F811 - se limpia antes que las reservas (FK de las cuotas)
) -> Iterator[None]:
    """Borra los objetos de Storage por su API con la clave de servicio local (solo pruebas)."""
    yield
    if request.node.get_closest_marker("integracion") is None:
        return
    rutas = [f[0] for f in sql(_OBJETOS_DE_PRUEBA)]
    if rutas:
        r = httpx.request(
            "DELETE",
            f"{configuracion.url_supabase}/storage/v1/object/comprobantes",
            headers={"Authorization": f"Bearer {configuracion.clave_servicio_supabase_pruebas}"},
            json={"prefixes": rutas},
        )
        r.raise_for_status()
    sql(
        "delete from public.comprobante_pago where id_cuota in (select c.id from public.cuota c "
        "join public.reserva r on r.id = c.id_reserva where r.inicio >= '2027-01-01' "
        "and r.inicio < '2028-01-01')"
    )
    huerfanos = (
        sql(_OBJETOS_DE_PRUEBA),
        sql("select id from public.comprobante_pago where numero_operacion like 'PRUEBA-%%'"),
    )
    assert huerfanos == ([], []), f"las pruebas dejaron pagos u objetos huerfanos: {huerfanos}"


@pytest.fixture
def cuota_de(sql: Ejecutar, reservar: Callable[..., str]) -> Callable[..., str]:  # noqa: F811
    """Reserva (2027) del cliente con una cuota `al_reservar` de 25.00; devuelve la cuota."""
    dias = iter(range(1, 28))

    def crear(usuario: object, estado: str = "confirmada") -> str:
        dia = next(dias)
        id_reserva = reservar(
            usuario.id,  # type: ignore[attr-defined]
            f"2027-05-{dia:02d}T10:00:00-05:00",
            f"2027-05-{dia:02d}T12:00:00-05:00",
            estado,
        )
        return str(
            sql(
                "insert into public.cuota (id_reserva, hito, monto) values (%s, 'al_reservar', 25) "
                "returning id",
                UUID(id_reserva),
            )[0][0]
        )

    return crear


def operacion() -> str:
    return f"PRUEBA-{uuid4().hex[:10]}"
