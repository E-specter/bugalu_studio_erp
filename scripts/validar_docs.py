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
    campos: dict = {}
    clave = None
    for linea in texto[4:fin].splitlines():
        item = re.match(r"^\s+-\s+(.*)$", linea)
        if item and clave:  # elemento de lista YAML bajo la última clave
            if not isinstance(campos[clave], list):
                campos[clave] = []
            campos[clave].append(item.group(1).strip())
            continue
        clave, sep, valor = linea.partition(":")
        if not sep:
            clave = None
            continue
        clave, valor = clave.strip(), valor.strip()
        if valor.startswith("[") and valor.endswith("]"):
            campos[clave] = [v.strip() for v in valor[1:-1].split(",") if v.strip()]
        else:
            campos[clave] = valor
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


def _norm(valor) -> str:
    return str(valor).strip().strip("\"'").lower()


def _skills(valor) -> set[str]:
    if isinstance(valor, list):
        return {s.strip().strip("\"'") for s in valor}
    return {s.strip() for s in str(valor or "").split(",") if s.strip()}


def validar_agentes(dir_agentes: Path, equipo: Path) -> list[str]:
    """Compara el frontmatter de .claude/agents/*.md con la tabla '## Subagentes' de equipo.md."""
    texto = equipo.read_text(encoding="utf-8")
    seccion = texto.split("## Subagentes", 1)[1].split("\n## ", 1)[0] if "## Subagentes" in texto else ""
    esperados = {}
    for nombre, resto in re.findall(r"^\| `([\w-]+)` \|(.*)$", seccion, re.MULTILINE):
        modelo, effort, turnos, precarga = [c.strip() for c in resto.split("|")][:4]
        esperados[nombre] = {
            "model": _norm(modelo),
            "effort": _norm(effort),
            "maxTurns": _norm(turnos),
            "skills": set(re.findall(r"`([^`]+)`", precarga)),
        }
    archivos = {p.stem: p for p in dir_agentes.glob("*.md")}
    errores = [f"{n}: agente sin fila en {equipo.name}" for n in sorted(archivos.keys() - esperados.keys())]
    errores += [f"{n}: fila de {equipo.name} sin archivo en {dir_agentes}" for n in sorted(esperados.keys() - archivos.keys())]
    for nombre in sorted(archivos.keys() & esperados.keys()):
        fm = leer_frontmatter(archivos[nombre].read_text(encoding="utf-8").replace("\r\n", "\n")) or {}
        real = {
            "model": _norm(fm.get("model", "")),
            "effort": _norm(fm.get("effort", "")),
            "maxTurns": _norm(fm.get("maxTurns", "")),
            "skills": _skills(fm.get("skills")),
        }
        for campo, valor in esperados[nombre].items():
            if real[campo] != valor:
                errores.append(f"{nombre}: {campo} es {real[campo] or '∅'} y {equipo.name} dice {valor or '∅'}")
    return errores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raiz", type=Path)
    parser.add_argument("--ids-desde", type=Path)
    args = parser.parse_args()
    errores = validar(args.raiz, args.ids_desde)
    if Path(".mcp.json").exists():
        errores += validar_mcp(Path(".mcp.json"))
    agentes, equipo = Path(".claude/agents"), args.raiz / "04-agentes" / "equipo.md"
    if agentes.is_dir() and equipo.exists():
        errores += validar_agentes(agentes, equipo)
    sys.stdout.reconfigure(encoding="utf-8")
    for e in errores:
        print(e)
    print(f"{len(errores)} error(es)" if errores else "docs OK")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
