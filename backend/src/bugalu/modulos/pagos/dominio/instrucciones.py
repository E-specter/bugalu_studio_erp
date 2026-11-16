"""Datos para pagar (RN-22) y contacto del estudio: validacion pura."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from bugalu.compartido.errores import DatosInvalidos

METODOS = ("transferencia", "yape", "plin", "tarjeta")
MAX_INSTRUCCION = 1000
MAX_CONTACTO = 500
_CONTROLES = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f  ]")  # salvo \n, \r, \t


@dataclass(frozen=True)
class Instruccion:
    metodo: str
    texto: str
    activo: bool


def _texto(valor: str, maximo: int) -> str:
    valor = valor.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(valor) > maximo or _CONTROLES.search(valor):
        raise DatosInvalidos(f"El texto admite hasta {maximo} caracteres.", {"campo": "texto"})
    return valor


def validar_instrucciones(entradas: Sequence[Instruccion]) -> list[Instruccion]:
    if sorted(e.metodo for e in entradas) != sorted(METODOS):
        raise DatosInvalidos("Envia los cuatro metodos, una vez cada uno.", {"campo": "metodo"})
    limpias = [Instruccion(e.metodo, _texto(e.texto, MAX_INSTRUCCION), e.activo) for e in entradas]
    if any(e.activo and not e.texto for e in limpias):
        raise DatosInvalidos("Un metodo activo necesita su texto.", {"campo": "texto"})
    return sorted(limpias, key=lambda e: METODOS.index(e.metodo))


def validar_contacto(texto: str) -> str:
    return _texto(texto, MAX_CONTACTO)
