"""Herramienta de mantenimiento (RF-17): publica la primera version de cada texto sin versiones.

Uso (desde backend/): uv run python -m bugalu.herramientas.cargar_textos_legales [carpeta]
Lee docs/08-legal/ (version del frontmatter; condiciones + anexo de propiedad intelectual;
resumenes de resumenes-para-pantallas.md) y conecta con URL_BASE_DATOS_ADMIN; no es parte de
la API. Es idempotente: un texto con alguna version, programada o vigente, no se toca.
En local se corre tras `db reset`; en produccion una vez, con los textos ya aprobados.
"""

import re
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from bugalu.compartido.configuracion import Configuracion

CARPETA = Path(__file__).resolve().parents[4] / "docs" / "08-legal"
# tipo -> archivos (el primero da la version; los demas se anexan al contenido)
ARCHIVOS = {
    "terminos_uso": ["terminos-de-uso.md"],
    "politica_privacidad": ["politica-de-privacidad.md"],
    "condiciones_contratacion": [
        "condiciones-de-contratacion.md",
        "condiciones-propiedad-intelectual.md",
    ],
    "declaracion_agrupacion": ["declaracion-de-agrupacion.md"],
}
# seccion de resumenes-para-pantallas.md -> contexto
SECCIONES = {
    "Registro": "registro",
    "Reserva de sala": "reserva",
    "Asesoría": "asesoria",
    "Registro de un pago": "pago",
    "Promociones": "promociones",
    "Usos promocionales": "usos_promocionales",
}
# tipo -> contextos cuyo resumen acompaña a ese texto
CONTEXTOS = {
    "terminos_uso": ["registro"],
    "politica_privacidad": ["registro", "pago", "promociones"],
    "condiciones_contratacion": ["reserva", "asesoria", "usos_promocionales"],
    "declaracion_agrupacion": [],  # su resumen es la casilla de agrupacion, aparte
}
_CASILLA_AGRUPACION = re.compile(
    r'^\*\*Si es una agrupación, casilla adicional \(obligatoria\):\*\* "(.+)"$', re.MULTILINE
)


class TextoInvalido(Exception):
    pass


def _leer(carpeta: Path, archivo: str) -> tuple[str, str]:
    """Devuelve (version del frontmatter, cuerpo sin frontmatter)."""
    texto = (carpeta / archivo).read_text(encoding="utf-8")
    partes = texto.split("---", 2)
    version = (
        re.search(r"^version: (\S+)\s*$", partes[1], re.MULTILINE) if len(partes) == 3 else None
    )
    if version is None:
        raise TextoInvalido(f"{archivo}: falta `version` en el frontmatter.")
    return version.group(1), partes[2].strip()


def _resumenes(carpeta: Path) -> tuple[dict[str, str], str]:
    """Resumen de cada contexto y la casilla de la agrupacion."""
    texto = (carpeta / "resumenes-para-pantallas.md").read_text(encoding="utf-8")
    resumenes: dict[str, str] = {}
    for seccion in re.split(r"^## ", texto, flags=re.MULTILINE)[1:]:
        titulo, _, cuerpo = seccion.partition("\n")
        contexto = SECCIONES.get(titulo.strip())
        resumen = re.search(r"^\*\*Resumen:\*\* (.+)$", cuerpo, re.MULTILINE)
        if contexto and resumen:
            resumenes[contexto] = resumen.group(1).strip()
    faltan = set(SECCIONES.values()) - set(resumenes)
    casilla = _CASILLA_AGRUPACION.search(texto)
    if faltan or casilla is None:
        raise TextoInvalido(
            "resumenes-para-pantallas.md: faltan los resumenes de "
            f"{sorted(faltan) or 'la casilla de agrupacion'}."
        )
    return resumenes, casilla.group(1)


def preparar(carpeta: Path) -> dict[str, tuple[str, str, dict[str, str]]]:
    """tipo -> (version, contenido, resumenes); falla antes de escribir si algo no cuadra."""
    if not carpeta.is_dir():
        raise TextoInvalido(f"No existe la carpeta {carpeta}.")
    resumenes, casilla = _resumenes(carpeta)
    textos = {}
    for tipo, archivos in ARCHIVOS.items():
        leidos = [_leer(carpeta, a) for a in archivos]
        por_contexto = {c: resumenes[c] for c in CONTEXTOS[tipo]}
        if tipo == "declaracion_agrupacion":
            por_contexto = {"registro": casilla}
        textos[tipo] = (leidos[0][0], "\n\n".join(cuerpo for _, cuerpo in leidos), por_contexto)
    return textos


def main(argumentos: list[str]) -> int:
    if len(argumentos) > 1:
        print("Uso: python -m bugalu.herramientas.cargar_textos_legales [carpeta]", file=sys.stderr)
        return 2
    url = Configuracion().url_base_datos_admin
    if not url:
        print("Falta URL_BASE_DATOS_ADMIN en backend/.env.", file=sys.stderr)
        return 1
    try:
        textos = preparar(Path(argumentos[0]) if argumentos else CARPETA)
    except (TextoInvalido, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    with psycopg.connect(url) as conexion:
        for tipo, (version, contenido, resumenes) in textos.items():
            publicado = conexion.execute(
                "insert into public.texto_legal "
                "(tipo, version, tipo_cambio, contenido, resumenes, vigente_desde) "
                "select %s, %s, 'mayor', %s, %s, now() "
                "where not exists (select 1 from public.texto_legal where tipo = %s)",
                (tipo, version, contenido, Jsonb(resumenes), tipo),
            ).rowcount
            print(f"{tipo}: " + (f"publicado {version}." if publicado else "ya tiene versiones."))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
