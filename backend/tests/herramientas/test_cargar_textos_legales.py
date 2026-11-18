"""RF-17: carga inicial de los textos de docs/08-legal/ (herramienta de mantenimiento)."""

import re
import shutil
from pathlib import Path
from typing import Any

import psycopg
import pytest

from bugalu.compartido.configuracion import Configuracion
from bugalu.herramientas.cargar_textos_legales import main

pytestmark = [pytest.mark.integracion, pytest.mark.usefixtures("textos_aislados")]

LEGAL = Path(__file__).resolve().parents[3] / "docs" / "08-legal"
TIPOS = {
    "terminos_uso",
    "politica_privacidad",
    "condiciones_contratacion",
    "declaracion_agrupacion",
}


def _filas(configuracion: Configuracion) -> dict[str, tuple[Any, ...]]:
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        filas = c.execute(
            "select tipo, version, tipo_cambio, contenido, resumenes, vigente_desde <= now(), "
            "publicado_en from public.texto_legal order by tipo"
        ).fetchall()
    return {f[0]: f for f in filas}


def _version(archivo: str) -> str:
    texto = (LEGAL / archivo).read_text(encoding="utf-8")
    encontrada = re.search(r"^version: (\S+)$", texto, re.MULTILINE)
    assert encontrada
    return encontrada.group(1)


def test_publica_la_primera_version_de_cada_texto_vigente_ya(
    configuracion: Configuracion, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([]) == 0
    filas = _filas(configuracion)
    assert set(filas) == TIPOS
    assert filas["terminos_uso"][1] == _version("terminos-de-uso.md")
    assert filas["politica_privacidad"][1] == _version("politica-de-privacidad.md")
    assert filas["condiciones_contratacion"][1] == _version("condiciones-de-contratacion.md")
    assert filas["declaracion_agrupacion"][1] == _version("declaracion-de-agrupacion.md")
    assert all(f[5] is True for f in filas.values())  # vigentes ya
    assert all(f[2] == "mayor" for f in filas.values())
    salida = capsys.readouterr().out
    assert all(tipo in salida for tipo in TIPOS)


def test_el_contenido_sale_del_cuerpo_sin_frontmatter_y_las_condiciones_llevan_el_anexo(
    configuracion: Configuracion,
) -> None:
    main([])
    filas = _filas(configuracion)
    terminos = filas["terminos_uso"][3]
    assert terminos.startswith("# Términos de uso de la plataforma Bugalú Studio")
    assert "estado: borrador" not in terminos  # el frontmatter no es contenido
    condiciones = filas["condiciones_contratacion"][3]
    assert condiciones.startswith("# Condiciones de contratación")
    assert "# Propiedad intelectual de las grabaciones" in condiciones  # el anexo, concatenado
    assert condiciones.index("# Propiedad intelectual") > condiciones.index("## ")  # al final
    danos = condiciones.index("\n# Uso del estudio y daños\n")
    assert danos > condiciones.index("# Propiedad intelectual")  # el anexo de daños, después
    assert filas["declaracion_agrupacion"][3].startswith("# Declaración de representación")


def test_los_resumenes_van_por_contexto_desde_resumenes_para_pantallas(
    configuracion: Configuracion,
) -> None:
    main([])
    filas = _filas(configuracion)
    assert set(filas["terminos_uso"][4]) == {"registro"}
    assert set(filas["politica_privacidad"][4]) == {"registro", "pago", "promociones"}
    assert set(filas["condiciones_contratacion"][4]) == {
        "reserva",
        "asesoria",
        "usos_promocionales",
    }
    assert set(filas["declaracion_agrupacion"][4]) == {"registro"}
    assert filas["terminos_uso"][4]["registro"].startswith("Para crear tu cuenta te pedimos")
    assert not filas["terminos_uso"][4]["registro"].startswith("**")
    assert filas["declaracion_agrupacion"][4]["registro"].startswith("Declaro que represento")
    assert filas["condiciones_contratacion"][4]["reserva"].startswith("El precio que ves")


def test_es_idempotente_y_no_toca_un_texto_que_ya_tiene_versiones(
    configuracion: Configuracion, capsys: pytest.CaptureFixture[str]
) -> None:
    with psycopg.connect(configuracion.url_base_datos_admin) as c:
        c.execute(
            "insert into public.texto_legal (tipo, version, tipo_cambio, contenido, vigente_desde) "
            "values ('terminos_uso', '5.0.0', 'mayor', 'Ya publicado', now())"
        )
    assert main([]) == 0
    primera = _filas(configuracion)
    assert primera["terminos_uso"][1:4] == ("5.0.0", "mayor", "Ya publicado")
    assert set(primera) == TIPOS
    capsys.readouterr()
    assert main([]) == 0  # segunda vez: nada cambia
    assert _filas(configuracion) == primera
    assert "publicado" not in capsys.readouterr().out


def test_un_texto_sin_version_en_su_frontmatter_falla_y_no_publica_nada(
    configuracion: Configuracion, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    carpeta = tmp_path / "legal"
    shutil.copytree(LEGAL, carpeta)
    archivo = carpeta / "politica-de-privacidad.md"
    archivo.write_text(
        re.sub(r"^version: .*\n", "", archivo.read_text(encoding="utf-8"), flags=re.MULTILINE),
        encoding="utf-8",
    )
    assert main([str(carpeta)]) == 1
    assert "politica-de-privacidad.md" in capsys.readouterr().err
    assert _filas(configuracion) == {}


def test_una_carpeta_inexistente_falla_con_mensaje(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "no-existe")]) == 1
    assert "no-existe" in capsys.readouterr().err
