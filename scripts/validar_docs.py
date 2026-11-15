"""Valida la documentación atómica de docs/ (PROYECTO.md §7.1) y que .mcp.json no tenga secretos.

Uso: python scripts/validar_docs.py docs [--ids-desde docs/superpowers/specs/PROYECTO-v0.2.md]
"""

import argparse
import json
import re
import sys
from pathlib import Path

CAMPOS = ("id", "titulo", "estado", "depende_de")
ESTADOS = {"borrador", "aprobado", "implementado"}
MAX_LINEAS = 150
RE_ID_TABLA = re.compile(r"^\| ((?:RN|RF|D)-\d+) \|", re.MULTILINE)
RE_ID = re.compile(r"^(?:RN|RF|D)-\d+$")
RE_ENLACE = re.compile(r"\]\(([^)\s]+)\)")
RE_CLAVE_SECRETA = re.compile(r"token|key|secret|password|authorization", re.IGNORECASE)


def leer_frontmatter(texto: str) -> dict | None:
    if not texto.startswith("---\n"):
        return None
    fin = texto.find("\n---\n", 4)
    if fin == -1:
        return None
    campos = {}
    for linea in texto[4:fin].splitlines():
        clave, sep, valor = linea.partition(":")
        if sep:
            campos[clave.strip()] = valor.strip()
    return campos


def validar(raiz: Path, fuente_ids: Path | None) -> list[str]:
    errores: list[str] = []
    definidos: dict[str, list[Path]] = {}
    for ruta in sorted(raiz.rglob("*.md")):
        rel = ruta.relative_to(raiz)
        if "superpowers" in rel.parts:  # planes y specs congeladas: fuera de la doc viva
            continue
        texto = ruta.read_text(encoding="utf-8").replace("\r\n", "\n")
        ids = set(RE_ID_TABLA.findall(texto))

        if texto.count("\n") > MAX_LINEAS:
            errores.append(f"{rel}: supera {MAX_LINEAS} líneas")

        if ruta.name != "README.md":
            fm = leer_frontmatter(texto)
            if fm is None:
                errores.append(f"{rel}: falta frontmatter")
            else:
                faltan = [c for c in CAMPOS if c not in fm]
                if faltan:
                    errores.append(f"{rel}: frontmatter sin {', '.join(faltan)}")
                if fm.get("estado") not in ESTADOS:
                    errores.append(f"{rel}: estado inválido '{fm.get('estado')}'")
                if RE_ID.match(fm.get("id", "")):
                    ids.add(fm["id"])

        for destino in RE_ENLACE.findall(texto):
            if destino.startswith(("http://", "https://", "mailto:", "#")):
                continue
            objetivo = destino.split("#", 1)[0]
            if objetivo and not (ruta.parent / objetivo).exists():
                errores.append(f"{rel}: enlace roto {destino}")

        for i in ids:
            definidos.setdefault(i, []).append(rel)

    for i, rutas in sorted(definidos.items()):
        if len(rutas) > 1:
            errores.append(f"{i}: definido en varios archivos ({', '.join(map(str, rutas))})")

    if fuente_ids:
        esperados = set(RE_ID_TABLA.findall(fuente_ids.read_text(encoding="utf-8").replace("\r\n", "\n")))
        for i in sorted(esperados - definidos.keys()):
            errores.append(f"{i}: presente en {fuente_ids.name} pero en ningún archivo de docs/")
    return errores


def validar_mcp(ruta: Path) -> list[str]:
    errores: list[str] = []

    def recorrer(nodo, camino):
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                if isinstance(valor, str) and RE_CLAVE_SECRETA.search(clave) and "${" not in valor:
                    errores.append(f"{ruta.name}: valor literal en {camino}{clave}; usa ${{VARIABLE}}")
                recorrer(valor, f"{camino}{clave}.")
        elif isinstance(nodo, list):
            for elem in nodo:
                recorrer(elem, camino)

    recorrer(json.loads(ruta.read_text(encoding="utf-8")), "")
    return errores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raiz", type=Path)
    parser.add_argument("--ids-desde", type=Path)
    args = parser.parse_args()
    errores = validar(args.raiz, args.ids_desde)
    if Path(".mcp.json").exists():
        errores += validar_mcp(Path(".mcp.json"))
    sys.stdout.reconfigure(encoding="utf-8")
    for e in errores:
        print(e)
    print(f"{len(errores)} error(es)" if errores else "docs OK")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
