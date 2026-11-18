import csv
import io

import pytest

from bugalu.modulos.reclamaciones.dominio.exportar import COLUMNAS, a_csv, neutralizar


@pytest.mark.parametrize("peligrosa", ["=1+1", "+51999", "-2", "@SUM(A1)", "\tx", "\rx"])
def test_neutraliza_las_celdas_que_un_programa_de_hojas_ejecutaria(peligrosa: str) -> None:
    assert neutralizar(peligrosa) == "'" + peligrosa


@pytest.mark.parametrize("segura", ["Ana", "2026-11-17", "", "a=b", "Av. Lima 123"])
def test_deja_igual_lo_demas(segura: str) -> None:
    assert neutralizar(segura) == segura


def test_el_csv_lleva_cabecera_filas_y_celdas_neutralizadas() -> None:
    fila = dict.fromkeys(COLUMNAS, "x") | {
        "nombre": '=HYPERLINK("http://x")',
        "detalle": 'a,b\n"c"',
    }
    leidas = list(csv.reader(io.StringIO(a_csv([fila]).removeprefix("\ufeff"))))
    assert leidas[0] == list(COLUMNAS)
    assert leidas[1][COLUMNAS.index("nombre")] == '\'=HYPERLINK("http://x")'
    assert leidas[1][COLUMNAS.index("detalle")] == 'a,b\n"c"'


def test_el_csv_empieza_con_bom_para_excel_y_sin_hojas_trae_solo_la_cabecera() -> None:
    texto = a_csv([])
    assert texto.startswith("\ufeff")
    assert len(list(csv.reader(io.StringIO(texto.removeprefix("\ufeff"))))) == 1
