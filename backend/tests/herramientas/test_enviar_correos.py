"""La herramienta envia una vez la bandeja (SMTP de Mailpit)."""

import httpx
import psycopg
import pytest

from bugalu.compartido.configuracion import Configuracion
from bugalu.herramientas.enviar_correos import main

pytestmark = pytest.mark.integracion


def test_envia_los_pendientes_y_los_marca(
    configuracion: Configuracion, capsys: pytest.CaptureFixture[str]
) -> None:
    correo = "herramienta@prueba.bugalu.pe"
    with psycopg.connect(configuracion.url_base_datos_admin, autocommit=True) as c:
        try:
            c.execute(
                "insert into public.notificacion (tipo, destinatario, datos) values "
                '(\'reserva_caducada\', %s, \'{"folio": "BG-H", "inicio": '
                '"2027-03-10T15:00:00+00:00", "fin": "2027-03-10T17:00:00+00:00"}\')',
                (correo,),
            )
            assert main() == 0
            assert "1 correo(s) enviado(s)" in capsys.readouterr().out
            assert c.execute(
                "select enviada_en is not null from public.notificacion where destinatario = %s",
                (correo,),
            ).fetchone() == (True,)
        finally:
            c.execute("delete from public.notificacion where destinatario = %s", (correo,))
            httpx.request(
                "DELETE", "http://127.0.0.1:45624/api/v1/search", params={"query": f"to:{correo}"}
            )
